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
import zipfile

import requests

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
    _description = "Claude Terminal Setup Wizard (5 steps)"

    state = fields.Selection(
        [
            ("upload", "1. Качете конфигурация"),
            ("review", "2. Прегледайте ключовете"),
            ("users", "3. Изберете потребители"),
            ("apply", "4. Прилагане"),
            ("test", "5. Тестване"),
        ],
        default="upload",
        required=True,
        readonly=True,
    )

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

    # ── Step 3: Users ────────────────────────────────────────────────────
    apply_to_company = fields.Boolean(
        string="Запиши настройки на фирмата",
        default=True,
        help="Записва ключовете в res.company (споделени за всички потребители).",
    )
    user_ids = fields.Many2many(
        "res.users",
        string="Потребители за активиране",
        help="Тези потребители ще получат Anthropic ключа и потребителските настройки.",
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
        order = ["upload", "review", "users", "apply", "test"]
        idx = order.index(self.state)
        if idx > 0:
            self.state = order[idx - 1]
        return self._reopen()

    def action_next(self):
        self.ensure_one()
        if self.state == "upload":
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

    def _reopen(self):
        return {
            "type": "ir.actions.act_window",
            "res_model": self._name,
            "res_id": self.id,
            "view_mode": "form",
            "target": "new",
        }

    # ════════════════════════════════════════════════════════════════════
    # Step 1 → unzip & parse
    # ════════════════════════════════════════════════════════════════════
    def _do_unzip_and_parse(self):
        self.ensure_one()
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
            with zipfile.ZipFile(buf, "r") as zf:
                names = zf.namelist()
                if not names:
                    raise UserError(_("ZIP файлът е празен."))
                # Prefer config.json if present, else first .json file
                target = "config.json" if "config.json" in names else next(
                    (n for n in names if n.endswith(".json")), names[0]
                )
                pwd_bytes = self.zip_password.encode("utf-8")
                payload_bytes = zf.read(target, pwd=pwd_bytes)
        except RuntimeError as e:
            # zipfile raises RuntimeError("Bad password ...") for wrong password
            raise UserError(
                _("Невалидна парола или повреден ZIP файл: %s") % e
            )
        except zipfile.BadZipFile:
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

        if self.user_ids and self.cfg_anthropic_api_key:
            self.user_ids.sudo().write({"claude_api_key": self.cfg_anthropic_api_key})
            applied_users = len(self.user_ids)
            log_lines.append(
                _("✓ Anthropic ключът записан на %d потребител(и): %s")
                % (applied_users, ", ".join(self.user_ids.mapped("login")))
            )
        elif self.user_ids and not self.cfg_anthropic_api_key:
            log_lines.append(
                _("⚠ Anthropic ключ липсва в конфигурацията — потребителите не са обновени.")
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
                    f"{mcp_url}/api/health",
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
