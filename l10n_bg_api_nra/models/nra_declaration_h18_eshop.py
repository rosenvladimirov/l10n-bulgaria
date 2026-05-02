"""
H-18 e-shop audit file declaration (Приложение №38 към Наредба Н-18/2006).

Inherits the base `nra.declaration` workflow so the existing
draft → generated → submitted pipeline + chatter + XSD-validation
infrastructure are reused. The XML payload follows
`data/xsd/dec_audit.xsd` (NRA, last published 06.06.2022).

Submission channel is **manual** (operator downloads XML, signs with
КЕП and uploads via portal.nra.bg "Подаване на стандартизиран
одиторски файл" e-service). The `nra.declaration` API-submission
helpers are intentionally bypassed for this declaration type — NRA
exposes no REST API for the H-18 audit file.
"""

import logging
import os
from datetime import date
from io import BytesIO

from lxml import etree

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.modules.module import get_module_resource

_logger = logging.getLogger(__name__)


# Месеците за period selection (трябва да е low-cardinality за UI).
_MONTH_SELECTION = [
    ("01", "01 — January"), ("02", "02 — February"), ("03", "03 — March"),
    ("04", "04 — April"), ("05", "05 — May"), ("06", "06 — June"),
    ("07", "07 — July"), ("08", "08 — August"), ("09", "09 — September"),
    ("10", "10 — October"), ("11", "11 — November"), ("12", "12 — December"),
]


# Платежни методи по XSD (paym 1-6) — mapping към Odoo payment methods.
PAYMENT_METHOD_SELECTION = [
    ("1", "1 — Payment service under Art. 3 PSA with bank card"),
    ("2", "2 — Electronic money — virtual"),
    ("3", "3 — Courier with cash on delivery"),
    ("4", "4 — Electronic wallet"),
    ("5", "5 — Other payment services (other than 1 and 4)"),
    ("6", "6 — Transfers via bank services"),
]

# Refund payment methods (r_paym 1-4)
REFUND_PAYMENT_SELECTION = [
    ("1", "1 — Payment card"),
    ("2", "2 — Bank transfer"),
    ("3", "3 — Cash"),
    ("4", "4 — Other"),
]


class NraDeclarationH18Eshop(models.Model):
    _inherit = "nra.declaration"

    # Регистрираме новия declaration_type през selection_add — base
    # nra.declaration вече има d1/d6/vat/vies; ние добавяме h18_eshop.
    declaration_type = fields.Selection(
        selection_add=[("h18_eshop", "H-18 Audit File (e-shop)")],
        ondelete={"h18_eshop": "cascade"},
    )

    # ------------------------------------------------------------------
    # Header fields (одиторски файл per Приложение №38)
    # ------------------------------------------------------------------

    eshop_uid = fields.Char(
        string="E-shop UID (NRA)",
        size=10,
        help="Unique e-shop number (Appendix 33 / Art. 52r). "
        "Defaults to the value on the company record.",
    )
    eshop_type = fields.Selection(
        selection=[
            ("1", "Own online shop"),
            ("2", "Online sales platform"),
        ],
        string="E-shop type",
    )
    eshop_domain = fields.Char(
        string="E-shop domain",
        size=200,
        help="Domain or link to the shop — written into <domain_name>.",
    )

    # period_month / period_year са вече дефинирани на nra.declaration
    # base. Reuse-ваме ги тук — не дублираме декларации.

    # ------------------------------------------------------------------
    # Order lines + refund lines
    # ------------------------------------------------------------------

    h18_order_line_ids = fields.One2many(
        "nra.declaration.h18.line",
        "declaration_id",
        string="Orders",
    )
    h18_refund_line_ids = fields.One2many(
        "nra.declaration.h18.refund",
        "declaration_id",
        string="Refunds",
    )

    # Auto-computed totals (preview — actual XML re-computes from lines)
    h18_order_count = fields.Integer(
        string="Orders count",
        compute="_compute_h18_totals",
        store=True,
    )
    h18_refund_count = fields.Integer(
        string="Refunds count",
        compute="_compute_h18_totals",
        store=True,
    )
    h18_total_orders = fields.Float(
        string="Total orders (BGN)",
        compute="_compute_h18_totals",
        store=True,
        digits=(12, 2),
    )
    h18_total_refunds = fields.Float(
        string="Total refunds (BGN)",
        compute="_compute_h18_totals",
        store=True,
        digits=(12, 2),
    )

    @api.depends("h18_order_line_ids.ord_total2",
                 "h18_refund_line_ids.r_amount")
    def _compute_h18_totals(self):
        for rec in self:
            rec.h18_order_count = len(rec.h18_order_line_ids)
            rec.h18_refund_count = len(rec.h18_refund_line_ids)
            rec.h18_total_orders = sum(rec.h18_order_line_ids.mapped("ord_total2"))
            rec.h18_total_refunds = sum(rec.h18_refund_line_ids.mapped("r_amount"))

    # ------------------------------------------------------------------
    # Defaults from company
    # ------------------------------------------------------------------

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("declaration_type") == "h18_eshop":
                company = self.env["res.company"].browse(
                    vals.get("company_id") or self.env.company.id)
                vals.setdefault("eshop_uid", company.l10n_bg_eshop_uid or "")
                vals.setdefault("eshop_type", company.l10n_bg_eshop_type or "1")
                vals.setdefault("eshop_domain", company.l10n_bg_eshop_domain or "")
        return super().create(vals_list)

    # ------------------------------------------------------------------
    # Source: collect orders from sale.order (Website module)
    # ------------------------------------------------------------------

    def action_collect_h18_orders(self):
        """Pull online orders for `period_month/period_year` from
        sale.order (records that came through the website — `website_id`
        is set) and have at least one delivered move in the period.
        Each sale.order becomes one h18 order-line; its order lines
        become art-lines.
        """
        self.ensure_one()
        if self.declaration_type != "h18_eshop":
            raise UserError(_("Only valid on H-18 e-shop declarations."))
        if not self.period_month or not self.period_year:
            raise UserError(_("Set period (month + year) first."))

        period_start = date(int(self.period_year),
                            int(self.period_month), 1)
        next_month = (int(self.period_month) % 12) + 1
        next_year = int(self.period_year) + (1 if next_month == 1 else 0)
        period_end = date(next_year, next_month, 1)

        SaleOrder = self.env.get("sale.order")
        if SaleOrder is None:
            raise UserError(_("Module `sale_management` is not installed."))

        # Online orders only — `website_id` is set ONLY on website-eCom
        # ones; physical POS / backend sales are excluded.
        domain = [
            ("company_id", "=", self.company_id.id),
            ("state", "in", ("sale", "done")),
            ("website_id", "!=", False),
            ("date_order", ">=", period_start),
            ("date_order", "<", period_end),
        ]
        orders = SaleOrder.search(domain)

        # Wipe any previous lines on this declaration to avoid dupes
        self.h18_order_line_ids.unlink()
        self.h18_refund_line_ids.unlink()

        Line = self.env["nra.declaration.h18.line"]
        Art = self.env["nra.declaration.h18.line.art"]
        for so in orders:
            invoice = so.invoice_ids[:1] if so.invoice_ids else None
            line = Line.create({
                "declaration_id": self.id,
                "ord_n": so.name[:300],
                "ord_d": so.date_order.date() if so.date_order else False,
                "doc_n": invoice.id if invoice else 0,
                "doc_date": invoice.invoice_date if invoice else so.date_order.date(),
                "ord_total1": so.amount_untaxed,
                "ord_disc": 0.0,
                "ord_vat": so.amount_tax,
                "ord_total2": so.amount_total,
                "paym": "1",  # default; user adjusts per row
                "trans_n": (so.transaction_ids[:1].provider_reference
                             if so.transaction_ids else ""),
            })
            for sol in so.order_line.filtered(lambda l: l.product_id):
                price_unit = sol.price_unit
                vat_rate = int(round(
                    sum((sol.tax_id.mapped("amount") or [0]))))
                Art.create({
                    "line_id": line.id,
                    "art_name": (sol.product_id.display_name or "")[:200],
                    "art_quant": sol.product_uom_qty,
                    "art_price": price_unit,
                    "art_vat_rate": vat_rate,
                    "art_vat": sol.price_tax,
                    "art_sum": sol.price_total,
                })

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "type": "success",
                "message": _("Collected %s orders for %s/%s.") % (
                    len(orders), self.period_month, self.period_year),
            },
        }

    # ------------------------------------------------------------------
    # XML generation per dec_audit.xsd
    # ------------------------------------------------------------------

    def _h18_build_xml(self):
        """Return the audit XML as bytes (CP-1251) per Приложение №38."""
        self.ensure_one()
        if not self.eshop_uid:
            raise UserError(_("E-shop UID (НАП) is required."))
        if not self.eshop_domain:
            raise UserError(_("E-shop domain is required."))
        if not self.period_month or not self.period_year:
            raise UserError(_("Period (month + year) is required."))

        nsmap = {}  # XSD has no namespace
        root = etree.Element("audit", nsmap=nsmap)

        def _add(parent, tag, text):
            el = etree.SubElement(parent, tag)
            el.text = "" if text is None else str(text)
            return el

        _add(root, "eik", (self.company_id.vat or "").lstrip("BGbg"))
        _add(root, "e_shop_n", self.eshop_uid)
        _add(root, "domain_name", self.eshop_domain[:200])
        _add(root, "e_shop_type", self.eshop_type or "1")
        _add(root, "creation_date", fields.Date.today().isoformat())
        _add(root, "mon", self.period_month)
        _add(root, "god", str(self.period_year))

        order_root = etree.SubElement(root, "order")
        for ol in self.h18_order_line_ids:
            ord_el = etree.SubElement(order_root, "orderenum")
            _add(ord_el, "ord_n", ol.ord_n)
            _add(ord_el, "ord_d", ol.ord_d.isoformat() if ol.ord_d else "")
            _add(ord_el, "doc_n", str(ol.doc_n or 0))
            _add(ord_el, "doc_date",
                 ol.doc_date.isoformat() if ol.doc_date else "")
            art_el = etree.SubElement(ord_el, "art")
            for art in ol.art_line_ids:
                a = etree.SubElement(art_el, "artenum")
                _add(a, "art_name", art.art_name[:200])
                _add(a, "art_quant", "%.2f" % art.art_quant)
                _add(a, "art_price", "%.2f" % art.art_price)
                _add(a, "art_vat_rate", str(int(art.art_vat_rate)))
                _add(a, "art_vat", "%.2f" % art.art_vat)
                _add(a, "art_sum", "%.2f" % art.art_sum)
            _add(ord_el, "ord_total1", "%.2f" % ol.ord_total1)
            _add(ord_el, "ord_disc", "%.2f" % ol.ord_disc)
            _add(ord_el, "ord_vat", "%.2f" % ol.ord_vat)
            _add(ord_el, "ord_total2", "%.2f" % ol.ord_total2)
            _add(ord_el, "paym", ol.paym or "1")
            if ol.pos_n:
                _add(ord_el, "pos_n", ol.pos_n[:200])
            if ol.trans_n:
                _add(ord_el, "trans_n", ol.trans_n[:200])
            if ol.proc_id:
                _add(ord_el, "proc_id", ol.proc_id[:200])

        if self.h18_refund_line_ids:
            _add(root, "r_ord", str(len(self.h18_refund_line_ids)))
            r_root = etree.SubElement(root, "rorder")
            r_total = 0.0
            for rl in self.h18_refund_line_ids:
                r_el = etree.SubElement(r_root, "rorderenum")
                _add(r_el, "r_ord_n", rl.r_ord_n)
                _add(r_el, "r_amount", "%.2f" % rl.r_amount)
                _add(r_el, "r_date",
                     rl.r_date.isoformat() if rl.r_date else "")
                _add(r_el, "r_paym", rl.r_paym or "1")
                r_total += rl.r_amount
            _add(root, "r_total", "%.2f" % r_total)

        return etree.tostring(
            root,
            xml_declaration=True,
            encoding="WINDOWS-1251",
            pretty_print=True,
        )

    def _h18_validate_xml(self, xml_bytes):
        """Validate against bundled dec_audit.xsd. Raises on failure."""
        xsd_path = get_module_resource(
            "l10n_bg_api_nra", "data", "xsd", "dec_audit.xsd")
        if not xsd_path or not os.path.exists(xsd_path):
            _logger.warning("dec_audit.xsd not found — skipping validation")
            return
        with open(xsd_path, "rb") as f:
            schema_doc = etree.parse(f)
        schema = etree.XMLSchema(schema_doc)
        doc = etree.parse(BytesIO(xml_bytes))
        if not schema.validate(doc):
            errors = "; ".join(str(e) for e in schema.error_log)
            raise ValidationError(
                _("XML does not validate against dec_audit.xsd:\n%s") % errors)

    # ------------------------------------------------------------------
    # Public actions (UI)
    # ------------------------------------------------------------------

    def action_h18_generate_xml(self):
        """Generate + validate + attach XML to chatter. Sets state to
        'generated'. The user then downloads from the attachment and
        uploads to portal.nra.bg manually (НАП provides no API for
        H-18 audit submissions).
        """
        self.ensure_one()
        if self.declaration_type != "h18_eshop":
            raise UserError(_("Only valid on H-18 e-shop declarations."))
        xml_bytes = self._h18_build_xml()
        self._h18_validate_xml(xml_bytes)

        filename = "audit_%s_%s_%s.xml" % (
            self.eshop_uid or "ESHOP",
            self.period_year,
            self.period_month,
        )
        attachment = self.env["ir.attachment"].create({
            "name": filename,
            "res_model": self._name,
            "res_id": self.id,
            "type": "binary",
            "raw": xml_bytes,
            "mimetype": "application/xml",
        })
        self.message_post(
            body=_("Generated H-18 audit XML — %s orders, %s refunds.") % (
                len(self.h18_order_line_ids),
                len(self.h18_refund_line_ids),
            ),
            attachment_ids=[attachment.id],
        )
        if hasattr(self, "state"):
            try:
                self.state = "generated"
            except Exception:
                pass
        return {
            "type": "ir.actions.act_url",
            "url": "/web/content/%s?download=1" % attachment.id,
            "target": "self",
        }
