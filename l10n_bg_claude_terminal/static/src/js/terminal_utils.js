/** @odoo-module **/
// Copyright 2026 Rosen Vladimirov <vladimirov.rosen@gmail.com>
// License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

/**
 * Build the URL for the external multi-user terminal.
 * Uses ttyd's ?arg=KEY=VALUE format for passing parameters.
 *
 * @param {string} terminalUrl - Base terminal URL
 * @param {Object} odooConfig - {url, db, username, protocol}
 * @param {string} apiKey - User's Odoo API key
 * @param {string} model - Current Odoo model
 * @param {number|boolean} resId - Current record ID
 * @param {string} [theme] - Terminal color theme name
 * @param {string} [anthropicApiKey] - Anthropic API key for pre-auth
 * @returns {string} Full URL with authentication parameters
 */
export function buildExternalTerminalUrl(terminalUrl, odooConfig, apiKey, model, resId, theme, anthropicApiKey) {
    const base = (terminalUrl || "").replace(/\/+$/, "");
    const odoo = odooConfig || {};
    const params = new URLSearchParams();
    params.append("arg", `API_KEY=${apiKey || ""}`);
    params.append("arg", `ODOO_URL=${odoo.url || window.location.origin}`);
    params.append("arg", `ODOO_DB=${odoo.db || ""}`);
    params.append("arg", `ODOO_USER=${odoo.username || ""}`);
    params.append("arg", `ODOO_PROTOCOL=${odoo.protocol || "xmlrpc"}`);
    params.append("arg", `ODOO_MODEL=${model || ""}`);
    params.append("arg", `ODOO_RES_ID=${resId || 0}`);
    if (theme) {
        params.append("arg", `CLAUDE_THEME=${theme}`);
    }
    if (anthropicApiKey) {
        params.append("arg", `ANTHROPIC_API_KEY=${anthropicApiKey}`);
    }
    return `${base}/?${params.toString()}`;
}
