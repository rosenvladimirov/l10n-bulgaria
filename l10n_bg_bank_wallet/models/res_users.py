import logging

from odoo import models, fields

_logger = logging.getLogger(__name__)


class Users(models.Model):
    _inherit = 'res.users'

    crypto_wallet_ids = fields.One2many(
        'crypto.wallet',
        'user_id',
        string='Crypto Wallets',
        help='Криптирани портфейли на потребителя'
    )

    def _check_credentials(self, credential, user_agent_env):
        """Прихваща успешната авторизация и синхронизира портфела"""
        old_password_hash = self.env.user.password

        result = super()._check_credentials(credential, user_agent_env)

        new_password_hash = self.env.user.password
        user_id = self.env.uid

        if old_password_hash != new_password_hash:
            _logger.info("Password hash changed for user %s", user_id)
            self._handle_wallet_reencryption(user_id, old_password_hash, new_password_hash)
        else:
            self._verify_wallet_sync(user_id, new_password_hash)

        return result

    def _handle_wallet_reencryption(self, user_id, old_hash, new_hash):
        """Обработва прекриптирането при промяна на хеша"""
        try:
            user = self.env['res.users'].browse(user_id)
            system_wallet = user.crypto_wallet_ids.filtered(lambda w: w.name == 'System Keys')

            if system_wallet and old_hash:
                success = system_wallet.auto_reencrypt_on_password_change(old_hash, new_hash)
                if success:
                    _logger.info("Successfully reencrypted wallet for user %s", user_id)
                else:
                    _logger.error("Failed to reencrypt wallet for user %s", user_id)
            elif not system_wallet:
                self._create_initial_wallet(user_id, new_hash)

        except Exception:
            _logger.exception("Error handling wallet reencryption for user %s", user_id)

    def _verify_wallet_sync(self, user_id, current_hash):
        """Проверява синхронизацията на портфела при същия хеш"""
        try:
            user = self.env['res.users'].browse(user_id)
            system_wallet = user.crypto_wallet_ids.filtered(lambda w: w.name == 'System Keys')

            if system_wallet:
                try:
                    system_wallet.unlock_wallet_with_password(current_hash)
                    _logger.debug("Wallet sync verified for user %s", user_id)
                except Exception:
                    _logger.warning("Wallet out of sync for user %s, attempting recovery", user_id)
                    self._create_initial_wallet(user_id, current_hash)
            else:
                self._create_initial_wallet(user_id, current_hash)

        except Exception:
            _logger.exception("Error verifying wallet sync for user %s", user_id)

    def _create_initial_wallet(self, user_id, master_password):
        """Създава начален портфел за потребител, ако вече няма такъв"""
        try:
            wallet_model = self.env['crypto.wallet'].sudo()
            existing = wallet_model.search([
                ('user_id', '=', user_id),
                ('name', '=', 'System Keys'),
            ], limit=1)
            if existing:
                _logger.debug("Wallet already exists for user %s, skipping creation", user_id)
                return
            wallet_model.create({
                'name': 'System Keys',
                'user_id': user_id,
                'master_password': master_password,
            })
            _logger.info("Created initial wallet for user %s", user_id)
        except Exception:
            _logger.exception("Failed to create initial wallet for user %s", user_id)
