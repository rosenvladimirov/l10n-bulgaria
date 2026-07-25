import json
import logging
import os

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)

# Пътят до blacklist.enc е фиксиран спрямо модулния директорий.
# Ако файлът липсва → controller връща 'blocked' → JS показва overlay.
_BLACKLIST_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    'data', 'blacklist.enc',
)


class BlacklistController(http.Controller):

    @http.route('/l10n_bg/blacklist/check', type='json', auth='user')
    def check_blacklist(self):
        """Проверява дали текущата фирма е в блекълиста.

        Връща:
            {'status': 'blocked'}              — файл липсва или ключ липсва/грешен
            {'status': 'ok', 'blacklisted': False}
            {'status': 'ok', 'blacklisted': True, 'message': '...', 'company': '...'}
        """
        # 1. Файлът трябва да съществува — ако е изтрит, блокираме.
        if not os.path.isfile(_BLACKLIST_FILE):
            _logger.warning('l10n_bg_config: blacklist.enc is missing — blocking application')
            return {'status': 'blocked'}

        # 2. Вземаме ключа от системните параметри.
        ICP = request.env['ir.config_parameter'].sudo()
        key_str = ICP.get_param('l10n_bg.blacklist_key')
        if not key_str:
            _logger.warning('l10n_bg_config: blacklist key not found in ir.config_parameter')
            return {'status': 'blocked'}

        # 3. Декриптираме.
        try:
            from cryptography.fernet import Fernet, InvalidToken
            f = Fernet(key_str.encode())
            with open(_BLACKLIST_FILE, 'rb') as fh:
                payload = f.decrypt(fh.read())
            data = json.loads(payload.decode('utf-8'))
        except Exception as exc:
            _logger.error('l10n_bg_config: blacklist decryption failed: %s', exc)
            return {'status': 'blocked'}

        # 4. Сравняваме ДДС номера на текущата фирма.
        company = request.env.company
        vat = (company.vat or '').replace(' ', '').upper()
        blacklisted_vat = {v.replace(' ', '').upper() for v in data.get('vat', [])}

        if vat and vat in blacklisted_vat:
            msg = data.get(
                'message',
                f'Company "{company.name}" is not licensed to use BLC modules. '
                f'Please contact support@odoo-shell.dev for licensing information.',
            )
            return {
                'status': 'ok',
                'blacklisted': True,
                'company': company.name,
                'message': msg,
            }

        return {'status': 'ok', 'blacklisted': False}
