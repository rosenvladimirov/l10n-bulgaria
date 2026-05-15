/** @odoo-module **/

/**
 * Bootstraps the myPOS Embedded SDK on the payment page.
 *
 * The server-rendered template (embedded_form) drops a mount <div> with
 * the createPayment params in a data attribute + loads the official
 * mypos-embedded-sdk.js. We wait for `MyPOSEmbedded` to be defined, then
 * mount the iFrame and wire the callbacks:
 *
 *   onSuccess → the signed urlNotify S2S callback has (or will) update
 *               the transaction; we just send the shopper to the Odoo
 *               payment-status page which polls the tx state.
 *   onError   → surface a generic failure (no PAN/PII ever reaches JS).
 *
 * Deliberately framework-light: it does NOT hook into Odoo's payment_form
 * state machine (fragile across 18/19). The template is rendered into the
 * page like a redirect form; this script takes over from there.
 */

function _waitForSdk(cb, tries) {
    tries = tries === undefined ? 50 : tries; // ~5s at 100ms
    if (typeof window.MyPOSEmbedded !== "undefined") {
        cb(window.MyPOSEmbedded);
        return;
    }
    if (tries <= 0) {
        console.error("[payment_mypos_embedded] MyPOSEmbedded SDK failed to load");
        return;
    }
    setTimeout(function () {
        _waitForSdk(cb, tries - 1);
    }, 100);
}

function _initMount(mount) {
    if (mount.dataset.myposInitialised === "1") {
        return; // guard against double-mount on re-render
    }
    mount.dataset.myposInitialised = "1";

    let params;
    try {
        params = JSON.parse(mount.dataset.myposParams || "{}");
    } catch (e) {
        console.error("[payment_mypos_embedded] bad params blob", e);
        return;
    }
    const isSandbox = mount.dataset.myposSandbox === "1";

    _waitForSdk(function (sdk) {
        sdk.createPayment(mount.id, params, {
            isSandbox: isSandbox,
            onSuccess: function () {
                // The authoritative state transition happens via the
                // signed S2S urlNotify; just move the shopper forward.
                window.location = "/payment/status";
            },
            onError: function () {
                window.location = "/payment/status";
            },
        });
    });
}

function _scan() {
    document
        .querySelectorAll(".o_mypos_embedded[data-mypos-params]")
        .forEach(_initMount);
}

if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", _scan);
} else {
    _scan();
}
