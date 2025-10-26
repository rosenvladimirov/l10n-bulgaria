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
        Обновява статуса на принтера (извиква се ръчно или от cron)
        ЗАБЕЛЕЖКА: Това е опционално - не е нужно за печат на бонове
        """
        self.ensure_one()
        try:
            status_data = self.get_printer_status()

            self.env['fiscal.printer.status'].create({
                'printer_id': self.id,
                'status': status_data.get('status'),
                'error_message': status_data.get('errorMessage'),
                'is_ready': status_data.get('ok', False),
                'paper_available': status_data.get('paperAvailable', False),
                'fiscal_memory_available': status_data.get('fiscalMemoryAvailable', False),
                'document_number': status_data.get('documentNumber'),
                'serial_number': status_data.get('serialNumber'),
                'firmware_version': status_data.get('firmwareVersion')
            })

            # Notification за frontend (опционално)
            self.env['bus.bus']._sendone(
                'fiscal.printer.status',
                'printer_status_update',
                {
                    'type': 'printer_status_update',
                    'printer_id': self.id,
                    'name': self.name,
                    'status': status_data.get('status'),
                    'is_ready': status_data.get('ok', False),
                    'error_message': status_data.get('errorMessage'),
                    'last_update': fields.Datetime.now().isoformat()
                }
            )

        except Exception as e:
            _logger.error(f"Грешка при обновяване на статус на {self.name}: {str(e)}")
            self.env['fiscal.printer.status'].create({
                'printer_id': self.id,
                'status': 'error',
                'error_message': str(e),
                'is_ready': False
            })

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
