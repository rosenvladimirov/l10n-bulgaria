# Copyright 2026 Rosen Vladimirov <vladimirov.rosen@gmail.com>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
"""
Claude Terminal — 5-step setup wizard.

Standard Odoo wizard pattern: TransientModel + state machine. The user
uploads a password-protected zip (downloaded from MCP server with a
temporary password), reviews the extracted keys, picks which users get
the per-user keys, applies, and tests connectivity.
"""
import base64
import io
import json
import logging

import requests

try:
    import pyzipper
except ImportError:
    pyzipper = None

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


# Keys that go on res.company (single source of truth, shared by all users)
_COMPANY_KEYS = (
    "claude_mcp_url",
    "claude_mcp_token",
    "claude_mcp_client_id",
    "claude_mcp_api_key",
    "claude_qdrant_url",
    "claude_qdrant_api_key",
    "claude_qdrant_collection_prefix",
    "claude_ollama_url",
    "claude_ollama_model",
    "claude_embedding_provider",
    "claude_embedding_api_key",
)

# Keys that go on res.users (per-user, can override company defaults)
_USER_KEYS = (
    "claude_terminal_url",
    "claude_use_external_terminal",
    "claude_api_key",
    "claude_theme",
    "claude_odoo_url",
    "claude_odoo_db",
    "claude_odoo_protocol",
    "claude_odoo_api_key",
    "claude_odoo_verify_ssl",
    "claude_telegram_api_id",
    "claude_telegram_api_hash",
    "claude_telegram_phone",
    "claude_telegram_session",
    "claude_viber_bot_token",
    "claude_viber_bot_name",
    "claude_viber_webhook_url",
    "claude_web_url",
    "claude_web_db",
    "claude_web_login",
    "claude_web_password",
    "claude_mcp_url",
    "claude_mcp_token",
    "claude_mcp_client_id",
    "claude_mcp_api_key",
)


class ClaudeTerminalSetupWizard(models.TransientModel):
    _name = "claude.terminal.setup.wizard"
    _description = "Claude Terminal Setup Wizard (6 steps)"

    state = fields.Selection(
        [
            ("provision", "0. Нова инстанция (опционално)"),
            ("upload", "1. Качете конфигурация"),
            ("review", "2. Прегледайте ключовете"),
            ("users", "3. Изберете потребители"),
            ("apply", "4. Прилагане"),
            ("test", "5. Тестване"),
        ],
        default="provision",
        required=True,
        readonly=True,
    )

    # ── Step 0: Provision new MCP instance (optional) ───────────────────
    create_new_instance = fields.Boolean(
        string="Създай нова MCP инстанция",
        help="Маркирайте ако нямате съществуваща MCP инстанция. Wizard-ът "
             "ще се свърже с v3 provisioning сървъра, ще създаде нова "
             "инстанция за вашата фирма и ще получи готов конфигурационен ZIP.",
    )
    provision_password = fields.Char(
        string="Парола за новата инстанция",
        help="Тази парола ще се ползва за encrypt-ване на ZIP файла. "
             "Запазете я — ще ви трябва ако решите да re-provision-нете "
             "същата инстанция (idempotent retry).",
    )
    provision_email = fields.Char(
        string="Email (за audit)",
        default=lambda self: self.env.user.email or "",
        help="Email на администратора (за audit на v3 server-а).",
    )
    provision_v3_url = fields.Char(
        string="v3 Provisioning URL",
        compute="_compute_provision_settings",
        store=False,
        help="Адресът на v3 provisioning сървъра. Конфигурира се чрез "
             "System Parameter `claude_terminal.provisioning_v3_url`.",
    )
    provision_api_key_set = fields.Boolean(
        string="API key конфигуриран",
        compute="_compute_provision_settings",
        store=False,
        help="True ако System Parameter `claude_terminal.provisioning_api_key` "
             "е попълнен.",
    )
    provision_company_vat = fields.Char(
        string="ДДС номер на фирмата",
        compute="_compute_provision_settings",
        store=False,
        help="Извлича се от res.company.vat. Ползва се като tenant id — "
             "името на client стака, контейнерите и hostname-а ще бъдат "
             "нормализирани от него (напр. BG123456789 → bg123456789, "
             "hostname mcp-bg123456789.mcpworks.net).",
    )
    provision_log = fields.Text(string="Provisioning лог", readonly=True)
    provisioned_client_id = fields.Char(string="Получен Client ID", readonly=True)
    provisioned_mcp_url = fields.Char(string="Получен MCP URL", readonly=True)

    @api.depends("create_new_instance")
    def _compute_provision_settings(self):
        ICP = self.env["ir.config_parameter"].sudo()
        v3_url = ICP.get_param("claude_terminal.provisioning_v3_url", "")
        api_key = ICP.get_param("claude_terminal.provisioning_api_key", "")
        for rec in self:
            rec.provision_v3_url = v3_url
            rec.provision_api_key_set = bool(api_key)
            rec.provision_company_vat = (
                self.env.user.company_id.vat or ""
            ).strip()

    # ── Step 1: Upload ───────────────────────────────────────────────────
    config_file = fields.Binary(
        string="Конфигурационен ZIP файл",
        help="Изтеглен от MCP сървъра с временна парола.",
    )
    config_filename = fields.Char(string="Име на файла")
    zip_password = fields.Char(
        string="Парола на ZIP",
        help="Временната парола, показана от MCP сървъра при изтегляне.",
    )

    # ── Step 2: Review (parsed keys, editable) ───────────────────────────
    parsed_payload = fields.Text(
        string="Извлечен JSON",
        help="Сурова JSON структура от ZIP-а (read-only).",
        readonly=True,
    )
    company_id = fields.Many2one(
        "res.company",
        string="Фирма",
        default=lambda self: self.env.company,
        required=True,
    )

    # Company-level keys — bound to company_id record
    cfg_mcp_url = fields.Char(string="MCP URL")
    cfg_mcp_token = fields.Char(string="MCP Token")
    cfg_mcp_client_id = fields.Char(string="MCP Client ID")
    cfg_mcp_api_key = fields.Char(string="MCP API Key")
    cfg_qdrant_url = fields.Char(string="Qdrant URL")
    cfg_qdrant_api_key = fields.Char(string="Qdrant API Key")
    cfg_qdrant_collection_prefix = fields.Char(string="Qdrant collection prefix")
    cfg_ollama_url = fields.Char(string="Ollama URL")
    cfg_ollama_model = fields.Char(string="Ollama model")
    cfg_embedding_provider = fields.Selection(
        [
            ("anthropic", "Anthropic"),
            ("openai", "OpenAI"),
            ("ollama", "Ollama"),
            ("voyage", "Voyage AI"),
        ],
        string="Embedding provider",
    )
    cfg_embedding_api_key = fields.Char(string="Embedding API Key")
    # Anthropic key — convenience: applied to selected users' claude_api_key
    cfg_anthropic_api_key = fields.Char(string="Anthropic API Key (за потребители)")

    # ── Per-user Claude Terminal stack (applied to each selected user) ───
    cfg_terminal_url = fields.Char(
        string="Claude Terminal URL",
        help="URL на terminal-control-mcp web UI (напр. https://terminal.mcp.odoo-shell.space).",
    )
    cfg_terminal_theme = fields.Selection(
        [
            ("github", "GitHub (Light)"),
            ("solarized-light", "Solarized Light"),
            ("dracula", "Dracula"),
            ("monokai", "Monokai"),
            ("tomorrow-night", "Tomorrow Night"),
            ("gruvbox-dark", "Gruvbox Dark"),
        ],
        string="Terminal тема",
        default="github",
    )

    # ── Per-user Odoo RPC Connector (applied to each selected user) ──────
    external_odoo_url = fields.Char(
        string="Външно Odoo URL",
        default=lambda self: self.env["ir.config_parameter"].sudo().get_param("web.base.url"),
        help="Външният URL на тази Odoo инстанция, който MCP сървърът ще ползва "
             "за RPC връзка обратно към нас. По подразбиране от web.base.url.",
    )
    cfg_odoo_protocol = fields.Selection(
        [("xmlrpc", "XML-RPC (порт 8069/443)"), ("jsonrpc", "JSON-RPC")],
        string="Odoo RPC протокол",
        default="xmlrpc",
    )
    cfg_odoo_verify_ssl = fields.Boolean(
        string="Verify SSL (Odoo)",
        default=True,
        help="Изключете само за self-signed сертификати в dev средата.",
    )

    # ── Step 3: Users ────────────────────────────────────────────────────
    apply_to_company = fields.Boolean(
        string="Запиши настройки на фирмата",
        default=True,
        help="Записва ключовете в res.company (споделени за всички потребители).",
    )
    user_ids = fields.Many2many(
        "res.users",
        string="Потребители за активиране",
        help="Всеки избран потребител получава: Claude Terminal URL/тема, "
             "Anthropic ключ, Odoo URL/db/протокол. ОСТАВА им да генерират "
             "сами Odoo API Key (Account Security → New API Key) и да го "
             "поставят в Odoo RPC Connector → API Key.",
    )

    # ── Step 4: Apply (results) ──────────────────────────────────────────
    apply_log = fields.Text(string="Лог на прилагането", readonly=True)
    applied_company = fields.Boolean(readonly=True)
    applied_user_count = fields.Integer(readonly=True)

    # ── Step 5: Test ─────────────────────────────────────────────────────
    test_log = fields.Text(string="Резултати от теста", readonly=True)
    test_mcp_ok = fields.Boolean(readonly=True)
    test_anthropic_ok = fields.Boolean(readonly=True)
    test_qdrant_ok = fields.Boolean(readonly=True)

    # ════════════════════════════════════════════════════════════════════
    # Step transitions
    # ════════════════════════════════════════════════════════════════════
    def action_back(self):
        self.ensure_one()
        order = ["provision", "upload", "review", "users", "apply", "test"]
        idx = order.index(self.state)
        if idx > 0:
            self.state = order[idx - 1]
        return self._reopen()

    def action_next(self):
        self.ensure_one()
        if self.state == "provision":
            if self.create_new_instance:
                # Call v3 → get ZIP + temp_password → fill upload step fields
                self._do_provision()
                # ZIP ready, jump straight to review (parsing already done)
                self.state = "review"
            else:
                # Skip provisioning, continue to standard upload step
                self.state = "upload"
        elif self.state == "upload":
            self._do_unzip_and_parse()
            self.state = "review"
        elif self.state == "review":
            self.state = "users"
        elif self.state == "users":
            self._do_apply()
            self.state = "apply"
        elif self.state == "apply":
            self._do_test()
            self.state = "test"
        return self._reopen()

    def action_run_tests(self):
        """Public wrapper for the re-test button on step 5 (Odoo 18+ disallows
        XML buttons calling private methods)."""
        self.ensure_one()
        self._do_test()
        return self._reopen()

    def _reopen(self):
        return {
            "type": "ir.actions.act_window",
            "res_model": self._name,
            "res_id": self.id,
            "view_mode": "form",
            "target": "new",
        }

    # ════════════════════════════════════════════════════════════════════
    # Step 0 → provision new instance via v3 server
    # ════════════════════════════════════════════════════════════════════
    def _do_provision(self):
        """POST към v3 /provision, store returned ZIP + parse it inline."""
        self.ensure_one()
        ICP = self.env["ir.config_parameter"].sudo()
        v3_url = (ICP.get_param("claude_terminal.provisioning_v3_url", "") or "").rstrip("/")
        api_key = ICP.get_param("claude_terminal.provisioning_api_key", "") or ""

        if not v3_url:
            raise UserError(_(
                "System Parameter `claude_terminal.provisioning_v3_url` "
                "не е конфигуриран. Settings → Technical → Parameters → System Parameters."
            ))
        if not api_key:
            raise UserError(_(
                "System Parameter `claude_terminal.provisioning_api_key` "
                "не е конфигуриран. Получете ключ от администратора на v3 сървъра."
            ))
        if not self.provision_password or len(self.provision_password) < 8:
            raise UserError(_("Паролата трябва да е поне 8 символа."))

        company_vat = (self.env.user.company_id.vat or "").strip()
        if not company_vat:
            raise UserError(_(
                "Фирмата '%s' няма попълнен ДДС номер. Tenant id-то на "
                "новата MCP инстанция се извлича от ДДС номера. Settings → "
                "Companies → %s → ДДС номер."
            ) % (self.env.user.company_id.name, self.env.user.company_id.name))

        body = {
            "api_key": api_key,
            "password": self.provision_password,
            "email": self.provision_email or self.env.user.email or "",
            "vat": company_vat,                        # primary tenant id
            "slug": self.env.cr.dbname,                # legacy fallback
        }

        try:
            resp = requests.post(
                f"{v3_url}/provision",
                json=body,
                timeout=90,  # provisioning may take 30-60s
            )
        except requests.RequestException as e:
            raise UserError(_("v3 server не отговаря: %s") % e)

        if resp.status_code != 200:
            try:
                err = resp.json()
            except Exception:
                err = {"error": resp.text[:300]}
            raise UserError(
                _("v3 provisioning неуспешно (HTTP %d): %s") % (resp.status_code, err.get("error", "?"))
            )

        result = resp.json()
        # Store the ZIP + use the same provision_password as zip_password.
        self.config_file = result["zip_base64"]
        self.config_filename = result.get("zip_filename", "config.zip")
        self.zip_password = self.provision_password
        self.provisioned_client_id = result.get("client_id")
        self.provisioned_mcp_url = result.get("mcp_url")
        self.provision_log = (
            "Status: %s\n"
            "Client ID: %s\n"
            "MCP URL: %s\n"
            "Elapsed: %ss\n"
            "Dry run: %s"
        ) % (
            result.get("status"),
            result.get("client_id"),
            result.get("mcp_url"),
            result.get("elapsed_s"),
            result.get("dry_run"),
        )
        # Parse the ZIP inline so step 2 can show the values immediately.
        self._do_unzip_and_parse()

    # ════════════════════════════════════════════════════════════════════
    # Step 1 → unzip & parse
    # ════════════════════════════════════════════════════════════════════
    def _do_unzip_and_parse(self):
        self.ensure_one()
        if pyzipper is None:
            raise UserError(_(
                "Липсва Python библиотеката `pyzipper` — нужна е за разкриптиране "
                "на AES-encrypted ZIP файлове. Инсталирайте: pip install pyzipper"
            ))
        if not self.config_file:
            raise UserError(_("Качете ZIP файл преди да продължите."))
        if not self.zip_password:
            raise UserError(_("Въведете паролата на ZIP файла."))

        try:
            raw = base64.b64decode(self.config_file)
        except Exception as e:
            raise UserError(_("Грешка при декодиране на файла: %s") % e)

        try:
            buf = io.BytesIO(raw)
            with pyzipper.AESZipFile(buf, "r") as zf:
                names = zf.namelist()
                if not names:
                    raise UserError(_("ZIP файлът е празен."))
                target = "config.json" if "config.json" in names else next(
                    (n for n in names if n.endswith(".json")), names[0]
                )
                zf.setpassword(self.zip_password.encode("utf-8"))
                payload_bytes = zf.read(target)
        except RuntimeError as e:
            # pyzipper raises RuntimeError("Bad password for file ...") on wrong pwd
            raise UserError(
                _("Невалидна парола или повреден ZIP файл: %s") % e
            )
        except pyzipper.BadZipFile:
            raise UserError(_("Файлът не е валиден ZIP архив."))

        try:
            payload = json.loads(payload_bytes.decode("utf-8"))
        except Exception as e:
            raise UserError(_("Конфигурацията не е валиден JSON: %s") % e)

        if not isinstance(payload, dict):
            raise UserError(_("Конфигурацията трябва да е JSON обект."))

        self.parsed_payload = json.dumps(payload, indent=2, ensure_ascii=False)

        # Map JSON keys → wizard fields. Accepted JSON shapes:
        #   {"company": {...}, "users": {...}}  (preferred)
        #   {flat keys}                          (fallback — all on company + anthropic)
        company_block = payload.get("company") if "company" in payload else payload
        user_block = payload.get("users") or {}

        # Company-level
        self.cfg_mcp_url = company_block.get("claude_mcp_url") or company_block.get("mcp_url")
        self.cfg_mcp_token = company_block.get("claude_mcp_token") or company_block.get("mcp_token")
        self.cfg_mcp_client_id = company_block.get("claude_mcp_client_id") or company_block.get("mcp_client_id")
        self.cfg_mcp_api_key = company_block.get("claude_mcp_api_key") or company_block.get("mcp_api_key")
        self.cfg_qdrant_url = company_block.get("claude_qdrant_url") or company_block.get("qdrant_url")
        self.cfg_qdrant_api_key = company_block.get("claude_qdrant_api_key") or company_block.get("qdrant_api_key")
        self.cfg_qdrant_collection_prefix = (
            company_block.get("claude_qdrant_collection_prefix")
            or company_block.get("qdrant_collection_prefix")
        )
        self.cfg_ollama_url = company_block.get("claude_ollama_url") or company_block.get("ollama_url")
        self.cfg_ollama_model = company_block.get("claude_ollama_model") or company_block.get("ollama_model")
        self.cfg_embedding_provider = (
            company_block.get("claude_embedding_provider") or company_block.get("embedding_provider")
        )
        self.cfg_embedding_api_key = (
            company_block.get("claude_embedding_api_key") or company_block.get("embedding_api_key")
        )
        # Anthropic — usually arrives as user-level but the wizard offers a single
        # convenience field that gets distributed to all selected users.
        self.cfg_anthropic_api_key = (
            user_block.get("claude_api_key")
            or user_block.get("anthropic_api_key")
            or company_block.get("anthropic_api_key")
        )
        # Claude Terminal URL — terminal-control-mcp web UI; per-user field but
        # configured once via the zip/wizard. Falls back to MCP URL host.
        terminal_url = (
            user_block.get("claude_terminal_url")
            or company_block.get("claude_terminal_url")
            or company_block.get("terminal_url")
        )
        if terminal_url:
            self.cfg_terminal_url = terminal_url

    # ════════════════════════════════════════════════════════════════════
    # Step 3/4 → apply
    # ════════════════════════════════════════════════════════════════════
    def _do_apply(self):
        self.ensure_one()
        log_lines = []
        applied_company = False
        applied_users = 0

        if self.apply_to_company:
            company = self.company_id.sudo()
            company_vals = {
                "claude_mcp_url": self.cfg_mcp_url,
                "claude_mcp_token": self.cfg_mcp_token,
                "claude_mcp_client_id": self.cfg_mcp_client_id,
                "claude_mcp_api_key": self.cfg_mcp_api_key,
                "claude_qdrant_url": self.cfg_qdrant_url,
                "claude_qdrant_api_key": self.cfg_qdrant_api_key,
                "claude_qdrant_collection_prefix": self.cfg_qdrant_collection_prefix,
                "claude_ollama_url": self.cfg_ollama_url,
                "claude_ollama_model": self.cfg_ollama_model,
                "claude_embedding_provider": self.cfg_embedding_provider,
                "claude_embedding_api_key": self.cfg_embedding_api_key,
                # Anthropic ключът е ФИРМЕН (1-ви избор за терминала), не per-user.
                "claude_anthropic_api_key": self.cfg_anthropic_api_key,
            }
            # Drop None so we don't wipe existing values that aren't in the upload
            company_vals = {k: v for k, v in company_vals.items() if v}
            if company_vals:
                company.write(company_vals)
                # Mark rotation timestamp (existing helper on res.company)
                if hasattr(company, "action_mark_keys_rotated"):
                    company.action_mark_keys_rotated()
                applied_company = True
                log_lines.append(
                    _("✓ Записани %d полета на фирма %s") % (len(company_vals), company.name)
                )

        if self.user_ids:
            # Write the full per-user Claude Terminal + Odoo RPC Connector stack.
            # claude_odoo_api_key is INTENTIONALLY left blank — each user must
            # generate their own Odoo API Key (Account Security → New API Key)
            # and paste it themselves. Pre-filling would be a credential-leak risk.
            user_vals = {
                "claude_use_external_terminal": True,
                "claude_odoo_db": self.env.cr.dbname,
                "claude_odoo_protocol": self.cfg_odoo_protocol or "xmlrpc",
                "claude_odoo_verify_ssl": self.cfg_odoo_verify_ssl,
            }
            # Anthropic ключът вече се пише на фирмата (company_vals по-горе), не на усера.
            # Per-user claude_api_key остава за ръчен override от самия усер.
            if self.cfg_terminal_url:
                user_vals["claude_terminal_url"] = self.cfg_terminal_url
            if self.cfg_terminal_theme:
                user_vals["claude_theme"] = self.cfg_terminal_theme
            if self.external_odoo_url:
                user_vals["claude_odoo_url"] = self.external_odoo_url

            self.user_ids.sudo().write(user_vals)
            applied_users = len(self.user_ids)
            logins = ", ".join(self.user_ids.mapped("login"))
            log_lines.append(
                _("✓ Конфигурирани %d потребител(и): %s") % (applied_users, logins)
            )
            log_lines.append(_("   Полета: %s") % ", ".join(sorted(user_vals.keys())))
            if not self.cfg_anthropic_api_key:
                log_lines.append(_("   ⚠ Anthropic ключ липсва — НЕ е презаписан."))
            log_lines.append(
                _("   ℹ Всеки потребител трябва сам да генерира Odoo API Key от "
                  "своя профил (Account Security → New API Key) и да го пейства "
                  "в Odoo RPC Connector → API Key.")
            )

        if not log_lines:
            log_lines.append(_("Нищо не е приложено — не сте маркирали company и не сте избрали потребители."))

        self.applied_company = applied_company
        self.applied_user_count = applied_users
        self.apply_log = "\n".join(log_lines)

    # ════════════════════════════════════════════════════════════════════
    # Step 5 → test
    # ════════════════════════════════════════════════════════════════════
    def _do_test(self):
        self.ensure_one()
        log_lines = []
        mcp_ok = False
        anthropic_ok = False
        qdrant_ok = False

        # Test 1: MCP server reachability
        mcp_url = (self.cfg_mcp_url or "").rstrip("/")
        mcp_token = self.cfg_mcp_token
        if mcp_url and mcp_token:
            try:
                r = requests.get(
                    f"{mcp_url}/health",
                    headers={"X-Api-Token": mcp_token},
                    timeout=10,
                )
                if r.status_code == 200:
                    mcp_ok = True
                    log_lines.append(_("✓ MCP сървър: достъпен (%s)") % mcp_url)
                else:
                    log_lines.append(
                        _("✗ MCP сървър върна HTTP %d: %s") % (r.status_code, r.text[:200])
                    )
            except requests.RequestException as e:
                log_lines.append(_("✗ MCP сървър недостъпен: %s") % e)
        else:
            log_lines.append(_("⊘ MCP тест пропуснат (липсва URL или token)"))

        # Test 2: Anthropic API (uses Messages API ping)
        if self.cfg_anthropic_api_key:
            try:
                r = requests.post(
                    "https://api.anthropic.com/v1/messages",
                    headers={
                        "x-api-key": self.cfg_anthropic_api_key,
                        "anthropic-version": "2023-06-01",
                        "content-type": "application/json",
                    },
                    json={
                        "model": "claude-haiku-4-5",
                        "max_tokens": 4,
                        "messages": [{"role": "user", "content": "ping"}],
                    },
                    timeout=15,
                )
                if r.status_code == 200:
                    anthropic_ok = True
                    log_lines.append(_("✓ Anthropic API: ключът работи"))
                else:
                    log_lines.append(
                        _("✗ Anthropic API върна HTTP %d: %s") % (r.status_code, r.text[:200])
                    )
            except requests.RequestException as e:
                log_lines.append(_("✗ Anthropic API недостъпен: %s") % e)
        else:
            log_lines.append(_("⊘ Anthropic тест пропуснат (липсва ключ)"))

        # Test 3: Qdrant collections endpoint
        qdrant_url = (self.cfg_qdrant_url or "").rstrip("/")
        if qdrant_url:
            try:
                headers = {}
                if self.cfg_qdrant_api_key:
                    headers["api-key"] = self.cfg_qdrant_api_key
                r = requests.get(f"{qdrant_url}/collections", headers=headers, timeout=10)
                if r.status_code == 200:
                    qdrant_ok = True
                    log_lines.append(_("✓ Qdrant: достъпен (%s)") % qdrant_url)
                else:
                    log_lines.append(_("✗ Qdrant върна HTTP %d") % r.status_code)
            except requests.RequestException as e:
                log_lines.append(_("✗ Qdrant недостъпен: %s") % e)
        else:
            log_lines.append(_("⊘ Qdrant тест пропуснат (липсва URL)"))

        self.test_mcp_ok = mcp_ok
        self.test_anthropic_ok = anthropic_ok
        self.test_qdrant_ok = qdrant_ok
        self.test_log = "\n".join(log_lines)
