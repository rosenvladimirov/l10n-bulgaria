/** @odoo-module **/

import { Component, onMounted, useState } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";
import { rpc } from "@web/core/network/rpc";
import { _t } from "@web/core/l10n/translation";
import { getSharedSigner, KepSignerError } from "./kep_signer";

/**
 * Custom dialog that runs the full КЕП sign → submit flow for an
 * nra.declaration record.
 *
 * The dialog displays a timeline of steps (Connect → Load → Sign → Submit)
 * and shows the StampIT PIN dialog transparently in the background. The
 * user sees a single Odoo-native modal instead of a trail of notifications,
 * which keeps the UX predictable and makes it clear which StampIT dialog
 * is expected at each point.
 */
export class SignSubmitDialog extends Component {
    static template = "l10n_bg_api_nra.SignSubmitDialog";
    static components = { Dialog };
    static props = {
        declarationId: Number,
        declarationName: String,
        close: Function,
    };

    setup() {
        this.state = useState({
            running: false,
            error: null,
            result: null,
        });
        this.steps = useState([
            {
                id: "connect",
                label: _t("Connect to StampIT signing component"),
                hint: _t("Checking http://127.0.0.1:8090"),
                status: "pending",
            },
            {
                id: "load",
                label: _t("Load declaration XML"),
                hint: _t("Fetching the document bytes from Odoo"),
                status: "pending",
            },
            {
                id: "sign",
                label: _t("Sign with КЕП"),
                hint: _t("Select your certificate (first time only), then enter PIN"),
                status: "pending",
            },
            {
                id: "submit",
                label: _t("Submit to НАП"),
                hint: _t("Posting signed payload to the public API"),
                status: "pending",
            },
        ]);
        onMounted(() => this.run());
    }

    stepClass(step) {
        return "o_kep_step_" + step.status;
    }

    _setStep(id, status) {
        const step = this.steps.find((s) => s.id === id);
        if (step) {
            step.status = status;
        }
    }

    async run() {
        this.state.running = true;
        this.state.error = null;
        const signer = getSharedSigner();

        try {
            // 1. Connect
            this._setStep("connect", "active");
            const health = await signer.isRunning();
            if (!health.ok) {
                if (health.reason === "blocked_pna") {
                    throw new KepSignerError(
                        _t(
                            "Browser blocked request to http://127.0.0.1:8090 " +
                            "(Private Network Access). Please allow insecure " +
                            "private network requests in your browser settings " +
                            "and try again.",
                        ),
                    );
                }
                throw new KepSignerError(
                    _t(
                        "StampIT signing component is not running. " +
                        "Start it from portal.nra.bg.",
                    ),
                );
            }
            this._setStep("connect", "done");

            // 2. Load XML
            this._setStep("load", "active");
            const docData = await rpc(
                "/l10n_bg_api_nra/declaration_content",
                { declaration_id: this.props.declarationId },
            );
            this._setStep("load", "done");

            // 3. Select signer (chooser dialog — ONCE per session)
            this._setStep("sign", "active");
            await signer.selectSigner();
            // Now sign (only PIN dialog, no chooser)
            const signed = await signer.sign(docData.content_base64);
            this._setStep("sign", "done");

            // 4. Submit — extract ЕГН from the certificate
            this._setStep("submit", "active");
            const signerPin = this._extractEgnFromCert(signed.signerCert)
                || this._extractEgnFromSignerName(signed.signerName);
            console.log(
                "KEP sign: pin=%s cert_len=%d sig_len=%d name=%s",
                signerPin, signed.signerCert?.length, signed.signature?.length,
                signed.signerName,
            );
            if (!signerPin) {
                throw new KepSignerError(
                    _t("Cannot extract ЕГН from the selected certificate."),
                );
            }
            const result = await rpc(
                "/l10n_bg_api_nra/sign_submit",
                {
                    declaration_id: this.props.declarationId,
                    signer_cert: signed.signerCert,
                    signer_pin: signerPin,
                    pkcs7_signature: signed.signature,
                },
            );
            this._setStep("submit", "done");

            this.state.result = result;
        } catch (err) {
            console.error("KEP sign/submit failed:", err);
            const activeStep = this.steps.find((s) => s.status === "active");
            if (activeStep) {
                activeStep.status = "error";
            }
            this.state.error = err instanceof KepSignerError
                ? err.message
                : (err.data?.message || err.message || String(err));
        } finally {
            this.state.running = false;
        }
    }

    onClose() {
        if (this.state.running) return;
        // Reload the form if submission succeeded
        if (this.state.result && this.props.close) {
            // Trigger a page/view reload so the user sees the new state
            this.props.close();
            window.location.reload();
            return;
        }
        if (this.props.close) {
            this.props.close();
        }
    }

    _extractEgnFromSignerName(signerName) {
        if (!signerName) return null;
        const m = signerName.match(/\b\d{10}\b/);
        return m ? m[0] : null;
    }

    _extractEgnFromCert(certBase64) {
        try {
            const bin = atob(certBase64);
            const bytes = new Uint8Array(bin.length);
            for (let i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);
            const oid = [0x06, 0x03, 0x55, 0x04, 0x05]; // OID 2.5.4.5
            for (let i = 0; i < bytes.length - oid.length - 2; i++) {
                let ok = true;
                for (let k = 0; k < oid.length; k++) {
                    if (bytes[i + k] !== oid[k]) { ok = false; break; }
                }
                if (!ok) continue;
                let j = i + oid.length;
                const tag = bytes[j++];
                if (tag !== 0x13 && tag !== 0x0c && tag !== 0x14) continue;
                const len = bytes[j++];
                const value = new TextDecoder("utf-8").decode(
                    bytes.slice(j, j + len),
                );
                const mm = value.match(/(\d{10})/);
                if (mm) return mm[1];
            }
        } catch (e) {
            console.warn("cannot extract ЕГН from cert", e);
        }
        return null;
    }
}
