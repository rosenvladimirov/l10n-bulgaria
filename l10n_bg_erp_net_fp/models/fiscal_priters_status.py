import logging
from datetime import timedelta

from odoo import models, fields, api, _

_logger = logging.getLogger(__name__)


class FiscalPrinterDevice(models.Model):
    _inherit = 'fiscal.printer.device'

    status_ids = fields.One2many('fiscal.printer.status', 'printer_id', string='Статусна история')
    status_count = fields.Integer('Брой статуси', compute='_compute_status_count')
    current_status = fields.Char('Текущ статус', compute='_compute_current_status', store=False)
    is_ready = fields.Boolean('Готов', compute='_compute_current_status', store=False)

    # Настройки за история
    status_history_days = fields.Integer(
        string='Дни за съхранение на история',
        default=30,
        help='Брой дни за запазване на статусна история. По-старите записи се изтриват автоматично.'
    )

    @api.depends('status_ids')
    def _compute_status_count(self):
        """Брои всички статуси"""
        for printer in self:
            printer.status_count = len(printer.status_ids)

    def _compute_current_status(self):
        """Изчислява текущия статус от последния запис"""
        for printer in self:
            last_status = printer.status_ids.sorted('create_date', reverse=True)[:1]
            printer.current_status = last_status.status if last_status else 'Няма информация'
            printer.is_ready = last_status.is_ready if last_status else False

    def update_status(self):
        """
        Заявка за обновяване на статуса на принтера
        Изпраща bus notification към браузъра, който прави реалната заявка
        """
        self.ensure_one()

        # Изпращаме bus notification към всички активни клиенти
        self.env['bus.bus']._sendone(
            self.env.user.partner_id,
            'fiscal.printer.status',
            {
                'type': 'check_printer_status',
                'printer_id': self.id,
                'name': self.name,
            }
        )

        _logger.info(f"Изпратена заявка за проверка на статус на {self.name}")

    def action_request_status(self):
        """Публичен метод за заявка на статус (извиква се от UI)"""
        self.update_status()
        return True

    @api.model
    def _cron_cleanup_status_history(self):
        """
        Крон задача за автоматично изчистване на стара история
        Изпълнява се седмично
        """
        _logger.info("Започване на изчистване на статусна история на фискални принтери")

        printers = self.search([('active', '=', True)])
        total_deleted = 0

        for printer in printers:
            try:
                # Изчисляваме датата преди която да изтрием
                cutoff_date = fields.Datetime.now() - timedelta(days=printer.status_history_days)

                # Намираме старите записи
                old_statuses = self.env['fiscal.printer.status'].search([
                    ('printer_id', '=', printer.id),
                    ('create_date', '<', cutoff_date)
                ])

                count = len(old_statuses)
                if count > 0:
                    old_statuses.unlink()
                    total_deleted += count
                    _logger.info(
                        f"Изтрити {count} стари статуса за принтер '{printer.name}' "
                        f"(по-стари от {printer.status_history_days} дни)"
                    )

            except Exception as e:
                _logger.error(f"Грешка при изчистване на история за {printer.name}: {str(e)}")
                continue

        _logger.info(f"Приключено изчистване на статусна история. Общо изтрити: {total_deleted} записа")
        return total_deleted

    def action_cleanup_old_status(self):
        """Ръчно изчистване на старата история от интерфейса"""
        self.ensure_one()
        cutoff_date = fields.Datetime.now() - timedelta(days=self.status_history_days)

        old_statuses = self.env['fiscal.printer.status'].search([
            ('printer_id', '=', self.id),
            ('create_date', '<', cutoff_date)
        ])

        count = len(old_statuses)
        if count > 0:
            old_statuses.unlink()
            message = f'Изтрити {count} стари статуса (по-стари от {self.status_history_days} дни)'
        else:
            message = 'Няма стари статуси за изтриване'

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Изчистване на история'),
                'message': message,
                'type': 'success' if count > 0 else 'info',
            }
        }

    def action_view_status_history(self):
        """Отваря списък със статусите на този принтер"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('История на статуси'),
            'res_model': 'fiscal.printer.status',
            'view_mode': 'list,form',
            'domain': [('printer_id', '=', self.id)],
            'context': {'default_printer_id': self.id},
        }
