import base64
import logging

from lxml import etree

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)

NRA_DECLARATION_STATES = [
    ("draft", "Draft"),
    ("ready", "Ready"),
    ("submitted", "Submitted"),
    ("accepted", "Accepted"),
    ("partially_accepted", "Partially Accepted"),
    ("rejected", "Rejected"),
    ("error", "Error"),
]


class NraDeclaration(models.Model):
    _name = "nra.declaration"
    _description = "NRA Declaration"
    _order = "create_date desc"
    _inherit = ["mail.thread", "mail.activity.mixin"]

    # ------------------------------------------------------------------
    # Core fields
    # ------------------------------------------------------------------

    name = fields.Char(
        string="Reference",
        required=True,
        readonly=True,
        default="/",
        copy=False,
        tracking=True,
    )
    company_id = fields.Many2one(
        "res.company",
        string="Company",
        required=True,
        default=lambda self: self.env.company,
        readonly=True,
        states={"draft": [("readonly", False)]},
    )
    declaration_type = fields.Selection(
        selection=[
            ("d1", "Декларация обр. 1"),
            ("d6", "Декларация обр. 6"),
            ("etz", "Електронни трудови записи"),
            ("vat", "ДДС декларация"),
            ("vies", "VIES декларация"),
        ],
        string="Declaration Type",
        required=True,
        readonly=True,
        states={"draft": [("readonly", False)]},
        tracking=True,
    )
    state = fields.Selection(
        selection=NRA_DECLARATION_STATES,
        string="Status",
        default="draft",
        required=True,
        readonly=True,
        copy=False,
        tracking=True,
    )

    # ------------------------------------------------------------------
    # Period
    # ------------------------------------------------------------------

    period_month = fields.Selection(
        selection=[
            ("1", "January"),
            ("2", "February"),
            ("3", "March"),
            ("4", "April"),
            ("5", "May"),
            ("6", "June"),
            ("7", "July"),
            ("8", "August"),
            ("9", "September"),
            ("10", "October"),
            ("11", "November"),
            ("12", "December"),
        ],
        string="Month",
        readonly=True,
        states={"draft": [("readonly", False)]},
    )
    period_year = fields.Char(
        string="Year",
        size=4,
        readonly=True,
        states={"draft": [("readonly", False)]},
    )

    # ------------------------------------------------------------------
    # XML payload
    # ------------------------------------------------------------------

    xml_content = fields.Binary(
        string="XML Content",
        attachment=True,
        copy=False,
    )
    xml_filename = fields.Char(
        string="XML Filename",
        copy=False,
    )

    # ------------------------------------------------------------------
    # NRA response
    # ------------------------------------------------------------------

    nra_doc_number = fields.Char(
        string="NRA Document Number",
        readonly=True,
        copy=False,
        tracking=True,
    )
    nra_incoming_number = fields.Char(
        string="NRA Incoming Number",
        readonly=True,
        copy=False,
        tracking=True,
    )
    submission_date = fields.Datetime(
        string="Submission Date",
        readonly=True,
        copy=False,
    )
    nra_response_message = fields.Text(
        string="NRA Response",
        readonly=True,
        copy=False,
    )
    accepted_count = fields.Integer(
        string="Accepted Records",
        readonly=True,
        copy=False,
    )
    total_count = fields.Integer(
        string="Total Records",
        readonly=True,
        copy=False,
    )

    # ------------------------------------------------------------------
    # Computed
    # ------------------------------------------------------------------

    l10n_bg_uic = fields.Char(
        related="company_id.l10n_bg_uic",
        string="UIC (ЕИК)",
    )

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", "/") == "/":
                dec_type = vals.get("declaration_type", "dec")
                vals["name"] = self.env["ir.sequence"].next_by_code(
                    f"nra.declaration.{dec_type}"
                ) or self.env["ir.sequence"].next_by_code("nra.declaration")
        return super().create(vals_list)

    # ------------------------------------------------------------------
    # XML generation — to be overridden by specific declaration modules
    # ------------------------------------------------------------------

    def _prepare_xml_data(self):
        """Prepare data dict for XML generation. Override in subclasses."""
        self.ensure_one()
        return {}

    def _generate_xml(self):
        """Generate XML content from declaration data.

        Override in specific declaration models to produce the correct
        XML structure per the NRA XSD schema for each type.

        :returns: bytes — serialised XML
        """
        self.ensure_one()
        data = self._prepare_xml_data()
        if not data:
            raise UserError(
                _("No data to generate XML for declaration '%s'.", self.name)
            )
        root = self._build_xml_tree(data)
        return etree.tostring(
            root, xml_declaration=True, encoding="UTF-8", pretty_print=True
        )

    def _build_xml_tree(self, data):
        """Build an lxml Element tree from data dict. Override per type."""
        self.ensure_one()
        raise UserError(
            _(
                "XML generation is not implemented for declaration type '%s'.",
                self.declaration_type,
            )
        )

    def _validate_xml(self, xml_bytes, xsd_content=None):
        """Validate XML against an XSD schema.

        :param xml_bytes: XML content as bytes
        :param xsd_content: XSD schema as bytes (optional)
        :returns: True if valid
        :raises ValidationError: if validation fails
        """
        if not xsd_content:
            return True
        try:
            schema_doc = etree.fromstring(xsd_content)
            schema = etree.XMLSchema(schema_doc)
            doc = etree.fromstring(xml_bytes)
            schema.assertValid(doc)
        except etree.XMLSchemaError as exc:
            raise ValidationError(
                _("XML validation error: %s", exc)
            ) from exc
        except etree.XMLSyntaxError as exc:
            raise ValidationError(
                _("XML syntax error: %s", exc)
            ) from exc
        return True

    # ------------------------------------------------------------------
    # API endpoint mapping — override per declaration type
    # ------------------------------------------------------------------

    def _get_submit_endpoint(self):
        """Return the API endpoint path for submitting this declaration."""
        self.ensure_one()
        endpoints = {
            "d1": "/api/declarations/d1",
            "d6": "/api/declarations/d6",
            "etz": "/api/declarations/etz",
            "vat": "/api/declarations/vat",
            "vies": "/api/declarations/vies",
        }
        return endpoints.get(self.declaration_type, "/api/declarations")

    def _get_status_endpoint(self):
        """Return the API endpoint for checking declaration status."""
        self.ensure_one()
        return f"{self._get_submit_endpoint()}/status"

    # ------------------------------------------------------------------
    # Workflow actions
    # ------------------------------------------------------------------

    def action_generate_xml(self):
        """Generate XML and move to 'ready' state."""
        for rec in self:
            if rec.state != "draft":
                raise UserError(
                    _("Can only generate XML for declarations in 'Draft' state.")
                )
            xml_bytes = rec._generate_xml()
            rec.write(
                {
                    "xml_content": base64.b64encode(xml_bytes),
                    "xml_filename": f"{rec.declaration_type}_{rec.l10n_bg_uic}_{rec.period_year}_{rec.period_month}.xml",
                    "state": "ready",
                }
            )
        return True

    def action_submit(self):
        """Submit the declaration XML to the NRA API."""
        provider = self.env["nra.api.provider"]
        for rec in self:
            if rec.state not in ("ready", "error"):
                raise UserError(
                    _(
                        "Can only submit declarations in 'Ready' or 'Error' state."
                    )
                )
            if not rec.xml_content:
                raise UserError(
                    _("No XML content. Please generate XML first.")
                )
            xml_bytes = base64.b64decode(rec.xml_content)
            endpoint = rec._get_submit_endpoint()

            try:
                result = provider.submit_declaration(
                    rec.company_id, endpoint, xml_bytes
                )
                rec._process_submit_response(result)
            except UserError:
                rec.write({"state": "error"})
                raise
        return True

    def _process_submit_response(self, result):
        """Process the NRA API response after submission.

        Override to handle declaration-type-specific response fields.

        :param result: dict or Response from the API
        """
        self.ensure_one()
        vals = {
            "submission_date": fields.Datetime.now(),
            "state": "submitted",
        }
        if isinstance(result, dict):
            vals["nra_doc_number"] = result.get("doc_number", result.get("documentNumber", ""))
            vals["nra_incoming_number"] = result.get(
                "incoming_number", result.get("incomingNumber", "")
            )
            vals["nra_response_message"] = result.get(
                "message", result.get("status", "")
            )

            # Detect accepted/rejected from immediate response
            status = result.get("status", "").lower()
            if status in ("accepted", "приет"):
                vals["state"] = "accepted"
            elif status in ("rejected", "отхвърлен"):
                vals["state"] = "rejected"
            elif "приет" in str(result.get("status", "")):
                # Partial acceptance: "Приет (X/Y)"
                vals["state"] = "partially_accepted"
                self._parse_partial_acceptance(result, vals)

        self.write(vals)

    def _parse_partial_acceptance(self, result, vals):
        """Parse 'Приет (X/Y)' format for partial acceptance."""
        import re

        status_str = str(result.get("status", ""))
        match = re.search(r"\((\d+)/(\d+)\)", status_str)
        if match:
            vals["accepted_count"] = int(match.group(1))
            vals["total_count"] = int(match.group(2))

    def action_check_status(self):
        """Check the processing status of a submitted declaration."""
        provider = self.env["nra.api.provider"]
        for rec in self:
            if rec.state not in ("submitted", "partially_accepted"):
                raise UserError(
                    _("Can only check status for submitted declarations.")
                )
            if not rec.nra_doc_number:
                raise UserError(
                    _(
                        "No NRA document number. "
                        "The declaration may not have been submitted correctly."
                    )
                )
            endpoint = rec._get_status_endpoint()
            try:
                result = provider.check_declaration_status(
                    rec.company_id, endpoint, rec.nra_doc_number
                )
                rec._process_status_response(result)
            except UserError:
                raise
        return True

    def _process_status_response(self, result):
        """Process the status check response from NRA."""
        self.ensure_one()
        if not isinstance(result, dict):
            return
        vals = {}
        status = result.get("status", "").lower()
        if status in ("accepted", "приет"):
            vals["state"] = "accepted"
        elif status in ("rejected", "отхвърлен"):
            vals["state"] = "rejected"

        message = result.get("message", result.get("details", ""))
        if message:
            vals["nra_response_message"] = message

        if vals:
            self.write(vals)

    def action_reset_to_draft(self):
        """Reset declaration back to draft state."""
        for rec in self:
            if rec.state in ("submitted", "accepted"):
                raise UserError(
                    _(
                        "Cannot reset a declaration that has been submitted "
                        "or accepted by NRA."
                    )
                )
            rec.write(
                {
                    "state": "draft",
                    "nra_response_message": False,
                }
            )
        return True
