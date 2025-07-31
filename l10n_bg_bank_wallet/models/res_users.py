class Users(models.Model):
    _inherit = 'res.users'

    @classmethod
    def _check_credentials(cls, env, credential):
        """Прихваща успешната авторизация и синхронизира портфела"""
        # Запазва стария хеш ПРЕДИ авторизацията
        user_login = credential.get('login') or credential.get('uid')
        old_user = None
        old_password_hash = None

        if user_login:
            # Намираме потребителя и запазваме стария хеш
            if isinstance(user_login, int):
                old_user = env['res.users'].browse(user_login)
            else:
                old_user = env['res.users'].search([('login', '=', user_login)], limit=1)

            if old_user:
                old_password_hash = old_user.password

        # Извиква оригиналния метод
        result = super(Users, cls)._check_credentials(env, credential)

        # Ако авторизацията е успешна и има промяна в хеша
        if result and old_user:
            new_user = env['res.users'].browse(result)
            new_password_hash = new_user.password

            # Проверява дали хешът се е променил
            if old_password_hash != new_password_hash:
                _logger.info(f"Password hash changed for user {result}")
                cls._handle_wallet_reencryption(env, result, old_password_hash, new_password_hash)
            else:
                # Хешът е същия - само проверява синхронизацията
                cls._verify_wallet_sync(env, result, new_password_hash)

        return result

    @classmethod
    def _handle_wallet_reencryption(cls, env, user_id, old_hash, new_hash):
        """Обработва прекриптирането при промяна на хеша"""
        try:
            user = env['res.users'].browse(user_id)
            system_wallet = user.crypto_wallet_ids.filtered(lambda w: w.name == 'System Keys')

            if system_wallet and old_hash:
                # Прекриптира портфела
                success = system_wallet.auto_reencrypt_on_password_change(old_hash, new_hash)
                if success:
                    _logger.info(f"Successfully reencrypted wallet for user {user_id}")
                else:
                    _logger.error(f"Failed to reencrypt wallet for user {user_id}")
            elif not system_wallet:
                # Създава нов портфел
                cls._create_initial_wallet(env, user_id, new_hash)

        except Exception as e:
            _logger.error(f"Error handling wallet reencryption for user {user_id}: {str(e)}")

    @classmethod
    def _verify_wallet_sync(cls, env, user_id, current_hash):
        """Проверява синхронизацията на портфела при същия хеш"""
        try:
            user = env['res.users'].browse(user_id)
            system_wallet = user.crypto_wallet_ids.filtered(lambda w: w.name == 'System Keys')

            if system_wallet:
                try:
                    # Опитва се да отключи портфела
                    system_wallet.unlock_wallet(current_hash)
                    _logger.debug(f"Wallet sync verified for user {user_id}")
                except:
                    # Портфелът не може да се отключи - нещо не е наред
                    _logger.warning(f"Wallet out of sync for user {user_id}, attempting recovery")
                    cls._create_initial_wallet(env, user_id, current_hash)
            else:
                # Няма портфел - създава нов
                cls._create_initial_wallet(env, user_id, current_hash)

        except Exception as e:
            _logger.error(f"Error verifying wallet sync for user {user_id}: {str(e)}")
