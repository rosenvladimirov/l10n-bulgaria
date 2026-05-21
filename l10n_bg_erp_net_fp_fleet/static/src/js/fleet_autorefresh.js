/** @odoo-module **/

/**
 * Fleet auto-refresh — handler for `FLEET_UPDATE` env.bus events
 * dispatched by the central hub in `l10n_bg_live_refresh`.
 *
 * The actual bus.bus channel subscription (`erpnet_fp_fleet`) lives in
 * the live_refresh service (consolidated to avoid every plugin opening
 * its own subscription). This service just listens for the env.bus
 * relay event and asks every open `erpnet.fp.proxy` view to reload —
 * throttled to ≤1 reload per 3 s so a fleet of hundreds of heartbeats
 * doesn't hammer the browser.
 */

import { registry } from "@web/core/registry";

const _MIN_INTERVAL_MS = 3000;

export const fleetAutorefreshService = {
    dependencies: ["live_refresh", "action"],
    start(env, _deps) {
        let _lastTick = 0;
        let _pending = null;

        const _reloadOpenFleetViews = () => {
            // Throttle — collapse bursts of FLEET_UPDATE events into one reload.
            const now = Date.now();
            if (now - _lastTick < _MIN_INTERVAL_MS) {
                if (_pending) return;
                _pending = setTimeout(() => {
                    _pending = null;
                    _reloadOpenFleetViews();
                }, _MIN_INTERVAL_MS - (now - _lastTick));
                return;
            }
            _lastTick = now;
            env.bus.trigger("ROUTE_CHANGE_REQUEST_FLEET_RELOAD");
        };

        env.bus.addEventListener("FLEET_UPDATE", _reloadOpenFleetViews);
    },
};

registry.category("services").add("erpnet_fp_fleet_autorefresh",
    fleetAutorefreshService);

/* -------------------------------------------------------------- */
/* Hook into the kanban + list controllers' load() so any open
   Fleet view reloads on the trigger above. We do NOT replace the
   controllers — we just patch a tiny `setup()` extension that
   listens for the trigger and calls `model.load()`.                */
/* -------------------------------------------------------------- */

import { KanbanController } from "@web/views/kanban/kanban_controller";
import { ListController } from "@web/views/list/list_controller";
import { FormController } from "@web/views/form/form_controller";
import { onMounted, onWillUnmount } from "@odoo/owl";
import { patch } from "@web/core/utils/patch";

function _patchController(C) {
    patch(C.prototype, {
        setup() {
            super.setup();
            if (this.props.resModel !== "erpnet.fp.proxy") return;
            const _onTrigger = () => {
                // Best-effort: model API differs slightly between
                // kanban (this.model.root.load) and list. We try the
                // common entrypoints and ignore failures.
                try {
                    if (this.model && this.model.load) {
                        this.model.load();
                    } else if (this.model && this.model.root && this.model.root.load) {
                        this.model.root.load();
                    }
                } catch (e) {
                    // Swallow — view may be transitioning out.
                }
            };
            onMounted(() => {
                this.env.bus.addEventListener(
                    "ROUTE_CHANGE_REQUEST_FLEET_RELOAD", _onTrigger);
            });
            onWillUnmount(() => {
                this.env.bus.removeEventListener(
                    "ROUTE_CHANGE_REQUEST_FLEET_RELOAD", _onTrigger);
            });
        },
    });
}

_patchController(KanbanController);
_patchController(ListController);
_patchController(FormController);
