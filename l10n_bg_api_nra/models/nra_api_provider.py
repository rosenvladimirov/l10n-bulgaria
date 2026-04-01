import base64
import json
import logging
import time
from contextlib import contextmanager

import requests

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

NRA_API_BASE_URL = "https://public-api.nra.bg"
NRA_API_TIMEOUT = 30
NRA_MAX_RETRIES = 3
NRA_RETRY_BACKOFF = 1.0

# NRA API endpoint paths (appended to base URL)
NRA_SUBMIT_ENDPOINT_PROD = "/declaration/api-declarations/"
NRA_SUBMIT_ENDPOINT_TEST = "/declaration/api-declarations-test/"
NRA_RESULT_SUFFIX = "result"

# NRA service document types
NRA_SERVICE_DOC_TYPES = {
    "d1": "DEC_1_6",
    "d6": "DEC_1_6",
    "etz": "DEC_ETZ62",
}

# NRA file document types
NRA_FILE_DOC_TYPES = {
    "d1": "DEC_1",
    "d6": "DEC_6",
    "etz": "DEC_ETZ62",
}

# NRA file types per declaration type
NRA_FILE_TYPES = {
    "d1": "txt",
    "d6": "txt",
    "etz": "xml",
}


class NraApiProvider(models.AbstractModel):
    _name = "nra.api.provider"
    _description = "NRA Public API Client"

    # ------------------------------------------------------------------
    # Configuration helpers
    # ------------------------------------------------------------------

    @api.model
    def _get_base_url(self):
        return (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("l10n_bg_api_nra.base_url", NRA_API_BASE_URL)
        )

    @api.model
    def _get_timeout(self):
        return int(
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("l10n_bg_api_nra.timeout", NRA_API_TIMEOUT)
        )

    @api.model
    def _get_submit_endpoint(self, company):
        """Return the full submit endpoint URL based on test/prod mode."""
        base = self._get_base_url()
        if company.l10n_bg_nra_test_mode:
            return f"{base}{NRA_SUBMIT_ENDPOINT_TEST}"
        return f"{base}{NRA_SUBMIT_ENDPOINT_PROD}"

    @api.model
    def _get_result_endpoint(self, company):
        """Return the full result endpoint URL based on test/prod mode."""
        submit_url = self._get_submit_endpoint(company)
        # Ensure trailing slash is handled correctly
        if submit_url.endswith("/"):
            return f"{submit_url}{NRA_RESULT_SUFFIX}"
        return f"{submit_url}/{NRA_RESULT_SUFFIX}"

    # ------------------------------------------------------------------
    # OAuth 2.0 — client credentials grant
    # ------------------------------------------------------------------

    @api.model
    def _get_token_endpoint(self):
        return (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param(
                "l10n_bg_api_nra.token_endpoint",
                f"{self._get_base_url()}/oauth/token",
            )
        )

    @api.model
    def _obtain_access_token(self, company):
        """Obtain an OAuth 2.0 access token using client credentials.

        Reads API key/secret from crypto wallet, obtains a bearer token
        from the NRA token endpoint, and stores it back in the wallet.

        :param company: res.company record with NRA API credentials
        :returns: access token string
        :raises UserError: on authentication failure
        """
        api_key, api_secret = company._nra_get_credentials()

        token_url = self._get_token_endpoint()
        try:
            resp = requests.post(
                token_url,
                data={
                    "grant_type": "client_credentials",
                    "client_id": api_key,
                    "client_secret": api_secret,
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                timeout=self._get_timeout(),
            )
        except requests.RequestException as exc:
            _logger.error("NRA token request failed: %s", exc)
            raise UserError(
                _("Cannot connect to NRA API token endpoint: %s", exc)
            ) from exc

        if resp.status_code == 401:
            raise UserError(
                _(
                    "NRA API authentication failed. "
                    "Please verify the API key and secret for company '%s'.",
                    company.name,
                )
            )
        if resp.status_code != 200:
            _logger.error(
                "NRA token endpoint returned %s: %s",
                resp.status_code,
                resp.text[:500],
            )
            raise UserError(
                _(
                    "NRA API token request failed (HTTP %(code)s): %(body)s",
                    code=resp.status_code,
                    body=resp.text[:200],
                )
            )

        data = resp.json()
        access_token = data.get("access_token")
        expires_in = data.get("expires_in", 3600)

        # Store token in crypto wallet
        company._nra_store_access_token(access_token, expires_in)

        _logger.info(
            "NRA API access token obtained for company %s (expires in %ss)",
            company.name,
            expires_in,
        )
        return access_token

    @api.model
    def _get_access_token(self, company):
        """Return a valid access token, refreshing if expired."""
        token = company._nra_get_access_token()
        if token:
            return token
        return self._obtain_access_token(company)

    # ------------------------------------------------------------------
    # HTTP request with rate-limit retry
    # ------------------------------------------------------------------

    @api.model
    def _request(self, method, url, company, **kwargs):
        """Execute an HTTP request against the NRA API.

        Handles OAuth 2.0 bearer auth, rate limiting (HTTP 429) with
        exponential backoff, and structured error responses.

        :param method: HTTP method (GET, POST, PUT, DELETE)
        :param url: Full API URL
        :param company: res.company record
        :param kwargs: additional arguments passed to requests.request
        :returns: parsed JSON response (dict) or raw Response for non-JSON
        :raises UserError: on unrecoverable API errors
        """
        token = self._get_access_token(company)

        headers = kwargs.pop("headers", {})
        headers["Authorization"] = f"Bearer {token}"
        headers.setdefault("Accept", "application/json")

        timeout = kwargs.pop("timeout", self._get_timeout())
        retries = 0

        while retries <= NRA_MAX_RETRIES:
            try:
                resp = requests.request(
                    method,
                    url,
                    headers=headers,
                    timeout=timeout,
                    **kwargs,
                )
            except requests.RequestException as exc:
                _logger.error("NRA API request error: %s %s → %s", method, url, exc)
                raise UserError(
                    _("NRA API connection error: %s", exc)
                ) from exc

            # Rate limited — back off and retry
            if resp.status_code == 429:
                retries += 1
                if retries > NRA_MAX_RETRIES:
                    raise UserError(
                        _(
                            "NRA API rate limit exceeded after %s retries. "
                            "Please try again later.",
                            NRA_MAX_RETRIES,
                        )
                    )
                retry_after = resp.headers.get("Retry-After")
                if retry_after:
                    try:
                        wait = float(retry_after)
                    except (ValueError, TypeError):
                        wait = NRA_RETRY_BACKOFF * (2 ** (retries - 1))
                else:
                    wait = NRA_RETRY_BACKOFF * (2 ** (retries - 1))
                _logger.warning(
                    "NRA API rate limited (429), retry %s/%s in %.1fs",
                    retries,
                    NRA_MAX_RETRIES,
                    wait,
                )
                time.sleep(wait)
                continue

            # Token expired — refresh once and retry
            if resp.status_code == 401 and retries == 0:
                retries += 1
                token = self._obtain_access_token(company)
                headers["Authorization"] = f"Bearer {token}"
                continue

            break

        if resp.status_code == 401:
            raise UserError(
                _("NRA API authentication failed. Please verify your credentials.")
            )
        if resp.status_code == 403:
            raise UserError(
                _(
                    "NRA API access denied. Your API key may not have "
                    "permission for this service."
                )
            )
        if resp.status_code not in (200, 201, 202, 204):
            # Try to parse NRA ApiError structure
            error_msg = resp.text[:200]
            try:
                error_data = resp.json()
                if error_data.get("errorCode"):
                    error_msg = "%s: %s" % (
                        error_data["errorCode"],
                        error_data.get("i18nMessage", ""),
                    )
                    if error_data.get("errors"):
                        error_msg += " " + "; ".join(error_data["errors"])
            except (ValueError, KeyError):
                pass
            _logger.error(
                "NRA API %s %s → %s: %s",
                method,
                url,
                resp.status_code,
                resp.text[:500],
            )
            raise UserError(
                _(
                    "NRA API error (HTTP %(code)s): %(body)s",
                    code=resp.status_code,
                    body=error_msg,
                )
            )

        if resp.status_code == 204 or not resp.content:
            return {}

        content_type = resp.headers.get("Content-Type", "")
        if "application/json" in content_type:
            return resp.json()
        return resp

    # ------------------------------------------------------------------
    # Convenience methods
    # ------------------------------------------------------------------

    @api.model
    def _post(self, url, company, **kwargs):
        return self._request("POST", url, company, **kwargs)

    @api.model
    def _get(self, url, company, **kwargs):
        return self._request("GET", url, company, **kwargs)

    # ------------------------------------------------------------------
    # Declaration submission (NRA JSON API)
    # ------------------------------------------------------------------

    @api.model
    def submit_declaration(self, company, declaration_type, file_content,
                           file_name, num_records=None, period_month=None,
                           period_year=None):
        """Submit a declaration to the NRA API.

        Builds the ApiDeclarationsSubmitInputDto JSON payload per the
        NRA Swagger specification and POSTs it to the declarations endpoint.

        :param company: res.company record
        :param declaration_type: 'd1', 'd6', or 'etz'
        :param file_content: file payload as bytes
        :param file_name: original file name
        :param num_records: number of records (required for D1/D6)
        :param period_month: tax period month (required for D1/D6)
        :param period_year: tax period year (required for D1/D6)
        :returns: dict with NRA response (entryNumber, entryDate, documentId)
        :raises UserError: on submission failure
        """
        service_doc_type = NRA_SERVICE_DOC_TYPES.get(declaration_type)
        if not service_doc_type:
            raise UserError(
                _(
                    "Declaration type '%(type)s' is not supported by the NRA API.",
                    type=declaration_type,
                )
            )

        file_doc_type = NRA_FILE_DOC_TYPES.get(declaration_type)
        file_type = NRA_FILE_TYPES.get(declaration_type)

        # Get user credentials from wallet
        user_pin, user_signature = company._nra_get_user_credentials()

        # Build file entry
        file_content_b64 = base64.b64encode(file_content).decode("ascii")
        file_entry = {
            "fileName": file_name,
            "fileType": file_type,
            "fileSize": len(file_content),
            "fileContentBase64": file_content_b64,
            "base64EncodedPkcs7": "",  # TODO: PKCS7 signature with КЕП
            "fileDocumentType": file_doc_type,
        }
        if num_records is not None and declaration_type in ("d1", "d6"):
            file_entry["numRecords"] = num_records

        # Build main payload
        payload = {
            "taxpayerPin": company.l10n_bg_uic,
            "taxpayerPinType": company.l10n_bg_nra_taxpayer_pin_type or "BUS_BULSTAT",
            "userPin": user_pin,
            "userPinType": company.l10n_bg_nra_user_pin_type or "IND_EGN",
            "userSignatureBase64": user_signature,
            "serviceDocumentType": service_doc_type,
            "files": [file_entry],
        }

        # Add D1/D6-specific fields
        if declaration_type in ("d1", "d6"):
            if period_month:
                month_str = str(period_month).zfill(2)
                payload["taxPeriodFrom"] = month_str
                payload["taxPeriodTo"] = month_str
            if period_year:
                payload["year"] = str(period_year)
            payload["insuranceFund"] = int(
                company.l10n_bg_nra_insurance_fund or "0"
            )

        url = self._get_submit_endpoint(company)
        _logger.info(
            "Submitting %s declaration for company %s to %s",
            declaration_type,
            company.name,
            url,
        )

        return self._post(
            url,
            company,
            json=payload,
            headers={"Content-Type": "application/json"},
        )

    @api.model
    def check_declaration_status(self, company, document_id=None,
                                 entry_number=None, entry_date=None):
        """Check the processing status of a submitted declaration.

        Per the NRA API, search by documentId OR by entryNumber + entryDate.

        :param company: res.company record
        :param document_id: NRA document ID (integer)
        :param entry_number: NRA entry number (string)
        :param entry_date: NRA entry date (string, YYYY-MM-DD)
        :returns: dict with status information
        :raises UserError: if neither search criterion is provided
        """
        if not document_id and not (entry_number and entry_date):
            raise UserError(
                _(
                    "Either document ID or entry number + entry date "
                    "are required to check declaration status."
                )
            )

        # Get user credentials from wallet
        user_pin, user_signature = company._nra_get_user_credentials()

        payload = {
            "taxpayerPin": company.l10n_bg_uic,
            "taxpayerPinType": company.l10n_bg_nra_taxpayer_pin_type or "BUS_BULSTAT",
            "userPin": user_pin,
            "userPinType": company.l10n_bg_nra_user_pin_type or "IND_EGN",
            "userSignatureBase64": user_signature,
        }

        if document_id:
            payload["documentId"] = int(document_id)
        else:
            payload["entryNumber"] = entry_number
            payload["entryDate"] = entry_date

        url = self._get_result_endpoint(company)
        _logger.info(
            "Checking declaration status for company %s (documentId=%s, "
            "entryNumber=%s) at %s",
            company.name,
            document_id,
            entry_number,
            url,
        )

        return self._post(
            url,
            company,
            json=payload,
            headers={"Content-Type": "application/json"},
        )

    # ------------------------------------------------------------------
    # Session context manager
    # ------------------------------------------------------------------

    @contextmanager
    def _nra_session(self, company):
        """Context manager that ensures a valid token for a batch of calls.

        Usage::

            provider = self.env["nra.api.provider"]
            with provider._nra_session(company) as api:
                result = api.submit_declaration(company, ...)
        """
        self._get_access_token(company)
        yield self
