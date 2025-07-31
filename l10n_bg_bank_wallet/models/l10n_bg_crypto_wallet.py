import logging
import os
import json
import base64
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend

from odoo import models, fields, api
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class CryptoWallet(models.Model):
    _name = 'crypto.wallet'
    _description = 'Virtual encrypted wallet for keys'
    _rec_name = 'name'

    name = fields.Char('Stored key name', required=True)
    user_id = fields.Many2one('res.users', 'User', required=True, default=lambda self: self.env.user)
    encrypted_data = fields.Text('Encrypted data', readonly=True)
    salt = fields.Text('Salt to encrypt', readonly=True)
    is_locked = fields.Boolean('Locked', default=True)
    created_date = fields.Datetime('Created on', default=fields.Datetime.now, readonly=True)
    last_accessed = fields.Datetime('Last opened', readonly=True)

    # Виртуални полета за ключовете (не се съхраняват в БД)
    master_password = fields.Char('Master password', store=False)
    decrypted_keys = fields.Text('Decrypted Keys', store=False, readonly=True)

    @api.model_create_multi
    def create(self, vals_list):
        """Създава нови crypto wallet записи"""
        # Обработка на master_password за всеки запис
        processed_vals_list = []
        master_passwords = []

        for vals in vals_list:
            processed_vals = vals.copy()

            if 'master_password' not in processed_vals:
                # Ако няма master_password, използва паролата на потребителя
                user_id = processed_vals.get('user_id', self.env.user.id)
                user = self.env['res.users'].browse(user_id)
                master_password = user.password
            else:
                master_password = processed_vals.pop('master_password')

            master_passwords.append(master_password)
            processed_vals_list.append(processed_vals)

        # Създава записите
        wallets = super().create(processed_vals_list)

        # Инициализира всеки портфел
        for wallet, master_password in zip(wallets, master_passwords):
            wallet._initialize_wallet(master_password)

        return wallets

    def write(self, vals):
        """Обновява crypto wallet записи"""
        # Ако има master_password в vals, трябва да го обработим специално
        if 'master_password' in vals:
            master_password = vals.pop('master_password')

            # Първо правим стандартното обновяване
            result = super().write(vals)

            # След това обработваме master_password за всеки запис
            for wallet in self:
                if wallet.encrypted_data:
                    # Ако портфелът вече има данни, трябва да ги прекриптираме
                    try:
                        current_password = wallet.get_master_password_for_user()
                        wallet_data = wallet.unlock_wallet(current_password)
                        wallet._reencrypt_wallet_with_new_key(wallet_data, master_password)
                    except Exception as e:
                        _logger.error(f"Failed to reencrypt wallet during write: {str(e)}")
                        # Fallback - създаваме нов портфел
                        wallet._initialize_wallet(master_password)
                else:
                    # Ако няма данни, просто инициализираме
                    wallet._initialize_wallet(master_password)

            return result
        else:
            # Стандартно обновяване без master_password
            return super().write(vals)

    def get_master_password_for_user(self):
        """
        Retrieves the master password associated with the current user's account.
        This method accesses the password stored within the user data corresponding to the
        user's unique identifier. It should be used with caution to maintain security
        of sensitive information.

        :return: Password associated with the current user's account
        :rtype: str
        """
        return self.user_id.password

    def unlock_with_user_password(self):
        """
        Unlocks the wallet using the user's master password.

        This method retrieves the master password associated with the current user
        and attempts to unlock the wallet using that password.

        :return: The result of the wallet unlocking operation.
        :rtype: bool
        """
        master_password = self.get_master_password_for_user()
        return self.unlock_wallet(master_password)

    def add_key_with_user_password(self, key_name, key_type, key_data):
        """
        Adds a key with the user's master password.

        This method is responsible for invoking the `add_key` method by supplying
        the user's master password, along with the key name, type, and data provided
        as arguments. It helps in securely associating a key with a specific user.

        :param key_name: Name of the key to be added
        :type key_name: str
        :param key_type: Type of the key to be added
        :type key_type: str
        :param key_data: Data of the key to be added
        :type key_data: str
        :return: Result of the `add_key` method
        :rtype: Any
        """
        master_password = self.get_master_password_for_user()
        return self.add_key(key_name, key_type, key_data, master_password)

    def get_key_with_user_password(self, key_name):
        """Взема ключ използвайки паролата на потребителя"""
        master_password = self.get_master_password_for_user()
        return self.get_key(key_name, master_password)

    def remove_key_with_user_password(self, key_name):
        """Премахва ключ използвайки паролата на потребителя"""
        master_password = self.get_master_password_for_user()
        return self.remove_key(key_name, master_password)

    def list_keys_with_user_password(self):
        """Показва списък с ключове използвайки паролата на потребителя"""
        master_password = self.get_master_password_for_user()
        return self.list_keys(master_password)

    @api.model
    def get_user_wallet(self, user_id=None):
        """Връща портфела на потребителя, създава го ако не съществува"""
        if not user_id:
            user_id = self.env.user.id

        user = self.env['res.users'].browse(user_id)
        current_hash = user.password

        # Търси портфел
        wallet = self.search([('user_id', '=', user_id), ('name', '=', 'System Keys')], limit=1)

        if not wallet:
            # Създава нов
            wallet = self.create({
                'name': 'System Keys',
                'user_id': user_id,
                'master_password': current_hash
            })
            _logger.info(f"Created new crypto wallet for user {user_id}")
        else:
            # Проверява синхронизацията
            try:
                wallet.unlock_wallet(current_hash)
                _logger.debug(f"Wallet sync verified for user {user_id}")
            except:
                # Reinitialize ако не работи
                _logger.warning(f"Wallet desync for user {user_id}, reinitializing")
                wallet._initialize_wallet(current_hash)

        return wallet

    def quick_access(self, key_name, user_id=None):
        """Бърз достъп до ключ"""
        wallet = self.get_user_wallet(user_id)
        user = self.env['res.users'].browse(user_id or self.env.user.id)
        return wallet.get_key(key_name, user.password)

    def quick_store(self, key_name, key_type, key_data, user_id=None):
        """Бързо съхранение на ключ"""
        wallet = self.get_user_wallet(user_id)
        user = self.env['res.users'].browse(user_id or self.env.user.id)
        return wallet.add_key(key_name, key_type, key_data, user.password)

    def _initialize_wallet(self, master_password):
        """Инициализира празен криптиран портфел"""
        # Генерира salt
        salt = os.urandom(16)
        self.salt = base64.b64encode(salt).decode()

        # Създава ключ за криптиране от паролата
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
            backend=default_backend()
        )
        key = base64.urlsafe_b64encode(kdf.derive(master_password.encode()))

        # Инициализира празен портфел
        empty_wallet = {
            'version': '1.0',
            'keys': {},
            'metadata': {
                'created': fields.Datetime.now().isoformat(),
                'key_count': 0
            }
        }

        # Криптира данните
        f = Fernet(key)
        encrypted_data = f.encrypt(json.dumps(empty_wallet).encode())
        self.encrypted_data = base64.b64encode(encrypted_data).decode()

        _logger.info(f"Initialized crypto wallet '{self.name}' for user {self.user_id.name}")

    def unlock_wallet(self, master_password):
        """Отключва портфела с главната парола"""
        try:
            # Възстановява ключа за криптиране
            salt = base64.b64decode(self.salt)
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=100000,
                backend=default_backend()
            )
            key = base64.urlsafe_b64encode(kdf.derive(master_password.encode()))

            # Декриптира данните
            f = Fernet(key)
            encrypted_data = base64.b64decode(self.encrypted_data)
            decrypted_data = f.decrypt(encrypted_data)

            # Парсва JSON данните
            wallet_data = json.loads(decrypted_data.decode())

            # Записва в сесията (не в БД)
            self.is_locked = False
            self.last_accessed = fields.Datetime.now()
            self.decrypted_keys = json.dumps(wallet_data, indent=2)

            # Съхранява ключа в кеша на сесията
            self.env.context = dict(self.env.context, wallet_key=key.decode())

            _logger.debug(f"Wallet '{self.name}' unlocked successfully")
            return wallet_data

        except Exception as e:
            _logger.error(f"Failed to unlock wallet '{self.name}': {str(e)}")
            raise UserError('Грешна главна парола или повредени данни в портфела')

    def lock_wallet(self):
        """Заключва портфела"""
        self.is_locked = True
        self.decrypted_keys = False
        # Изчиства ключа от контекста
        if 'wallet_key' in self.env.context:
            self.env.context = {k: v for k, v in self.env.context.items() if k != 'wallet_key'}
        _logger.debug(f"Wallet '{self.name}' locked")

    def add_key(self, key_name, key_type, key_data, master_password=None):
        """Добавя нов ключ в портфела"""
        if not master_password:
            master_password = self.get_master_password_for_user()

        if self.is_locked:
            wallet_data = self.unlock_wallet(master_password)
        else:
            # Ако е отключен, използва кеширания ключ
            wallet_key = self.env.context.get('wallet_key')
            if not wallet_key:
                wallet_data = self.unlock_wallet(master_password)
            else:
                # Декриптира текущите данни
                f = Fernet(wallet_key.encode())
                encrypted_data = base64.b64decode(self.encrypted_data)
                decrypted_data = f.decrypt(encrypted_data)
                wallet_data = json.loads(decrypted_data.decode())

        # Добавя новия ключ
        wallet_data['keys'][key_name] = {
            'type': key_type,
            'data': key_data,
            'created': fields.Datetime.now().isoformat(),
            'metadata': {}
        }
        wallet_data['metadata']['key_count'] = len(wallet_data['keys'])
        wallet_data['metadata']['last_modified'] = fields.Datetime.now().isoformat()

        # Криптира и съхранява обратно
        self._save_wallet_data(wallet_data)

        _logger.debug(f"Added key '{key_name}' of type '{key_type}' to wallet '{self.name}'")
        return True

    def get_key(self, key_name, master_password=None):
        """Извлича ключ от портфела"""
        if not master_password:
            master_password = self.get_master_password_for_user()

        if self.is_locked:
            wallet_data = self.unlock_wallet(master_password)
        else:
            wallet_key = self.env.context.get('wallet_key')
            if not wallet_key:
                wallet_data = self.unlock_wallet(master_password)
            else:
                f = Fernet(wallet_key.encode())
                encrypted_data = base64.b64decode(self.encrypted_data)
                decrypted_data = f.decrypt(encrypted_data)
                wallet_data = json.loads(decrypted_data.decode())

        if key_name not in wallet_data['keys']:
            raise UserError(f'Ключ "{key_name}" не съществува в портфела')

        return wallet_data['keys'][key_name]

    def list_keys(self, master_password=None):
        """Показва списък с всички ключове в портфела"""
        if not master_password:
            master_password = self.get_master_password_for_user()

        if self.is_locked:
            wallet_data = self.unlock_wallet(master_password)
        else:
            wallet_key = self.env.context.get('wallet_key')
            if not wallet_key:
                wallet_data = self.unlock_wallet(master_password)
            else:
                f = Fernet(wallet_key.encode())
                encrypted_data = base64.b64decode(self.encrypted_data)
                decrypted_data = f.decrypt(encrypted_data)
                wallet_data = json.loads(decrypted_data.decode())

        keys_info = []
        for key_name, key_info in wallet_data['keys'].items():
            keys_info.append({
                'name': key_name,
                'type': key_info['type'],
                'created': key_info['created']
            })

        return keys_info

    def remove_key(self, key_name, master_password=None):
        """Премахва ключ от портфела"""
        if not master_password:
            master_password = self.get_master_password_for_user()

        if self.is_locked:
            wallet_data = self.unlock_wallet(master_password)
        else:
            wallet_key = self.env.context.get('wallet_key')
            if not wallet_key:
                wallet_data = self.unlock_wallet(master_password)
            else:
                f = Fernet(wallet_key.encode())
                encrypted_data = base64.b64decode(self.encrypted_data)
                decrypted_data = f.decrypt(encrypted_data)
                wallet_data = json.loads(decrypted_data.decode())

        if key_name not in wallet_data['keys']:
            raise UserError(f'Ключ "{key_name}" не съществува в портфела')

        # Премахва ключа
        del wallet_data['keys'][key_name]
        wallet_data['metadata']['key_count'] = len(wallet_data['keys'])
        wallet_data['metadata']['last_modified'] = fields.Datetime.now().isoformat()

        # Съхранява обратно
        self._save_wallet_data(wallet_data)

        _logger.debug(f"Removed key '{key_name}' from wallet '{self.name}'")
        return True

    def _save_wallet_data(self, wallet_data):
        """Криптира и съхранява данните на портфела"""
        wallet_key = self.env.context.get('wallet_key')
        if not wallet_key:
            # Ако няма кеширан ключ, използва паролата на потребителя
            master_password = self.get_master_password_for_user()
            self.unlock_wallet(master_password)
            wallet_key = self.env.context.get('wallet_key')

        # Криптира данните
        f = Fernet(wallet_key.encode())
        encrypted_data = f.encrypt(json.dumps(wallet_data).encode())
        self.encrypted_data = base64.b64encode(encrypted_data).decode()

        # Актуализира виртуалното поле
        self.decrypted_keys = json.dumps(wallet_data, indent=2)

    def change_master_password(self, old_password, new_password):
        """Променя главната парола на портфела"""
        # Първо отключва с старата парола
        wallet_data = self.unlock_wallet(old_password)

        # Прекриптира с новата парола
        self._reencrypt_wallet_with_new_key(wallet_data, new_password)

        _logger.info(f"Master password changed for wallet '{self.name}'")
        return True

    def export_wallet(self, master_password=None, export_password=None):
        """Експортира портфела за backup"""
        if not master_password:
            master_password = self.get_master_password_for_user()

        wallet_data = self.unlock_wallet(master_password)

        export_data = {
            'wallet_name': self.name,
            'export_date': fields.Datetime.now().isoformat(),
            'data': wallet_data
        }

        if export_password:
            # Криптира експорта с различна парола
            salt = os.urandom(16)
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=100000,
                backend=default_backend()
            )
            key = base64.urlsafe_b64encode(kdf.derive(export_password.encode()))
            f = Fernet(key)

            encrypted_export = f.encrypt(json.dumps(export_data).encode())

            return {
                'encrypted': True,
                'salt': base64.b64encode(salt).decode(),
                'data': base64.b64encode(encrypted_export).decode()
            }
        else:
            return {
                'encrypted': False,
                'data': export_data
            }

    def auto_reencrypt_on_password_change(self, old_password_hash, new_password_hash):
        """Автоматично прекриптира портфела при промяна на парола"""
        try:
            # Декриптира с стария хеш
            wallet_data = self.unlock_wallet(old_password_hash)

            # Прекриптира със новия хеш
            self._reencrypt_wallet_with_new_key(wallet_data, new_password_hash)

            _logger.info(f"Auto-reencrypted wallet '{self.name}' with new password hash")
            return True

        except Exception as e:
            _logger.error(f"Failed to auto-reencrypt wallet '{self.name}': {str(e)}")
            # В случай на грешка, създава нов портфел
            return self._create_emergency_wallet(new_password_hash)

    def _reencrypt_wallet_with_new_key(self, wallet_data, new_master_password):
        """Прекриптира портфела с нов master ключ"""
        # Генерира нов salt
        salt = os.urandom(16)
        self.salt = base64.b64encode(salt).decode()

        # Създава нов ключ за криптиране
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
            backend=default_backend()
        )
        new_key = base64.urlsafe_b64encode(kdf.derive(new_master_password.encode()))

        # Обновява metadata
        wallet_data['metadata']['reencrypted'] = fields.Datetime.now().isoformat()
        wallet_data['metadata']['reencryption_reason'] = 'password_hash_change'

        # Криптира с новия ключ
        f = Fernet(new_key)
        encrypted_data = f.encrypt(json.dumps(wallet_data).encode())
        self.encrypted_data = base64.b64encode(encrypted_data).decode()

        # Актуализира контекста
        self.env.context = dict(self.env.context, wallet_key=new_key.decode())
        self.is_locked = False

        _logger.debug(f"Wallet '{self.name}' reencrypted successfully")

    def _create_emergency_wallet(self, new_password_hash):
        """Създава нов портфел в случай на неуспешно прекриптиране"""
        try:
            # Инициализира нов портфел
            self._initialize_wallet(new_password_hash)
            _logger.warning(f"Created emergency wallet for '{self.name}' - old data may be lost")
            return True
        except Exception as e:
            _logger.error(f"Failed to create emergency wallet: {str(e)}")
            return False
