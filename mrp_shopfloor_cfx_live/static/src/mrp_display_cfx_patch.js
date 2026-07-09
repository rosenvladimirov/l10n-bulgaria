/** @odoo-module **/
// Copyright 2026 Rosen Vladimirov <vladimirov.rosen@gmail.com>
// License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
//
// Shop Floor real-time CFX injection.
//
// CFX машинните събития пътуват по СЪЩЕСТВУВАЩИЯ bus канал
// `erpnet_fp_proxy_events`. `l10n_bg_live_refresh` вече ги префирва като
// единичен `PROXY_EVENT` на `env.bus` (виж live_refresh_service.js). Тук
// само се абонираме за него и филтрираме `cfx.*` — НЕ добавяме нов канал
// и НЕ пипаме mrp_workorder / live_refresh (само patch + t-inherit).
//
// ДВА пласта:
//   • MrpDisplay      → авторитетен repaint чрез env.reload(record)
//                       (Shop Floor repaint лоста, mrp_display.js:98).
//   • MrpDisplayRecord → ephemeral overlay badge БЕЗ DB round-trip.

import { patch } from "@web/core/utils/patch";
import { useBus } from "@web/core/utils/hooks";
import { useState } from "@odoo/owl";
import { MrpDisplay } from "@mrp_workorder/mrp_display/mrp_display";
import { MrpDisplayRecord } from "@mrp_workorder/mrp_display/mrp_display_record";

// Единен CFX type префикс — вокабуларът е дефиниран в Phase-2
// (cfx_ingest.py _EVENT_TYPE_MAP): cfx.work_started / cfx.materials_installed
// / cfx.work_completed / cfx.station_state / cfx.fault / cfx.wo_progress.
const CFX_TYPE_PREFIX = "cfx.";

// Кои събития оправдават DB reload (authoritative repaint). Високо-честотните
// (materials_installed / station_state / fault) се обслужват само от
// ephemeral overlay-а, за да не хамерим ORM-а на всяко поставяне на детайл.
const CFX_RELOAD_TYPES = new Set([
    "cfx.work_started",
    "cfx.work_completed",
    "cfx.wo_progress",
]);

// Извади WO/MO ключа от CFX envelope-а. Phase-2 emit-ва `data.workorder`
// (виж cfx_ingest.py _emit_wo_refresh); приемаме и `wo_name` / `workorder_id`
// алиаси за устойчивост към бъдещи proxy-payload варианти.
function _cfxWoKey(envelope) {
    const d = (envelope && envelope.data) || {};
    const key = d.workorder ?? d.wo_name ?? d.workorder_id;
    if (key === undefined || key === null || key === "") {
        return "";
    }
    return String(key);
}

function _isCfxEvent(envelope) {
    const t = envelope && envelope.type;
    return typeof t === "string" && t.startsWith(CFX_TYPE_PREFIX);
}

// ───────────────────────── MrpDisplay (repaint) ─────────────────────────
patch(MrpDisplay.prototype, {
    setup() {
        super.setup(...arguments);
        // Преизползваме префирнатия PROXY_EVENT (една абонирана точка,
        // без нов bus канал). live_refresh_service.js:137 го trigger-ва.
        useBus(this.env.bus, "PROXY_EVENT", (ev) => this._onCfxProxyEvent(ev.detail));
    },

    /**
     * Match CFX събитие към отворена MO/WO карта и презареди авторитетно.
     * @param {Object} envelope пълният bus_inject envelope {v,type,source,ts,id,data}
     */
    _onCfxProxyEvent(envelope) {
        try {
            if (!_isCfxEvent(envelope)) {
                return;
            }
            const key = _cfxWoKey(envelope);
            if (!key || !this.model || !this.model.root) {
                return;
            }
            // 1) MO (mrp.production) по name — Phase-2 обичайно носи MO ключ.
            let target = this.model.root.records.find(
                (mo) => String(mo.data.name) === key
            );
            // 2) иначе WO (mrp.workorder) по name или barcode.
            if (!target) {
                target = this.workorders.find(
                    (wo) =>
                        String(wo.data.name) === key ||
                        String(wo.data.barcode || "") === key
                );
            }
            if (target) {
                // env.reload изкачва до mrp.production и презарежда картата.
                this.env.reload(target);
            } else if (CFX_RELOAD_TYPES.has(envelope.type)) {
                // WO, който още не е на дъската, може да е станал релевантен
                // (напр. току-що стартиран) → пълен board reload.
                this.env.reload();
            }
        } catch (e) {
            console.warn("[cfx-live] MrpDisplay reload suppressed:", e);
        }
    },
});

// ─────────────────── MrpDisplayRecord (ephemeral overlay) ───────────────────
patch(MrpDisplayRecord.prototype, {
    setup() {
        super.setup(...arguments);
        // Transient live състояние за overlay значката — НЕ докосва DB.
        this.cfxLive = useState({
            active: false,
            placed: 0,
            station: "",
            message: "",
            ts: 0,
        });
        useBus(this.env.bus, "PROXY_EVENT", (ev) => this._onCfxOverlayEvent(ev.detail));
    },

    /** Дали CFX събитието се отнася за ТАЗИ карта (MO или неин WO). */
    _cfxMatchesThisCard(key) {
        const rec = this.props.record;
        if (!rec || !rec.data) {
            return false;
        }
        if (String(rec.data.name) === key) {
            return true;
        }
        // MO карта: провери имената на нейните work orders.
        if (rec.resModel === "mrp.production") {
            const wos = (rec.data.workorder_ids && rec.data.workorder_ids.records) || [];
            return wos.some((w) => String(w.data.name) === key);
        }
        return false;
    },

    _onCfxOverlayEvent(envelope) {
        try {
            if (!_isCfxEvent(envelope)) {
                return;
            }
            const key = _cfxWoKey(envelope);
            if (!key || !this._cfxMatchesThisCard(key)) {
                return;
            }
            const d = envelope.data || {};
            this.cfxLive.active = true;
            if (d.placed !== undefined && d.placed !== null) {
                this.cfxLive.placed = Number(d.placed) || 0;
            }
            if (d.state) {
                this.cfxLive.station = String(d.state);
            }
            // Кратък етикет: "work_started" / "materials_installed" / ...
            this.cfxLive.message = String(envelope.type).slice(CFX_TYPE_PREFIX.length);
            this.cfxLive.ts = Date.now();
        } catch (e) {
            console.warn("[cfx-live] overlay update suppressed:", e);
        }
    },
});
