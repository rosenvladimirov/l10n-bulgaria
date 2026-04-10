/** @odoo-module **/

/**
 * KepSigner — browser-side wrapper around the StampIT LSManager HTTP API.
 *
 * StampIT LSManager is a Java Web Start application (stampitls.jnlp) from
 * portal.nra.bg/ls/ that exposes a local HTTP service on 127.0.0.1:8090
 * and signs data with the user's КЕП (qualified electronic signature).
 *
 * Architecture:
 *   Browser (Odoo UI) ─fetch─> http://127.0.0.1:8090/signer/*  (StampIT)
 *                                  │
 *                                  ├── selectSigner → cert info
 *                                  └── sign → PIN dialog → PKCS7
 *
 * When multiple certificates are available on the card, selectSigner
 * shows a native Swing chooser dialog. Once a signer is picked, we
 * cache its hex serial number and issuerCN so subsequent calls bypass
 * the chooser (the PIN dialog still appears for each sign operation).
 *
 * This module is shared between:
 *   - Variant 1: single-document signing (sign_submit_button.js)
 *   - Variant 2: batch signing (future; uses signFile for multiple docs)
 */

const DEFAULT_STAMPIT_URL = "http://127.0.0.1:8090";
const SIGNER_ROOT = "/signer";

export class KepSignerError extends Error {
    constructor(message, code = null, reasonCode = null) {
        super(message);
        this.name = "KepSignerError";
        this.code = code;
        this.reasonCode = reasonCode;
    }
}

export class KepSigner {
    /**
     * @param {string} [url] - base URL of StampIT LSManager
     */
    constructor(url = DEFAULT_STAMPIT_URL) {
        this.url = url;
        this._cert = null;
        this._signerName = null;
        this._sn = null;
        this._issuerCN = null;
        this._sid = null;
    }

    // ------------------------------------------------------------------
    // Low-level HTTP helpers
    // ------------------------------------------------------------------

    async _post(method, body = {}) {
        let response;
        try {
            response = await fetch(`${this.url}${SIGNER_ROOT}/${method}`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(body),
            });
        } catch (err) {
            throw new KepSignerError(
                `Cannot reach StampIT LSManager at ${this.url}. ` +
                `Make sure the signing component is running.`,
                "STAMPIT_UNREACHABLE",
            );
        }
        if (!response.ok) {
            throw new KepSignerError(
                `StampIT returned HTTP ${response.status}`,
                "HTTP_ERROR",
            );
        }
        const data = await response.json();
        if (data.status !== "ok") {
            // Provide user-friendly messages for common StampIT errors
            let message = data.reasonText || `StampIT ${method} failed`;
            if (data.errorCode === 1) {
                message =
                    "Signing failed (code 1). Possible causes:\n" +
                    "• PIN dialog was cancelled\n" +
                    "• Wrong PIN entered\n" +
                    "• КЕП device disconnected\n\n" +
                    "Check the StampIT icon in the system tray and try again.";
            }
            throw new KepSignerError(
                message,
                data.errorCode,
                data.reasonCode,
            );
        }
        return data;
    }

    // ------------------------------------------------------------------
    // Public API
    // ------------------------------------------------------------------

    /**
     * Check if StampIT LSManager is running and reachable.
     *
     * Returns one of:
     *   { ok: true }                        — signer reachable
     *   { ok: false, reason: "not_running" } — fetch failed, not running
     *   { ok: false, reason: "blocked_pna" } — blocked by Private Network Access
     *
     * Uses a GET request to /signer/ which returns HTTP 400 on a healthy
     * server (because the root endpoint requires a method name in the path).
     * Any non-exception response means the server is up. We avoid OPTIONS
     * because some browsers restrict sending it directly from JS.
     *
     * Note: when fetching from HTTPS to http://127.0.0.1, modern Chrome
     * (94+) requires the target server to respond to the preflight with
     * `Access-Control-Allow-Private-Network: true`. StampIT does not send
     * that header, so requests from HTTPS Odoo can get blocked. Firefox
     * 115+ has a loopback exception and works.
     */
    async isRunning() {
        try {
            const response = await fetch(`${this.url}${SIGNER_ROOT}/`, {
                method: "GET",
                // mode: no-cors so a 400 response doesn't trigger a CORS error
                mode: "no-cors",
            });
            // In no-cors mode the response is opaque — any non-throw means
            // we reached the server.
            return { ok: true };
        } catch (err) {
            // fetch() TypeError — either network unreachable or blocked by
            // mixed content / PNA. If the parent page is HTTPS and the
            // target is HTTP loopback, it's very likely PNA.
            const parentIsHttps = typeof window !== "undefined"
                && window.location
                && window.location.protocol === "https:";
            if (parentIsHttps) {
                return { ok: false, reason: "blocked_pna" };
            }
            return { ok: false, reason: "not_running" };
        }
    }

    /**
     * Select a КЕП signer. If sn/issuerCN are omitted and the card has
     * multiple certificates, StampIT shows a native chooser dialog.
     *
     * The selected signer is cached on this instance so subsequent sign()
     * calls pass the hex serial + issuerCN filter and skip the chooser.
     *
     * @param {object} [filter]
     * @param {string} [filter.sn] - hex serial number of the certificate
     * @param {string} [filter.issuerCN] - CN of the certificate issuer
     * @returns {Promise<object>} { signerName, signerCert (Base64 DER), signerProv, sid }
     */
    async selectSigner({ sn = "", issuerCN = "" } = {}) {
        const body = {};
        if (sn) body.sn = sn;
        if (issuerCN) body.issuerCN = issuerCN;

        const data = await this._post("selectSigner", body);

        this._cert = data.signerCert;
        this._signerName = data.signerName;
        this._sid = data.sid;
        // Extract hex serial + issuerCN from the cert so we can reuse
        // the filter on subsequent sign() calls without the chooser.
        const parsed = this._parseCertFilter(data.signerCert);
        if (parsed) {
            this._sn = parsed.sn;
            this._issuerCN = parsed.issuerCN;
        }
        return data;
    }

    /**
     * Sign content with the previously selected КЕП.
     *
     * IMPORTANT: caller MUST call selectSigner() before sign().
     * This method does NOT call selectSigner internally — it only
     * POSTs to /signer/sign. This prevents the certificate chooser
     * dialog from appearing twice.
     *
     * The only Swing dialog the user sees is the PIN dialog (one
     * per sign operation, inherent to КЕП hardware token).
     *
     * @param {string} contentBase64 - Base64-encoded bytes to sign
     * @returns {Promise<{signature: string, signerCert: string}>}
     */
    async sign(contentBase64) {
        if (!this._cert) {
            throw new KepSignerError(
                "No signer selected. Call selectSigner() first.",
                "NO_SIGNER",
            );
        }

        const data = await this._post("sign", {
            signatureType: "signature",
            content: contentBase64,
            charset: "",
            newline: "",
            compress: false,
        });

        return {
            signature: data.signature,
            signerCert: this._cert,
            signerName: this._signerName,
            signatureAlgorithm: data.signatureAlgorithm,
        };
    }

    /**
     * Clear the currently selected signer. Next selectSigner() call
     * will show the chooser dialog again.
     */
    async clearSigner() {
        try {
            await this._post("clearSigner", {});
        } finally {
            this._cert = null;
            this._signerName = null;
            this._sn = null;
            this._issuerCN = null;
            this._sid = null;
        }
    }

    /** @returns {string|null} Base64 DER of the selected cert */
    getCertificate() {
        return this._cert;
    }

    /** @returns {string|null} Full subject CN of the selected signer */
    getSignerName() {
        return this._signerName;
    }

    // ------------------------------------------------------------------
    // Certificate parsing helpers
    // ------------------------------------------------------------------

    /**
     * Extract the hex serial number and issuer CN from a Base64 DER cert.
     * Uses a minimal ASN.1 walk — no external library needed.
     *
     * @param {string} certBase64
     * @returns {{sn: string, issuerCN: string}|null}
     */
    _parseCertFilter(certBase64) {
        try {
            const der = this._base64ToBytes(certBase64);
            const parsed = this._parseX509(der);
            return parsed;
        } catch (err) {
            console.warn("kep_signer: cannot parse cert for filter caching", err);
            return null;
        }
    }

    _base64ToBytes(b64) {
        const bin = atob(b64);
        const bytes = new Uint8Array(bin.length);
        for (let i = 0; i < bin.length; i++) {
            bytes[i] = bin.charCodeAt(i);
        }
        return bytes;
    }

    /**
     * Very small ASN.1 DER walker — just enough to extract the cert
     * serial number (in hex) and the issuer's CN. Not a full parser.
     */
    _parseX509(der) {
        // Certificate ::= SEQUENCE { tbsCertificate, signatureAlgorithm, signature }
        let idx = 0;
        const readLen = (i) => {
            const first = der[i++];
            if (first < 0x80) return { len: first, next: i };
            const n = first & 0x7f;
            let len = 0;
            for (let k = 0; k < n; k++) len = (len << 8) | der[i++];
            return { len, next: i };
        };
        const skipHeader = (i) => {
            const { next } = readLen(i + 1);
            return next;
        };
        const readTLV = (i) => {
            const tag = der[i];
            const { len, next } = readLen(i + 1);
            return { tag, len, start: next, end: next + len };
        };

        // Outer SEQUENCE
        if (der[0] !== 0x30) return null;
        const outer = readTLV(0);
        // tbsCertificate SEQUENCE
        const tbs = readTLV(outer.start);
        if (tbs.tag !== 0x30) return null;
        let p = tbs.start;

        // Optional [0] version
        if (der[p] === 0xa0) {
            const v = readTLV(p);
            p = v.end;
        }
        // serialNumber INTEGER
        const serial = readTLV(p);
        if (serial.tag !== 0x02) return null;
        let snHex = "";
        for (let i = serial.start; i < serial.end; i++) {
            snHex += der[i].toString(16).padStart(2, "0");
        }
        // Strip leading zero (ASN.1 sign byte) to match what StampIT expects
        snHex = snHex.replace(/^0+/, "") || "0";
        p = serial.end;

        // signature AlgorithmIdentifier
        const sigAlg = readTLV(p);
        p = sigAlg.end;

        // issuer Name SEQUENCE
        const issuer = readTLV(p);
        if (issuer.tag !== 0x30) return null;
        const issuerCN = this._findCNInName(der, issuer.start, issuer.end);

        return { sn: snHex, issuerCN };
    }

    _findCNInName(der, start, end) {
        // Name ::= SEQUENCE OF RelativeDistinguishedName (SET OF AttributeTypeAndValue)
        // commonName OID: 2.5.4.3 → 06 03 55 04 03
        const cnOid = [0x06, 0x03, 0x55, 0x04, 0x03];
        for (let i = start; i < end - cnOid.length; i++) {
            let match = true;
            for (let k = 0; k < cnOid.length; k++) {
                if (der[i + k] !== cnOid[k]) {
                    match = false;
                    break;
                }
            }
            if (!match) continue;
            // Next TLV is the value (UTF8String / PrintableString)
            let j = i + cnOid.length;
            const tag = der[j];
            const { len, next } = this._readLenAt(der, j + 1);
            if (tag === 0x0c || tag === 0x13 || tag === 0x14) {
                const bytes = der.slice(next, next + len);
                return new TextDecoder("utf-8").decode(bytes);
            }
        }
        return "";
    }

    _readLenAt(der, i) {
        const first = der[i++];
        if (first < 0x80) return { len: first, next: i };
        const n = first & 0x7f;
        let len = 0;
        for (let k = 0; k < n; k++) len = (len << 8) | der[i++];
        return { len, next: i };
    }
}

/**
 * Convenience: create a singleton signer for a page. Reusing the same
 * instance between button clicks keeps the cached filter so the chooser
 * dialog only appears once per session even if the user signs several
 * documents one after another.
 */
let _sharedSigner = null;
export function getSharedSigner() {
    if (!_sharedSigner) {
        _sharedSigner = new KepSigner();
    }
    return _sharedSigner;
}
