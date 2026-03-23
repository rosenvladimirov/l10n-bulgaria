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
    def _request(self, method, endpoint, company, **kwargs):
        """Execute an HTTP request against the NRA API.

        Handles OAuth 2.0 bearer auth, rate limiting (HTTP 429) with
        exponential backoff, and structured error responses.

        :param method: HTTP method (GET, POST, PUT, DELETE)
        :param endpoint: API path (appended to base URL) or full URL
        :param company: res.company record
        :param kwargs: additional arguments passed to requests.request
        :returns: parsed JSON response (dict) or raw Response for non-JSON
        :raises UserError: on unrecoverable API errors
        """
        if endpoint.startswith("http"):
            url = endpoint
        else:
            url = f"{self._get_base_url()}{endpoint}"

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
                    body=resp.text[:200],
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
    def _post(self, endpoint, company, **kwargs):
        return self._request("POST", endpoint, company, **kwargs)

    @api.model
    def _get(self, endpoint, company, **kwargs):
        return self._request("GET", endpoint, company, **kwargs)

    # ------------------------------------------------------------------
    # Declaration submission
    # ------------------------------------------------------------------

    @api.model
    def submit_declaration(self, company, endpoint, xml_content, content_type="application/xml"):
        """Submit an XML declaration to the NRA API.

        :param company: res.company record
        :param endpoint: API endpoint path for the declaration type
        :param xml_content: XML payload as bytes
        :param content_type: MIME type of the payload
        :returns: dict with NRA response data
        """
        return self._post(
            endpoint,
            company,
            data=xml_content,
            headers={
                "Content-Type": content_type,
            },
        )

    @api.model
    def check_declaration_status(self, company, endpoint, doc_number):
        """Check the processing status of a submitted declaration.

        :param company: res.company record
        :param endpoint: API endpoint for status checking
        :param doc_number: NRA document number from submission response
        :returns: dict with status information
        """
        return self._get(
            endpoint,
            company,
            params={"doc_number": doc_number},
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
                result = api.submit_declaration(company, endpoint, xml)
        """
        self._get_access_token(company)
        yield self
