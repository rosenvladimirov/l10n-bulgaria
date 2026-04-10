import base64
import logging

from odoo import _, http
from odoo.exceptions import AccessError, UserError
from odoo.http import request

_logger = logging.getLogger(__name__)


class NraSignController(http.Controller):
    """JSON-RPC endpoints for browser-side КЕП signing via StampIT LSManager.

    The frontend calls these after obtaining a PKCS#7 signature from
    http://127.0.0.1:8090/signer/sign on the user's local machine.
    """

    @http.route(
        "/l10n_bg_api_nra/declaration_content",
        type="json",
        auth="user",
        methods=["POST"],
    )
    def declaration_content(self, declaration_id):
        """Return the XML content of a declaration as Base64.

        The frontend needs this to pass to StampIT's `/signer/sign`
        endpoint. We return the exact same bytes that the backend will
        later include in `fileContentBase64` — otherwise the PKCS#7
        would be computed over a different payload and NRA rejects
        the submission with API_DOCUMENT_SIGNATURE_MISMATCH.
        """
        declaration = request.env["nra.declaration"].browse(int(declaration_id))
        declaration.check_access("read")
        if not declaration.exists():
            raise UserError(_("Declaration not found."))
        if not declaration.xml_content:
            raise UserError(
                _("Declaration has no generated file. Click 'Generate' first.")
            )
        return {
            "declaration_id": declaration.id,
            "name": declaration.name,
            "filename": declaration.xml_filename or declaration._get_file_name(),
            # xml_content is already Base64-encoded in the Binary field
            "content_base64": declaration.xml_content.decode("ascii")
            if isinstance(declaration.xml_content, bytes)
            else declaration.xml_content,
        }

    @http.route(
        "/l10n_bg_api_nra/sign_submit",
        type="json",
        auth="user",
        methods=["POST"],
    )
    def sign_submit(self, declaration_id, signer_cert, signer_pin,
                    pkcs7_signature):
        """Submit a declaration with a browser-provided PKCS#7 signature.

        :param declaration_id: int — nra.declaration ID
        :param signer_cert: Base64 DER cert of the КЕП (from StampIT selectSigner)
        :param signer_pin: ЕГН/ЛНЧ string (from cert subject serialNumber)
        :param pkcs7_signature: Base64 PKCS#7 detached signature (from StampIT sign)
        :returns: dict with state, entry_number, entry_date, document_id
        """
        declaration = request.env["nra.declaration"].browse(int(declaration_id))
        declaration.check_access("write")
        if not declaration.exists():
            raise UserError(_("Declaration not found."))

        _logger.info(
            "sign_submit: decl=%s pin=%s pin_len=%s cert_len=%s pkcs7_len=%s",
            declaration.name,
            signer_pin[:3] + "..." if signer_pin else None,
            len(signer_pin) if signer_pin else 0,
            len(signer_cert) if signer_cert else 0,
            len(pkcs7_signature) if pkcs7_signature else 0,
        )
        declaration.action_submit_signed(
            signer_cert_b64=signer_cert,
            signer_pin=signer_pin,
            pkcs7_signature_b64=pkcs7_signature,
        )

        return {
            "state": declaration.state,
            "entry_number": declaration.nra_entry_number or "",
            "entry_date": declaration.nra_entry_date or "",
            "document_id": declaration.nra_document_id or 0,
            "message": declaration.nra_response_message or "",
        }
