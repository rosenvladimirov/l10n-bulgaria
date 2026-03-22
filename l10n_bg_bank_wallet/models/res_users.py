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

    @classmethod
    def _check_credentials(cls, env, credential, user_agent_env=None):
        """Прихваща успешната авторизация и синхронизира портфела"""
        # Запазва стария хеш ПРЕДИ авторизацията
        user_login = credential.get('login') or credential.get('uid')
        old_user = None
        old_password_hash = None

        if user_login:
            if isinstance(user_login, int):
                old_user = env['res.users'].browse(user_login)
            else:
                old_user = env['res.users'].search([('login', '=', user_login)], limit=1)

            if old_user:
                old_password_hash = old_user.password

        result = super(Users, cls)._check_credentials(env, credential, user_agent_env)

        if result and old_user:
            new_user = env['res.users'].browse(result)
            new_password_hash = new_user.password

            if old_password_hash != new_password_hash:
                _logger.info("Password hash changed for user %s", result)
                cls._handle_wallet_reencryption(env, result, old_password_hash, new_password_hash)
            else:
                cls._verify_wallet_sync(env, result, new_password_hash)

        return result

    @classmethod
    def _handle_wallet_reencryption(cls, env, user_id, old_hash, new_hash):
        """Обработва прекриптирането при промяна на хеша"""
        try:
            user = env['res.users'].browse(user_id)
            system_wallet = user.crypto_wallet_ids.filtered(lambda w: w.name == 'System Keys')

            if system_wallet and old_hash:
                success = system_wallet.auto_reencrypt_on_password_change(old_hash, new_hash)
                if success:
                    _logger.info("Successfully reencrypted wallet for user %s", user_id)
                else:
                    _logger.error("Failed to reencrypt wallet for user %s", user_id)
            elif not system_wallet:
                cls._create_initial_wallet(env, user_id, new_hash)

        except Exception:
            _logger.exception("Error handling wallet reencryption for user %s", user_id)

    @classmethod
    def _verify_wallet_sync(cls, env, user_id, current_hash):
        """Проверява синхронизацията на портфела при същия хеш"""
        try:
            user = env['res.users'].browse(user_id)
            system_wallet = user.crypto_wallet_ids.filtered(lambda w: w.name == 'System Keys')

            if system_wallet:
                try:
                    system_wallet.unlock_wallet_with_password(current_hash)
                    _logger.debug("Wallet sync verified for user %s", user_id)
                except Exception:
                    _logger.warning("Wallet out of sync for user %s, attempting recovery", user_id)
                    cls._create_initial_wallet(env, user_id, current_hash)
            else:
                cls._create_initial_wallet(env, user_id, current_hash)

        except Exception:
            _logger.exception("Error verifying wallet sync for user %s", user_id)

    @classmethod
    def _create_initial_wallet(cls, env, user_id, master_password):
        """Създава начален портфел за потребител"""
        try:
            wallet_model = env['crypto.wallet'].sudo()
            wallet_model.create({
                'name': 'System Keys',
                'user_id': user_id,
                'master_password': master_password,
            })
            _logger.info("Created initial wallet for user %s", user_id)
        except Exception:
            _logger.exception("Failed to create initial wallet for user %s", user_id)
