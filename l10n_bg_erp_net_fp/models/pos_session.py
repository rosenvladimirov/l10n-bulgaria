import json
import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class PosSession(models.Model):
    _inherit = "pos.session"

    l10n_bg_fiscal_printer_id = fields.Many2one(
        'fiscal.printer.device',
        string='Fiscal printer',
        related='config_id.l10n_bg_fiscal_printer_id',
        store=True,
        readonly=True
    )
    l10n_bg_last_x_report = fields.Datetime(
        'Last X report',
        readonly=True
    )
    l10n_bg_z_report_printed = fields.Boolean(
        'Z report printed',
        readonly=True,
        default=False
    )
    l10n_bg_z_report_datetime = fields.Datetime(
        'Z Report Date/Time',
        readonly=True
    )
    l10n_bg_erp_net_fp_ip = fields.Char(
        'ErpNet.FP IP',
        compute='_compute_l10n_bg_erp_net_fp_ip',
        store=True
    )
    l10n_bg_erp_net_fp_host = fields.Char(
        'ErpNet.FP Host',
        compute='_compute_l10n_bg_erp_net_fp_host',
        store=True
    )

    # ─── Per-cashier fiscal-printer credentials ──────────────────
    # Mirrored from the session's `user_id` so the POS frontend can
    # read them without a separate RPC. When empty, the ErpNet.FP
    # server falls back to its config.yaml `operator` / `operator_password`
    # for the targeted printer.
    l10n_bg_fp_operator = fields.Char(
        related='user_id.l10n_bg_fp_operator',
        string='Cashier operator code',
        readonly=True,
        store=False,
    )
    l10n_bg_fp_operator_password = fields.Char(
        related='user_id.l10n_bg_fp_operator_password',
        string='Cashier operator password',
        readonly=True,
        store=False,
    )

    @api.depends('l10n_bg_fiscal_printer_id', 'l10n_bg_fiscal_printer_id.printer_id')
    def _compute_l10n_bg_erp_net_fp_ip(self):
        for config in self:
            config.l10n_bg_erp_net_fp_ip = config.l10n_bg_fiscal_printer_id.printer_id

    @api.depends('l10n_bg_fiscal_printer_id', 'l10n_bg_fiscal_printer_id.host')
    def _compute_l10n_bg_erp_net_fp_host(self):
        for config in self:
            config.l10n_bg_erp_net_fp_host = config.l10n_bg_fiscal_printer_id.host

    @api.model
    def _load_pos_data_fields(self, config_id):
        """Зареждане на необходимите полета за фискален принтер"""
        res = super()._load_pos_data_fields(config_id)

        # Добавяме полета за сесията
        fiscal_fields = [
            'l10n_bg_erp_net_fp_host',
            'l10n_bg_erp_net_fp_ip',
            'l10n_bg_last_x_report',
            'l10n_bg_z_report_printed',
            'l10n_bg_z_report_datetime',
            'l10n_bg_fp_operator',
            'l10n_bg_fp_operator_password',
            # Phase 5 — external mode badge needs these in the POS UI
            'l10n_bg_external_pos_mode',
            'l10n_bg_external_push_status',
            'l10n_bg_external_push_summary',
        ]

        res.extend(fiscal_fields)
        return res

    # ========== Open-shift auto PLU push ==========

    def action_pos_session_open(self):
        """Push pending/stale PLUs to fiscal devices when the operator
        opens a session.

        Skipped when `l10n_bg_external_pos_mode` is on — the external
        flow in `pos_session_external.py` handles PLU + VAT + operators
        + logo + headers + X-report sanity in one orchestrated step,
        and we don't want to double-fire the PLU push.

        Best-effort per device: a network or device error on push is
        logged but does NOT block the session open. Operators can
        retry from the "Push PLUs..." wizard on the printer form. The
        only hard block is `conflict`/`error` push_state — those need
        manual fix and should surface before the operator opens.
        """
        res = super().action_pos_session_open()
        for sess in self:
            cfg = sess.config_id
            if cfg.l10n_bg_external_pos_mode:
                continue
            sess._l10n_bg_open_push_plus()
        return res

    def _l10n_bg_open_push_plus(self):
        """Lightweight open-shift PLU push for standard POS mode."""
        self.ensure_one()
        devices = self.config_id.l10n_bg_all_fiscal_devices
        if not devices:
            return
        Plu = self.env["l10n.bg.fiscal.plu"]
        plus = Plu.search([
            ("company_id", "=", self.company_id.id),
            ("active", "=", True),
            ("push_state", "in", ("pending", "stale", "name_drift", "pushed")),
        ])
        if not plus:
            return
        # Refresh push_state via consistency check before deciding
        # whether to block or push. Without this a price change since
        # the last validation could let a stale-but-unflagged PLU
        # through.
        for plu in plus:
            plu._check_consistency()
        conflicts = plus.filtered(
            lambda p: p.push_state in ("conflict", "error")
        )
        if conflicts:
            names = ", ".join(p.display_name for p in conflicts[:5])
            more = ""
            if len(conflicts) > 5:
                more = _(" (+%d more)") % (len(conflicts) - 5)
            raise UserError(_(
                "Cannot open POS session — %(n)d PLU(s) are in "
                "conflict/error state: %(names)s%(more)s. Fix them "
                "from Settings → Bulgarian Fiscal → PLU Slots before "
                "opening the session."
            ) % {"n": len(conflicts), "names": names, "more": more})
        pushable = plus.filtered(
            lambda p: p.push_state in ("pending", "stale", "name_drift")
        )
        if not pushable:
            return
        for device in devices:
            try:
                device._l10n_bg_push_plu_registry(pushable)
            except Exception:  # noqa: BLE001
                _logger.exception(
                    "Open-shift PLU push to '%s' failed for session %s; "
                    "session continues — operator can retry from the "
                    "device form.",
                    device.name, self.name,
                )

    # ========== Close-shift Z-report + reconcile ==========

    def action_pos_session_closing_control(self, *args, **kwargs):
        """Auto-print Z + create reconcile records on close.

        Skipped when:
          * Z is already printed (manual `action_print_z_report` ran)
          * config is in `l10n_bg_external_pos_mode` — that path orchestrates
            its own broader close in pos_session_external.py

        Per-device errors never block the standard close flow — operators
        must always be able to finish closing the session even when a fiscal
        device is unreachable. The error is captured in a Z-report record
        with status='error' for the audit trail.

        ORDER MATTERS: fire Z BEFORE super(). The super() call transitions
        `state` → `closing_control`, which navigates the POS UI away from
        `/pos/ui` to the closing-control modal. In `proxy` connection mode
        that tears down the browser-side bus listener for fiscal.printer
        requests — the queued Z fetch never reaches the proxy and times out
        at 90s, leaving the cashier stuck in the closing modal even though
        the session is already DB-closed. By firing Z first we use the live
        bus connection that the running POS UI still has.
        """
        for sess in self:
            if sess.l10n_bg_z_report_printed:
                continue
            if sess.config_id.l10n_bg_external_pos_mode:
                continue
            if not sess.config_id.l10n_bg_auto_z_on_close:
                continue
            sess._l10n_bg_close_zreport_per_device()
        return super().action_pos_session_closing_control(*args, **kwargs)

    def _l10n_bg_close_zreport_per_device(self):
        """For each fiscal device on this POS, run Z and persist a
        l10n.bg.fiscal.z.report record with both device-reported and
        Odoo-aggregate totals."""
        self.ensure_one()
        devices = self.config_id.l10n_bg_all_fiscal_devices
        if not devices:
            return
        odoo_totals = self._l10n_bg_compute_odoo_totals_by_group()
        ZReport = self.env["l10n.bg.fiscal.z.report"]
        any_success = False
        for device in devices:
            try:
                resp = device._l10n_bg_call_zreport_totals() or {}
            except Exception as exc:  # noqa: BLE001
                _logger.exception(
                    "Z-report call to '%s' failed; saving error record",
                    device.name,
                )
                ZReport.create({
                    "session_id": self.id,
                    "device_id": device.id,
                    "reconcile_status": "error",
                    "raw_messages": str(exc),
                    "odoo_totals_json": json.dumps(odoo_totals),
                })
                continue
            device_totals = resp.get("totals_by_group") or {}
            device_returned = bool(resp.get("device_returned_totals"))
            ok = bool(resp.get("ok"))
            status, diff = self._l10n_bg_reconcile_z(
                odoo_totals, device_totals, device_returned, ok)
            ZReport.create({
                "session_id": self.id,
                "device_id": device.id,
                "report_number": int(resp.get("report_number") or 0),
                "device_returned_totals": device_returned,
                "device_totals_json": json.dumps(device_totals),
                "odoo_totals_json": json.dumps(odoo_totals),
                "reconcile_status": status,
                "reconcile_diff_json": json.dumps(diff),
                "raw_messages": "\n".join(resp.get("messages") or []),
            })
            if ok:
                any_success = True
        if any_success:
            self.write({
                "l10n_bg_z_report_printed": True,
                "l10n_bg_z_report_datetime": fields.Datetime.now(),
            })

    def _l10n_bg_compute_odoo_totals_by_group(self):
        """Aggregate session pos.order.line amounts per BG VAT group letter.

        Mapping path:  pos.order.line.tax_ids[0] → l10n_bg_letter (custom field
        added by l10n_bg core). Lines without a mapped letter fall into the
        'А' (default) bucket so totals are never silently lost.
        """
        self.ensure_one()
        out: dict[str, float] = {}
        for order in self.order_ids:
            for line in order.lines:
                tax = line.tax_ids[:1]
                letter = (
                    getattr(tax, "l10n_bg_letter", None)
                    or "А"
                )
                out.setdefault(letter, 0.0)
                out[letter] += line.price_subtotal_incl
        return {k: round(v, 2) for k, v in out.items()}

    @staticmethod
    def _l10n_bg_reconcile_z(odoo, device, device_returned, ok):
        """Compute reconcile status + per-group diff. Tolerance ±0.01 BGN.

        Returns: (status, diff_dict)
        """
        if not ok:
            return "error", {}
        if not device_returned:
            return "no_device_totals", {}
        diff: dict[str, float] = {}
        all_keys = set(odoo) | set(device)
        for k in all_keys:
            d = float(device.get(k, 0))
            o = float(odoo.get(k, 0))
            delta = round(d - o, 2)
            if abs(delta) > 0.01:
                diff[k] = delta
        return ("matched" if not diff else "mismatch"), diff

    # ========== X ОТЧЕТ ==========

    def action_print_x_report(self):
        """Отпечатване на X отчет от сесията"""
        self.ensure_one()

        if not self.l10n_bg_fiscal_printer_id:
            raise UserError(_('There is no fiscal printer configured for this POS session'))

        if self.state != 'opened':
            raise UserError(_('An X report can only be printed with an open session'))

        # Проверка дали принтерът е достъпен
        printer_check = self.l10n_bg_fiscal_printer_id.check_printer_available()

        if not printer_check['available']:
            error_msg = printer_check.get('error', _('Принтерът не е достъпен'))
            mode = printer_check.get('mode', 'unknown')

            help_text = ''
            if mode == 'proxy':
                help_text = _(
                    '\n\nМоля, уверете се че:\n'
                    '• Браузърът с ErpNet прокси е отворен\n'
                    '• Принтерът е свързан и включен\n'
                    '• Прокси приложението има достъп до принтера'
                )
            elif mode == 'direct':
                help_text = _(
                    '\n\nМоля, проверете:\n'
                    '• ErpNet.FP сървърът е стартиран\n'
                    '• Принтерът е достъпен от сървъра'
                )

            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Принтерът не е достъпен'),
                    'message': error_msg + help_text,
                    'type': 'danger',
                    'sticky': True,
                }
            }

        try:
            result = self.l10n_bg_fiscal_printer_id.print_x_report()
            self.l10n_bg_last_x_report = fields.Datetime.now()

            self.message_post(
                body=_('X отчет отпечатан успешно'),
                message_type='notification'
            )

            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Успех'),
                    'message': _('X отчетът е отпечатан успешно'),
                    'type': 'success',
                }
            }
        except Exception as e:
            error_msg = str(e)
            if 'Timeout waiting for browser' in error_msg:
                error_msg = _(
                    'Няма връзка с фискалния принтер.\n\n'
                    'Моля, отворете браузъра с ErpNet прокси приложението.'
                )

            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Грешка'),
                    'message': error_msg,
                    'type': 'danger',
                    'sticky': True,
                }
            }

    # ========== Z ОТЧЕТ ==========

    def action_print_z_report(self):
        """Отпечатване на Z отчет при затваряне на сесията"""
        self.ensure_one()

        if not self.l10n_bg_fiscal_printer_id:
            raise UserError(_('Няма конфигуриран фискален принтер за тази POS сесия'))

        if self.l10n_bg_z_report_printed:
            raise UserError(_('Z отчет вече е отпечатан за тази сесия'))

        # Проверка дали принтерът е достъпен
        printer_check = self.l10n_bg_fiscal_printer_id.check_printer_available()

        if not printer_check['available']:
            error_msg = printer_check.get('error', _('Принтерът не е достъпен'))
            mode = printer_check.get('mode', 'unknown')

            help_text = ''
            if mode == 'proxy':
                help_text = _(
                    '\n\nМоля, уверете се че:\n'
                    '• Браузърът с ErpNet прокси е отворен\n'
                    '• Принтерът е свързан и включен\n'
                    '• Прокси приложението има достъп до принтера'
                )
            elif mode == 'direct':
                help_text = _(
                    '\n\nМоля, проверете:\n'
                    '• ErpNet.FP сървърът е стартиран\n'
                    '• Принтерът е достъпен от сървъра'
                )

            raise UserError(error_msg + help_text)

        try:
            result = self.l10n_bg_fiscal_printer_id.print_z_report()

            self.write({
                'l10n_bg_z_report_printed': True,
                'l10n_bg_z_report_datetime': fields.Datetime.now()
            })

            self.message_post(
                body=_('Z отчет отпечатан успешно'),
                message_type='notification'
            )

            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Успех'),
                    'message': _('Z отчетът е отпечатан успешно. Сесията може да бъде затворена.'),
                    'type': 'success',
                }
            }
        except Exception as e:
            error_msg = str(e)
            if 'Timeout waiting for browser' in error_msg:
                error_msg = _(
                    'Няма връзка с фискалния принтер.\n\n'
                    'Моля, отворете браузъра с ErpNet прокси приложението.'
                )

            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Грешка'),
                    'message': error_msg,
                    'type': 'danger',
                    'sticky': True,
                }
            }

    # ========== СЛУЖЕБНИ ОПЕРАЦИИ ==========

    def action_fiscal_withdraw(self):
        """Отваря wizard за служебно изведени"""
        self.ensure_one()
        return {
            'name': _('Officially removed'),
            'type': 'ir.actions.act_window',
            'res_model': 'fiscal.cash.operation.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_session_id': self.id,
                'default_operation_type': 'withdraw'
            }
        }

    def action_fiscal_deposit(self):
        """Отваря wizard за служебно въведени"""
        self.ensure_one()
        return {
            'name': _('Officially introduced'),
            'type': 'ir.actions.act_window',
            'res_model': 'fiscal.cash.operation.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_session_id': self.id,
                'default_operation_type': 'deposit'
            }
        }

    def action_check_printer(self):
        """Проверка на връзката с фискалния принтер"""
        self.ensure_one()

        if not self.l10n_bg_fiscal_printer_id:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Attention'),
                    'message': _('There is no fiscal printer configured'),
                    'type': 'warning',
                }
            }

        return self.l10n_bg_fiscal_printer_id.action_check_connection()
