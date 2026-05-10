"""
HTTP controller for the standalone External Shift dashboard frontend.

The frontend is a self-contained OWL app — it does NOT live inside
the backend chrome. We render raw HTML directly here (mirrors the
`point_of_sale.controllers.main.PosController.pos_web()` approach
of returning a Response with raw HTML) instead of going through a
QWeb template, so we get full control over the boot sequence and
no XML-parser fights with HTML5 `<!DOCTYPE html>` inside templates.
"""

import json
import logging

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


_HTML_TEMPLATE = """<!DOCTYPE html>
<html data-shift-id="{shift_id}"
      data-user-id="{user_id}"
      data-company-id="{company_id}">
<head>
    <meta charset="utf-8"/>
    <title>External Shift — {company_name_html}</title>
    <meta http-equiv="X-UA-Compatible" content="IE=edge"/>
    <meta name="viewport" content="width=device-width, initial-scale=1"/>
    <link rel="icon" sizes="any" type="image/svg+xml"
          href="/web/image/res.company/{company_id}/favicon"/>
    <script type="text/javascript">
        // MUST be set BEFORE the asset bundle loads — the OWL app
        // reads it inside its setup() hook. Using window.* (not odoo.*)
        // because the `odoo` global is defined later by the bundle.
        window.__externalShiftConfig__ = {config_json};
    </script>
    {assets}
</head>
<body class="o_external_shift_body">
    <div id="external_shift_root" class="o_external_shift_root">
        <div class="o_external_shift_loading
                    d-flex align-items-center justify-content-center vh-100">
            <div class="text-center">
                <div class="spinner-border text-primary mb-3" role="status">
                    <span class="visually-hidden">Loading…</span>
                </div>
                <div>External Shift Dashboard loading…</div>
            </div>
        </div>
    </div>
</body>
</html>
"""


class ExternalShiftController(http.Controller):

    @http.route(
        ["/external-shift", "/external-shift/<int:shift_id>"],
        type="http", auth="user", website=False,
    )
    def external_shift_app(self, shift_id=None, **kwargs):
        """Render the External Shift dashboard shell page.

        :param shift_id: optional integer — pre-select this shift on
            app boot. Falsy = blank state, operator picks device then
            clicks Open Shift.
        """
        if not shift_id and "shift_id" in (kwargs or {}):
            try:
                shift_id = int(kwargs.get("shift_id") or 0) or None
            except (ValueError, TypeError):
                shift_id = None

        if shift_id:
            shift = request.env["l10n.bg.fiscal.shift"].browse(shift_id)
            try:
                shift.check_access_rights("read")
                shift.check_access_rule("read")
                if not shift.exists():
                    shift_id = None
            except Exception:  # noqa: BLE001
                _logger.info(
                    "User %s denied access to shift %s; rendering blank "
                    "frontend.",
                    request.env.user.login, shift_id,
                )
                shift_id = None

        company = request.env.company
        user = request.env.user
        config = {
            "shift_id": shift_id or 0,
            "user_id": user.id,
            "user_name": user.name,
            "company_id": company.id,
            "company_name": company.name,
        }

        # Load the dedicated bundle. Odoo's IrAsset.get_asset_bundle
        # returns the asset URLs; we splat them into <link>/<script>
        # tags ourselves.
        IrAsset = request.env["ir.asset"]
        try:
            assets_html = request.env["ir.qweb"]._get_asset_nodes(
                "l10n_bg_erp_net_fp.external_shift_assets",
                {"defer_load": False, "lazy_load": False},
            )
            # _get_asset_nodes returns list of (tag, attrs, content) tuples.
            html_chunks = []
            for tag, attrs, content in assets_html:
                attrs_str = " ".join(
                    f'{k}="{v}"' for k, v in (attrs or {}).items())
                if content:
                    html_chunks.append(
                        f"<{tag} {attrs_str}>{content}</{tag}>")
                else:
                    html_chunks.append(f"<{tag} {attrs_str}></{tag}>")
            assets_block = "\n".join(html_chunks)
        except Exception:  # noqa: BLE001
            _logger.exception("Failed to render asset bundle")
            assets_block = ""

        import html as _html
        body = _HTML_TEMPLATE.format(
            shift_id=shift_id or 0,
            user_id=user.id,
            company_id=company.id,
            company_name_html=_html.escape(company.name or ""),
            assets=assets_block,
            config_json=json.dumps(config, ensure_ascii=False),
        )
        return request.make_response(
            body,
            headers=[("Content-Type", "text/html; charset=utf-8")],
        )
