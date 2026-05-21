/** @odoo-module **/

/**
 * Auto-refresh listener for the ErpNet.FP Fleet kanban/list view.
 *
 * The server emits `fleet_update` events on the `erpnet_fp_fleet`
 * bus channel whenever a proxy heartbeats, auto-enrols, or gets
 * banned. This module subscribes to that channel and, when a hit
 * arrives, asks every open `erpnet.fp.proxy` view (kanban/list/form)
 * to reload its records.
 *
 * Throttled to one reload per 3 seconds so a fleet with hundreds of
 * heartbeating proxies doesn't hammer the browser. The trade-off is
 * worth it — admins want "is my new shop online?" feedback within
 * a minute, not real-time tick rate.
 */

import { registry } from "@web/core/registry";

const _MIN_INTERVAL_MS = 3000;

export const fleetAutorefreshService = {
    dependencies: ["bus_service", "action"],
    start(env, { bus_service, action }) {
        let _lastTick = 0;
        let _pending = null;

        const _reloadOpenFleetViews = () => {
            // Throttle — collapse bursts of bus events into one reload.
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
            // Fire a global event the controller picks up.
            env.bus.trigger("ROUTE_CHANGE_REQUEST_FLEET_RELOAD");
        };

        bus_service.addChannel("erpnet_fp_fleet");
        bus_service.addEventListener("notification", ({ detail }) => {
            for (const { type, payload } of detail) {
                if (type !== "fleet_update") continue;
                _reloadOpenFleetViews();
            }
        });
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
