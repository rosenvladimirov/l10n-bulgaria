/** @odoo-module **/
// Copyright 2026 Rosen Vladimirov <vladimirov.rosen@gmail.com>
// License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

/**
 * Build the URL for the external multi-user terminal.
 *
 * The four parameters API_KEY, ODOO_URL, ODOO_DB and ODOO_USER are the
 * credentials the terminal's start-session.sh passes to the MCP server
 * unified-auth middleware (as `Authorization: Bearer <API_KEY>` and
 * `X-Odoo-Url` / `X-Odoo-Db` / `X-Odoo-Login` headers). The MCP server
 * validates them via XMLRPC `common.authenticate` and resolves the
 * caller to a registered profile, so memory_* and user_connection_*
 * tool calls originating inside the iframe are bound to this identity.
 *
 * Values use ttyd's ?arg=KEY=VALUE URL format. URL params are visible
 * in browser history; for MCP unified-auth the API key is validated
 * per-request and can be rotated in `res.users.claude_api_key`.
 *
 * @param {string} terminalUrl - Base terminal URL
 * @param {Object} odooConfig - {url, db, username, protocol}
 * @param {string} apiKey - User's Odoo API key (res.users.claude_api_key)
 * @param {string} model - Current Odoo model (context only)
 * @param {number|boolean} resId - Current record ID (context only)
 * @param {string} [theme] - Terminal color theme name
 * @param {string} [anthropicApiKey] - Anthropic API key for pre-auth
 * @returns {string} Full URL with authentication parameters
 */
export function buildExternalTerminalUrl(terminalUrl, odooConfig, apiKey, model, resId, theme, anthropicApiKey) {
    const base = (terminalUrl || "").replace(/\/+$/, "");
    const odoo = odooConfig || {};
    const params = new URLSearchParams();
    // API_KEY = Odoo/unified ключ (claude_odoo_api_key, идва в odooConfig.api_key) — за
    // start-session.sh XML-RPC authenticate + MCP Bearer. anthropicApiKey остава отделен arg.
    params.append("arg", `API_KEY=${odoo.api_key || ""}`);
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
