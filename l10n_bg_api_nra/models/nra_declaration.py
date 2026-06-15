import base64
import logging
import re

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
    )
    # Base declaration type — plug-in modules extend this via selection_add.
    # The "xml" fallback lets the base be usable on its own; real declaration
    # types are contributed by l10n_bg_api_nra_etz, l10n_bg_api_nra_noi, etc.
    declaration_type = fields.Selection(
        selection=[("xml", "Custom XML")],
        string="Declaration Type",
        required=True,
        readonly=True,
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
    )
    period_year = fields.Char(
        string="Year",
        size=4,
    )

    # ------------------------------------------------------------------
    # File payload
    # ------------------------------------------------------------------

    xml_content = fields.Binary(
        string="File Content",
        attachment=True,
        copy=False,
    )
    xml_filename = fields.Char(
        string="Filename",
        copy=False,
    )

    # ------------------------------------------------------------------
    # NRA response fields (per ApiDeclarationsSubmitOutputDto)
    # ------------------------------------------------------------------

    nra_document_id = fields.Integer(
        string="NRA Document ID",
        readonly=True,
        copy=False,
        tracking=True,
        help="documentId returned by NRA API on successful submission.",
    )
    nra_entry_number = fields.Char(
        string="NRA Entry Number",
        readonly=True,
        copy=False,
        tracking=True,
        help="entryNumber returned by NRA API.",
    )
    nra_entry_date = fields.Char(
        string="NRA Entry Date",
        readonly=True,
        copy=False,
        help="entryDate returned by NRA API.",
    )
    # Keep legacy field names as aliases for compatibility
    nra_doc_number = fields.Char(
        related="nra_entry_number",
        string="NRA Document Number",
        store=False,
    )
    nra_incoming_number = fields.Char(
        related="nra_entry_number",
        string="NRA Incoming Number",
        store=False,
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
    nra_response_html = fields.Html(
        string="NRA Response (HTML)",
        readonly=True,
        copy=False,
        sanitize=False,
        help="Base64-decoded HTML result from NRA status check.",
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
        string="UIC",
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
    # File generation — to be overridden by specific declaration modules
    # ------------------------------------------------------------------

    def _prepare_xml_data(self):
        """Prepare data dict for file generation. Override in subclasses."""
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
                _("No data to generate file for declaration '%s'.", self.name)
            )
        root = self._build_xml_tree(data)
        return etree.tostring(
            root, xml_declaration=True, encoding="UTF-8", pretty_print=True
        )

    def _generate_file_content(self):
        """Generate the file content for NRA submission.

        Returns bytes in the format expected by NRA:
        - TXT for D1/D6
        - XML for ETZ
        Override in subclasses for type-specific formats.
        """
        self.ensure_one()
        # Default: generate XML (correct for ETZ, VAT, VIES)
        return self._generate_xml()

    def _get_file_record_count(self):
        """Return the number of records in the file (for D1/D6 numRecords)."""
        self.ensure_one()
        return 0

    def _build_xml_tree(self, data):
        """Build an lxml Element tree from data dict. Override per type."""
        self.ensure_one()
        raise UserError(
            _(
                "File generation is not implemented for declaration type '%s'.",
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
    # File extension helpers
    # ------------------------------------------------------------------

    def _get_file_extension(self):
        """Return file extension for this declaration type."""
        self.ensure_one()
        from .nra_api_provider import NRA_FILE_TYPES
        return NRA_FILE_TYPES.get(self.declaration_type, "xml")

    def _get_file_name(self):
        """Generate a file name for the declaration."""
        self.ensure_one()
        ext = self._get_file_extension()
        return (
            f"{self.declaration_type}_{self.l10n_bg_uic}"
            f"_{self.period_year}_{self.period_month}.{ext}"
        )

    # ------------------------------------------------------------------
    # Workflow actions
    # ------------------------------------------------------------------

    def action_generate_xml(self):
        """Generate file content and move to 'ready' state."""
        for rec in self:
            if rec.state != "draft":
                raise UserError(
                    _("Can only generate files for declarations in 'Draft' state.")
                )
            file_bytes = rec._generate_file_content()
            rec.write(
                {
                    "xml_content": base64.b64encode(file_bytes),
                    "xml_filename": rec._get_file_name(),
                    "state": "ready",
                }
            )
            rec._snapshot_on_generate()
        return True

    def _snapshot_on_generate(self):
        """Hook: freeze a draft snapshot at XML-generation time.

        No-op in base. Plug-in modules (e.g. ETZ) override this to capture
        the raw export data as an audit snapshot at the moment the file is
        generated.
        """
        self.ensure_one()
        return

    def _check_submittable(self):
        """Raise UserError if the declaration cannot be submitted.

        Plug-in modules override this to add type-specific restrictions
        (e.g. VAT/VIES declarations cannot go through the ETZ endpoint).
        """
        self.ensure_one()
        if self.state not in ("ready", "error"):
            raise UserError(
                _("Can only submit declarations in 'Ready' or 'Error' state.")
            )
        if not self.xml_content:
            raise UserError(
                _("No file content. Please generate the file first.")
            )

    def action_kep_sign_submit(self):
        """Trigger browser-side signing via StampIT LSManager.

        Returns a client action that is handled by the kep_sign_submit
        JS handler registered in the actions registry. The handler talks
        to http://127.0.0.1:8090/signer/* on the user's machine, collects
        the PKCS#7 signature, and posts it back to action_submit_signed
        through the /l10n_bg_api_nra/sign_submit controller.
        """
        self.ensure_one()
        self._check_submittable()
        return {
            "type": "ir.actions.client",
            "tag": "l10n_bg_api_nra.kep_sign_submit",
            "params": {
                "declaration_id": self.id,
                "declaration_name": self.name,
            },
        }

    def action_submit(self):
        """Submit using server-side signing (wallet-stored КЕП or test fallback).

        For browser-side КЕП signing (StampIT LSManager), the frontend
        calls action_submit_signed with the PKCS7 produced locally.
        """
        provider = self.env["nra.api.provider"]
        for rec in self:
            rec._check_submittable()
            file_bytes = base64.b64decode(rec.xml_content)
            try:
                result = provider.submit_declaration(
                    company=rec.company_id,
                    declaration_type=rec.declaration_type,
                    file_content=file_bytes,
                    file_name=rec.xml_filename or rec._get_file_name(),
                    num_records=rec._get_file_record_count() or None,
                    period_month=rec.period_month,
                    period_year=rec.period_year,
                )
                rec._process_submit_response(result)
            except UserError:
                rec.write({"state": "error"})
                raise
        return True

    def action_submit_signed(self, signer_cert_b64, signer_pin,
                             pkcs7_signature_b64):
        """Submit the declaration using an externally-produced PKCS#7 signature.

        Called by the browser-side StampIT integration: the user clicks
        "Sign and Submit" in the Odoo UI, the JavaScript component talks
        to http://127.0.0.1:8090/signer/sign, the user enters their PIN,
        and the resulting PKCS#7 + certificate are passed here.

        :param signer_cert_b64: Base64 DER certificate from the signer's КЕП
        :param signer_pin: ЕГН/ЛНЧ from the cert subject (serialNumber OID)
        :param pkcs7_signature_b64: Base64 PKCS#7 signature of xml_content
        :returns: True on success (declaration moved to 'submitted' state)
        :raises UserError: on validation or API failure
        """
        self.ensure_one()
        self._check_submittable()
        if not (signer_cert_b64 and signer_pin and pkcs7_signature_b64):
            raise UserError(
                _("Signer certificate, PIN and PKCS#7 signature are all required.")
            )

        provider = self.env["nra.api.provider"]
        file_bytes = base64.b64decode(self.xml_content)
        try:
            result = provider.submit_declaration(
                company=self.company_id,
                declaration_type=self.declaration_type,
                file_content=file_bytes,
                file_name=self.xml_filename or self._get_file_name(),
                num_records=self._get_file_record_count() or None,
                period_month=self.period_month,
                period_year=self.period_year,
                signer_cert_b64=signer_cert_b64,
                signer_pin=signer_pin,
                pkcs7_signature_b64=pkcs7_signature_b64,
            )
            self._process_submit_response(result)
        except UserError:
            self.write({"state": "error"})
            raise
        return True

    def get_declaration_type_label(self):
        """Return the human-readable label for the declaration type."""
        self.ensure_one()
        for key, label in self._fields["declaration_type"].selection:
            if key == self.declaration_type:
                return label
        return self.declaration_type

    @api.depends("name", "declaration_type", "period_year", "period_month")
    def _compute_display_name(self):
        """DEF-41: смислен display name — референция + тип + период.

        По подразбиране display_name = name (sequence „ETZ/2026/00068"), който
        в dropdown-и/breadcrumbs не казва нито типа, нито периода. Добавяме
        човешкия етикет на типа и периода mm.yyyy.
        """
        for rec in self:
            parts = [rec.name or "/"]
            type_label = rec.get_declaration_type_label()
            if type_label and type_label != rec.declaration_type:
                parts.append(type_label)
            if rec.period_year and rec.period_month:
                parts.append(
                    "%s.%s" % (rec.period_month.zfill(2), rec.period_year))
            rec.display_name = " — ".join(parts)

    def _process_submit_response(self, result):
        """Process the NRA API response after submission.

        Per ApiDeclarationsSubmitOutputDto, the response contains:
        - entryNumber: входящ номер
        - entryDate: дата на входиране
        - documentId: ID на документ

        :param result: dict from the API
        """
        self.ensure_one()
        vals = {
            "submission_date": fields.Datetime.now(),
            "state": "submitted",
        }
        if isinstance(result, dict):
            vals["nra_document_id"] = result.get("documentId", 0)
            vals["nra_entry_number"] = result.get("entryNumber", "")
            vals["nra_entry_date"] = result.get("entryDate", "")
            _logger.info(
                "Declaration %s submitted: documentId=%s, entryNumber=%s",
                self.name,
                result.get("documentId"),
                result.get("entryNumber"),
            )

        self.write(vals)
        self._promote_snapshot_on_submit()

    def _promote_snapshot_on_submit(self):
        """Hook: promote draft snapshot → final snapshot on submit.

        No-op in base. Called from _process_submit_response right after the
        state→'submitted' write — the single chokepoint both action_submit
        and action_submit_signed funnel through. Plug-in modules override to
        freeze the final audit snapshot.
        """
        self.ensure_one()
        return

    def action_check_status(self):
        """Check the processing status of a submitted declaration."""
        provider = self.env["nra.api.provider"]
        for rec in self:
            if rec.state not in ("submitted", "partially_accepted"):
                raise UserError(
                    _("Can only check status for submitted declarations.")
                )
            if not rec.nra_document_id and not rec.nra_entry_number:
                raise UserError(
                    _(
                        "No NRA document ID or entry number. "
                        "The declaration may not have been submitted correctly."
                    )
                )
            try:
                result = provider.check_declaration_status(
                    company=rec.company_id,
                    document_id=rec.nra_document_id or None,
                    entry_number=rec.nra_entry_number or None,
                    entry_date=rec.nra_entry_date or None,
                )
                rec._process_status_response(result)
            except UserError:
                raise
        return True

    def _process_status_response(self, result):
        """Process the status check response from NRA.

        Per ApiDeclarationsResultOutputDto, the response contains:
        - entryNumber, entryDate
        - base64HtmlResult: Base64-encoded HTML fragment
        - base64FullHtmlResultInfo: Base64-encoded full HTML page
        - base64Result: Base64-encoded non-HTML result
        """
        self.ensure_one()
        if not isinstance(result, dict):
            return

        vals = {}

        # Decode the HTML result
        html_content = ""
        if result.get("base64FullHtmlResultInfo"):
            try:
                html_content = base64.b64decode(
                    result["base64FullHtmlResultInfo"]
                ).decode("utf-8")
            except Exception:
                pass
        elif result.get("base64HtmlResult"):
            try:
                html_content = base64.b64decode(
                    result["base64HtmlResult"]
                ).decode("utf-8")
            except Exception:
                pass

        # Decode non-HTML result
        text_result = ""
        if result.get("base64Result"):
            try:
                text_result = base64.b64decode(
                    result["base64Result"]
                ).decode("utf-8")
            except Exception:
                pass

        if html_content:
            vals["nra_response_html"] = html_content
            vals["nra_response_message"] = html_content
            # Try to detect acceptance status from HTML content
            self._parse_html_status(html_content, vals)
        elif text_result:
            vals["nra_response_message"] = text_result
            self._parse_text_status(text_result, vals)

        if vals:
            self.write(vals)

    def _parse_html_status(self, html_content, vals):
        """Parse the NRA HTML response to determine acceptance status.

        Detects patterns like:
        - "е приета" → accepted
        - "Брой приети ... Брой отхвърлени" → count-based
        - "отхвърлен" → rejected
        - "Общ брой вписани" → for ETZ
        """
        content_lower = html_content.lower()

        # Simple acceptance (e.g. "Декларация образец ХХХ е приета")
        if "е приета" in content_lower and "отхвърлен" not in content_lower:
            vals["state"] = "accepted"
            return

        # D1/D6: Parse "Брой подадени ... Брой приети ... Брой отхвърлени"
        submitted_match = re.findall(
            r"Брой подадени[^:]*:\s*(\d+)", html_content
        )
        accepted_match = re.findall(
            r"Брой приети[^:]*:\s*(\d+)", html_content
        )
        rejected_match = re.findall(
            r"Брой отхвърлени[^:]*:\s*(\d+)", html_content
        )

        if submitted_match and accepted_match:
            total_submitted = sum(int(x) for x in submitted_match)
            total_accepted = sum(int(x) for x in accepted_match)
            total_rejected = sum(int(x) for x in rejected_match) if rejected_match else 0

            vals["total_count"] = total_submitted
            vals["accepted_count"] = total_accepted

            if total_rejected == 0 and total_accepted > 0:
                vals["state"] = "accepted"
            elif total_accepted == 0 and total_rejected > 0:
                vals["state"] = "rejected"
            elif total_accepted > 0 and total_rejected > 0:
                vals["state"] = "partially_accepted"
            return

        # ETZ: Parse "Общ брой вписани ... Общ брой невписани"
        etz_accepted = re.search(
            r"Общ брой вписани[^:]*:\s*(\d+)", html_content
        )
        etz_rejected = re.search(
            r"Общ брой невписани[^:]*:\s*(\d+)", html_content
        )
        if etz_accepted or etz_rejected:
            accepted_n = int(etz_accepted.group(1)) if etz_accepted else 0
            rejected_n = int(etz_rejected.group(1)) if etz_rejected else 0
            vals["accepted_count"] = accepted_n
            vals["total_count"] = accepted_n + rejected_n

            if rejected_n == 0 and accepted_n > 0:
                vals["state"] = "accepted"
            elif accepted_n == 0 and rejected_n > 0:
                vals["state"] = "rejected"
            elif accepted_n > 0 and rejected_n > 0:
                vals["state"] = "partially_accepted"
            return

        # General rejection keywords
        if "отхвърлен" in content_lower:
            vals["state"] = "rejected"

    def _parse_text_status(self, text_content, vals):
        """Parse non-HTML text result (used for DEC_HIGH_FISC_RISK etc.)."""
        try:
            data = __import__("json").loads(text_content)
            if "success" in data:
                vals["state"] = "accepted"
            elif "errors" in data:
                vals["state"] = "rejected"
        except (ValueError, TypeError):
            pass

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
                    "nra_response_html": False,
                }
            )
        return True
