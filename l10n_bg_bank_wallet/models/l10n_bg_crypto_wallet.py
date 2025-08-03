import logging
import os
import json
import base64
import uuid
from pathlib import Path
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend

from odoo import models, fields, api, tools
from odoo.exceptions import UserError, AccessError

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
    file_path = fields.Char('File path on disk', readonly=True)

    # Виртуални полета за ключовете (не се съхраняват в БД)
    master_password = fields.Char('Master password', store=False)
    decrypted_keys = fields.Text('Decrypted Keys', store=False, readonly=True)

    # Нива на права за достъп
    PERMISSION_LEVELS = {
        'read': 'l10n_bg_crypto_wallet.group_crypto_wallet_read',
        'write': 'l10n_bg_crypto_wallet.group_crypto_wallet_write',
        'admin': 'l10n_bg_crypto_wallet.group_crypto_wallet_admin',
        'generate': 'l10n_bg_crypto_wallet.group_crypto_wallet_generate',
        'export': 'l10n_bg_crypto_wallet.group_crypto_wallet_export'
    }

    def _check_permission(self, permission_level):
        """Проверява дали потребителят има необходимото разрешение"""
        if not self.env.user.has_group(self.PERMISSION_LEVELS.get(permission_level)):
            raise AccessError(f'Нямате разрешение за операция: {permission_level}')

    def _get_wallet_directory(self):
        """Създава и връща директорията за съхранение на портфейли"""
        # Използва filestore директорията на текущата база данни
        db_name = self.env.cr.dbname
        filestore_path = tools.config.filestore(db_name)
        wallet_dir = Path(filestore_path) / 'crypto_wallets'

        # Създава директорията ако не съществува
        wallet_dir.mkdir(mode=0o700, parents=True, exist_ok=True)

        return wallet_dir

    def _get_wallet_file_path(self, key_name=None):
        """Връща пътя до файла на портфейла с подробно име"""
        wallet_dir = self._get_wallet_directory()

        # Получава uid на базата данни
        db_uid = self.env['ir.config_parameter'].sudo().get_param('database.uuid')
        if not db_uid:
            # Ако няма UUID на базата, генерира един
            db_uid = str(uuid.uuid4())
            self.env['ir.config_parameter'].sudo().set_param('database.uuid', db_uid)

        # Скъсява UUID-тата за по-кратки имена
        db_short = db_uid[:8]
        user_short = str(self.user_id.id).zfill(4)  # padding с нули
        wallet_short = str(self.id).zfill(4)

        if key_name:
            # За отделни ключове
            # Форматира името на ключа (премахва специални символи)
            safe_key_name = "".join(c for c in key_name if c.isalnum() or c in '-_').lower()
            filename = f"key_{db_short}_{user_short}_{wallet_short}_{safe_key_name}.enc"
        else:
            # За целия портфел
            filename = f"wallet_{db_short}_{user_short}_{wallet_short}_{self.name.lower().replace(' ', '_')}.enc"

        return wallet_dir / filename

    def _get_individual_key_path(self, key_name):
        """Връща пътя за отделен ключ"""
        return self._get_wallet_file_path(key_name)

    def _save_individual_key_to_disk(self, key_name, key_data):
        """Записва отделен ключ на диск"""
        file_path = self._get_individual_key_path(key_name)

        try:
            # Подготвя данните за записване
            key_envelope = {
                'key_name': key_name,
                'wallet_id': self.id,
                'user_id': self.user_id.id,
                'created': fields.Datetime.now().isoformat(),
                'data': key_data
            }

            # Криптира данните
            master_password = self.get_master_password_for_user()
            salt = os.urandom(16)
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=100000,
                backend=default_backend()
            )
            key = base64.urlsafe_b64encode(kdf.derive(master_password.encode()))
            f = Fernet(key)

            encrypted_envelope = {
                'salt': base64.b64encode(salt).decode(),
                'data': base64.b64encode(f.encrypt(json.dumps(key_envelope).encode())).decode()
            }

            # Записва с ограничени права
            with open(file_path, 'w') as file:
                json.dump(encrypted_envelope, file)

            # Задава права 600 (само собственик чете/пише)
            os.chmod(file_path, 0o600)

            _logger.info(f"Individual key saved to disk: {file_path}")
            return str(file_path)

        except Exception as e:
            _logger.error(f"Failed to save individual key to disk: {str(e)}")
            raise UserError(f'Грешка при записването на ключ на диск: {str(e)}')

    def _load_individual_key_from_disk(self, key_name):
        """Зарежда отделен ключ от диск"""
        file_path = self._get_individual_key_path(key_name)

        if not file_path.exists():
            return None

        try:
            with open(file_path, 'r') as file:
                encrypted_envelope = json.load(file)

            # Декриптира данните
            master_password = self.get_master_password_for_user()
            salt = base64.b64decode(encrypted_envelope['salt'])
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=100000,
                backend=default_backend()
            )
            key = base64.urlsafe_b64encode(kdf.derive(master_password.encode()))
            f = Fernet(key)

            decrypted_data = f.decrypt(base64.b64decode(encrypted_envelope['data']))
            key_envelope = json.loads(decrypted_data.decode())

            return key_envelope['data']

        except Exception as e:
            _logger.error(f"Failed to load individual key from disk: {str(e)}")
            return None

    def list_wallet_files_on_disk(self):
        """Показва всички файлове на портфейла на диск"""
        self._check_permission('admin')

        wallet_dir = self._get_wallet_directory()
        db_uid = self.env['ir.config_parameter'].sudo().get_param('database.uuid', 'unknown')
        db_short = db_uid[:8]
        user_short = str(self.user_id.id).zfill(4)
        wallet_short = str(self.id).zfill(4)

        # Търси всички файлове свързани с този портфел
        pattern = f"{db_short}_{user_short}_{wallet_short}_*"
        files = list(wallet_dir.glob(f"*{pattern}*"))

        file_info = []
        for file_path in files:
            stat = file_path.stat()
            file_info.append({
                'name': file_path.name,
                'path': str(file_path),
                'size': stat.st_size,
                'created': fields.Datetime.from_timestamp(stat.st_ctime),
                'modified': fields.Datetime.from_timestamp(stat.st_mtime),
                'permissions': oct(stat.st_mode)[-3:]
            })

        return file_info

    def cleanup_orphaned_files(self):
        """Почиства файлове без съответни записи в базата"""
        self._check_permission('admin')

        wallet_dir = self._get_wallet_directory()
        all_files = list(wallet_dir.glob("*.enc"))

        # Получава всички активни портфейли
        active_wallets = self.search([])
        active_patterns = set()

        for wallet in active_wallets:
            db_uid = self.env['ir.config_parameter'].sudo().get_param('database.uuid', 'unknown')
            db_short = db_uid[:8]
            user_short = str(wallet.user_id.id).zfill(4)
            wallet_short = str(wallet.id).zfill(4)
            active_patterns.add(f"{db_short}_{user_short}_{wallet_short}")

        orphaned_files = []
        for file_path in all_files:
            file_pattern = "_".join(file_path.stem.split("_")[1:4])  # взема db_user_wallet частта
            if file_pattern not in active_patterns:
                orphaned_files.append(file_path)

        # Премахва orphaned файлове
        removed_count = 0
        for file_path in orphaned_files:
            try:
                file_path.unlink()
                removed_count += 1
                _logger.info(f"Removed orphaned wallet file: {file_path}")
            except Exception as e:
                _logger.error(f"Failed to remove orphaned file {file_path}: {str(e)}")

        return {
            'removed_count': removed_count,
            'orphaned_files': [str(f) for f in orphaned_files]
        }

    def _save_to_disk(self, data):
        """Записва криптираните данни на диск"""
        file_path = self._get_wallet_file_path()

        try:
            # Записва с ограничени права (само за собственика)
            with open(file_path, 'wb') as f:
                f.write(base64.b64decode(data))

            # Задава права 600 (само собственик чете/пише)
            os.chmod(file_path, 0o600)

            # Записва пътя в БД
            self.file_path = str(file_path)

            _logger.info(f"Wallet data saved to disk: {file_path}")

        except Exception as e:
            _logger.error(f"Failed to save wallet to disk: {str(e)}")
            raise UserError(f'Грешка при записването на диск: {str(e)}')

    def _load_from_disk(self):
        """Зарежда криптираните данни от диск"""
        if not self.file_path or not os.path.exists(self.file_path):
            return None

        try:
            with open(self.file_path, 'rb') as f:
                data = f.read()
            return base64.b64encode(data).decode()

        except Exception as e:
            _logger.error(f"Failed to load wallet from disk: {str(e)}")
            return None

    @api.model_create_multi
    def create(self, vals_list):
        """Създава нови crypto wallet записи"""
        self._check_permission('write')

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
        self._check_permission('write')

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

    def unlink(self):
        """Премахва портфейла и файла от диск"""
        self._check_permission('admin')

        for wallet in self:
            if wallet.file_path and os.path.exists(wallet.file_path):
                try:
                    os.remove(wallet.file_path)
                    _logger.info(f"Deleted wallet file: {wallet.file_path}")
                except Exception as e:
                    _logger.error(f"Failed to delete wallet file: {str(e)}")

        return super().unlink()

    def get_master_password_for_user(self):
        """
        Retrieves the master password associated with the current user's account.
        This method accesses the password stored within the user data corresponding to the
        user's unique identifier. It should be used with caution to maintain security
        of sensitive information.

        :return: Password associated with the current user's account
        :rtype: str
        """
        self._check_permission('read')
        return self.user_id.password

    def unlock_with_user_password(self):
        """
        Unlocks the wallet using the user's master password.

        This method retrieves the master password associated with the current user
        and attempts to unlock the wallet using that password.

        :return: The result of the wallet unlocking operation.
        :rtype: bool
        """
        self._check_permission('read')
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
        self._check_permission('write')
        master_password = self.get_master_password_for_user()
        return self.add_key(key_name, key_type, key_data, master_password)

    def get_key_with_user_password(self, key_name):
        """Взема ключ използвайки паролата на потребителя"""
        self._check_permission('read')
        master_password = self.get_master_password_for_user()
        return self.get_key(key_name, master_password)

    def remove_key_with_user_password(self, key_name):
        """Премахва ключ използвайки паролата на потребителя"""
        self._check_permission('write')
        master_password = self.get_master_password_for_user()
        return self.remove_key(key_name, master_password)

    def list_keys_with_user_password(self):
        """Показва списък с ключове използвайки паролата на потребителя"""
        self._check_permission('read')
        master_password = self.get_master_password_for_user()
        return self.list_keys(master_password)

    def generate_keypair(self, key_name, key_type='rsa'):
        """Генерира двойка ключове (публичен/частен)"""
        self._check_permission('generate')

        from cryptography.hazmat.primitives.asymmetric import rsa, ec
        from cryptography.hazmat.primitives import serialization

        try:
            if key_type.lower() == 'rsa':
                # Генерира RSA ключова двойка
                private_key = rsa.generate_private_key(
                    public_exponent=65537,
                    key_size=2048,
                    backend=default_backend()
                )
                public_key = private_key.public_key()

                # Сериализира ключовете
                private_pem = private_key.private_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PrivateFormat.PKCS8,
                    encryption_algorithm=serialization.NoEncryption()
                )

                public_pem = public_key.public_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PublicFormat.SubjectPublicKeyInfo
                )

            elif key_type.lower() == 'ec':
                # Генерира elliptic curve ключова двойка
                private_key = ec.generate_private_key(ec.SECP256R1(), default_backend())
                public_key = private_key.public_key()

                private_pem = private_key.private_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PrivateFormat.PKCS8,
                    encryption_algorithm=serialization.NoEncryption()
                )

                public_pem = public_key.public_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PublicFormat.SubjectPublicKeyInfo
                )
            else:
                raise UserError(f'Неподдържан тип ключ: {key_type}')

            # Записва частния ключ
            self.add_key_with_user_password(
                f'{key_name}_private',
                f'{key_type}_private',
                private_pem.decode('utf-8')
            )

            # Записва публичния ключ
            self.add_key_with_user_password(
                f'{key_name}_public',
                f'{key_type}_public',
                public_pem.decode('utf-8')
            )

            _logger.info(f"Generated {key_type.upper()} keypair: {key_name}")

            return {
                'private_key_name': f'{key_name}_private',
                'public_key_name': f'{key_name}_public',
                'key_type': key_type
            }

        except Exception as e:
            _logger.error(f"Failed to generate keypair: {str(e)}")
            raise UserError(f'Грешка при генериране на ключове: {str(e)}')

    @api.model
    def get_user_wallet(self, user_id=None):
        """Връща портфела на потребителя, създава го ако не съществува"""
        self._check_permission('read')

        if not user_id:
            user_id = self.env.user.id

        user = self.env['res.users'].browse(user_id)
        current_hash = user.password

        # Търси портфел
        wallet = self.search([('user_id', '=', user_id), ('name', '=', 'System Keys')], limit=1)

        if not wallet:
            # Проверява права за създаване
            if not self.env.user.has_group(self.PERMISSION_LEVELS['write']):
                raise AccessError('Нямате права за създаване на портфейл')

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
        self._check_permission('read')
        wallet = self.get_user_wallet(user_id)
        user = self.env['res.users'].browse(user_id or self.env.user.id)
        return wallet.get_key(key_name, user.password)

    def quick_store(self, key_name, key_type, key_data, user_id=None):
        """Бързо съхранение на ключ"""
        self._check_permission('write')
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

        # Записва на диск
        self._save_to_disk(self.encrypted_data)

        _logger.info(f"Initialized crypto wallet '{self.name}' for user {self.user_id.name}")

    def unlock_wallet(self, master_password):
        """Отключва портфела с главната парола"""
        self._check_permission('read')

        try:
            # Първо проверява дали има данни на диск
            disk_data = self._load_from_disk()
            if disk_data:
                self.encrypted_data = disk_data

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
        self._check_permission('read')
        self.is_locked = True
        self.decrypted_keys = False
        # Изчиства ключа от контекста
        if 'wallet_key' in self.env.context:
            self.env.context = {k: v for k, v in self.env.context.items() if k != 'wallet_key'}
        _logger.debug(f"Wallet '{self.name}' locked")

    def add_key(self, key_name, key_type, key_data, master_password=None):
        """Добавя нов ключ в портфела"""
        self._check_permission('write')

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

        # Също така записва отделен файл за този ключ
        self._save_individual_key_to_disk(key_name, wallet_data['keys'][key_name])

        _logger.debug(f"Added key '{key_name}' of type '{key_type}' to wallet '{self.name}'")
        return True

    def get_key(self, key_name, master_password=None):
        """Извлича ключ от портфела"""
        self._check_permission('read')

        if not master_password:
            master_password = self.get_master_password_for_user()

        # Първо опитва да зареди от отделен файл
        individual_key_data = self._load_individual_key_from_disk(key_name)
        if individual_key_data:
            return individual_key_data

        # Ако няма отделен файл, използва основния портфел
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
        self._check_permission('read')

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
        self._check_permission('write')

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

        # Премахва отделния файл ако съществува
        individual_key_path = self._get_individual_key_path(key_name)
        if individual_key_path.exists():
            try:
                individual_key_path.unlink()
                _logger.info(f"Removed individual key file: {individual_key_path}")
            except Exception as e:
                _logger.error(f"Failed to remove individual key file: {str(e)}")

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

        # Записва на диск
        self._save_to_disk(self.encrypted_data)

        # Актуализира виртуалното поле
        self.decrypted_keys = json.dumps(wallet_data, indent=2)

    def change_master_password(self, old_password, new_password):
        """Променя главната парола на портфела"""
        self._check_permission('admin')

        # Първо отключва с старата парола
        wallet_data = self.unlock_wallet(old_password)

        # Прекриптира с новата парола
        self._reencrypt_wallet_with_new_key(wallet_data, new_password)

        _logger.info(f"Master password changed for wallet '{self.name}'")
        return True

    def export_wallet(self, master_password=None, export_password=None):
        """Експортира портфела за backup"""
        self._check_permission('export')

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
        self._check_permission('admin')

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

        # Записва на диск
        self._save_to_disk(self.encrypted_data)

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

    # ===== SECURITY AND ACCESS CONTROL METHODS =====

    @api.model
    def _get_accessible_wallets(self, permission_level='read'):
        """Връща портфейлите до които потребителят има достъп"""
        # Основните собствени портфейли
        domain = [('user_id', '=', self.env.user.id)]

        # Добавяме портфейли с explicit permissions
        if permission_level in ['read', 'write', 'admin']:
            permissions = self.env['crypto.wallet.permission'].search([
                ('user_id', '=', self.env.user.id),
                ('permission_level', 'in', [permission_level, 'admin']),
                ('is_active', '=', True),
                '|',
                ('expires_date', '=', False),
                ('expires_date', '>', fields.Datetime.now())
            ])

            wallet_ids = permissions.mapped('wallet_id.id')
            if wallet_ids:
                domain = ['|'] + domain + [('id', 'in', wallet_ids)]

        return self.search(domain)

    def _check_record_access(self, operation='read'):
        """Проверява дали текущият потребител има достъп до записа"""
        # Проверява дали е собственик
        if self.user_id == self.env.user:
            return True

        # Проверява дали е админ
        if self.env.user.has_group('l10n_bg_crypto_wallet.group_crypto_wallet_admin'):
            return True

        # Проверява explicit permissions
        permission_levels = {
            'read': ['read', 'write', 'admin', 'export', 'generate'],
            'write': ['write', 'admin', 'generate'],
            'create': ['write', 'admin'],
            'unlink': ['admin']
        }

        required_levels = permission_levels.get(operation, ['admin'])

        permission = self.env['crypto.wallet.permission'].search([
            ('user_id', '=', self.env.user.id),
            ('wallet_id', '=', self.id),
            ('permission_level', 'in', required_levels),
            ('is_active', '=', True),
            '|',
            ('expires_date', '=', False),
            ('expires_date', '>', fields.Datetime.now())
        ])

        return bool(permission)

    @api.model
    def check_access_rights(self, operation, raise_exception=True):
        """Override за допълнителни проверки на права"""
        result = super().check_access_rights(operation, raise_exception=False)

        if not result and raise_exception:
            raise AccessError(f'Нямате права за операция "{operation}" върху Crypto Wallet записи')

        return result

    def check_access_rule(self, operation):
        """Override за проверка на record rules"""
        super().check_access_rule(operation)

        # Допълнителни проверки
        for record in self:
            if not record._check_record_access(operation):
                raise AccessError(f'Нямате достъп до портфел "{record.name}"')

    @api.model
    def grant_permission(self, wallet_id, user_id, permission_level, expires_date=None):
        """Дава разрешение на потребител за достъп до портфел"""
        # Само собственикът или админ може да дава разрешения
        wallet = self.browse(wallet_id)
        if wallet.user_id != self.env.user and not self.env.user.has_group(
            'l10n_bg_crypto_wallet.group_crypto_wallet_admin'):
            raise AccessError('Нямате права да давате разрешения за този портфел')

        # Създава разрешението
        permission = self.env['crypto.wallet.permission'].create({
            'user_id': user_id,
            'wallet_id': wallet_id,
            'permission_level': permission_level,
            'granted_by': self.env.user.id,
            'expires_date': expires_date,
            'is_active': True
        })

        _logger.info(f"Granted {permission_level} permission to user {user_id} for wallet {wallet_id}")
        return permission

    @api.model
    def revoke_permission(self, permission_id):
        """Отнема разрешение"""
        permission = self.env['crypto.wallet.permission'].browse(permission_id)

        # Само давателят на разрешението, собственикът на портфела или админ може да го отнеме
        if (permission.granted_by != self.env.user and
            permission.wallet_id.user_id != self.env.user and
            not self.env.user.has_group('l10n_bg_crypto_wallet.group_crypto_wallet_admin')):
            raise AccessError('Нямате права да отнемате това разрешение')

        permission.is_active = False
        _logger.info(f"Revoked permission {permission_id}")
        return True

    def get_user_permissions_summary(self, user_id=None):
        """Връща обобщение на разрешенията на потребител"""
        if not user_id:
            user_id = self.env.user.id

        # Собствени портфейли
        own_wallets = self.search([('user_id', '=', user_id)])

        # Портфейли с explicit разрешения
        permissions = self.env['crypto.wallet.permission'].search([
            ('user_id', '=', user_id),
            ('is_active', '=', True),
            '|',
            ('expires_date', '=', False),
            ('expires_date', '>', fields.Datetime.now())
        ])

        return {
            'own_wallets_count': len(own_wallets),
            'shared_wallets_count': len(permissions),
            'total_accessible': len(own_wallets) + len(permissions),
            'own_wallets': own_wallets.read(['id', 'name', 'created_date']),
            'shared_wallets': [{
                'wallet_id': p.wallet_id.id,
                'wallet_name': p.wallet_id.name,
                'permission_level': p.permission_level,
                'granted_by': p.granted_by.name,
                'expires_date': p.expires_date
            } for p in permissions]
        }


class CryptoWalletPermission(models.Model):
    """Модел за управление на права за достъп до crypto wallet"""
    _name = 'crypto.wallet.permission'
    _description = 'Crypto Wallet Access Permissions'
    _rec_name = 'user_id'

    user_id = fields.Many2one('res.users', 'User', required=True)
    wallet_id = fields.Many2one('crypto.wallet', 'Wallet', required=True)
    permission_level = fields.Selection([
        ('read', 'Read Only'),
        ('write', 'Read/Write'),
        ('admin', 'Admin'),
        ('generate', 'Generate Keys'),
        ('export', 'Export')
    ], string='Permission Level', required=True)
    granted_by = fields.Many2one('res.users', 'Granted By', required=True)
    granted_date = fields.Datetime('Granted Date', default=fields.Datetime.now)
    expires_date = fields.Datetime('Expires Date')
    is_active = fields.Boolean('Active', default=True)

    @api.model
    def check_user_permission(self, user_id, wallet_id, permission_level):
        """Проверява дали потребителят има определено разрешение"""
        permission = self.search([
            ('user_id', '=', user_id),
            ('wallet_id', '=', wallet_id),
            ('permission_level', '=', permission_level),
            ('is_active', '=', True),
            '|',
            ('expires_date', '=', False),
            ('expires_date', '>', fields.Datetime.now())
        ])
        return bool(permission)

    def check_access_rule(self, operation):
        """Override за проверка на record rules за permissions"""
        super().check_access_rule(operation)

        # Допълнителни проверки за permissions
        for record in self:
            # Потребителят може да вижда разрешения дадени на него
            if record.user_id == self.env.user:
                continue

            # Собственикът на портфела може да управлява разрешенията
            if record.wallet_id.user_id == self.env.user:
                continue

            # Давателят на разрешението може да го управлява
            if record.granted_by == self.env.user:
                continue

            # Админите могат всичко
            if self.env.user.has_group('l10n_bg_crypto_wallet.group_crypto_wallet_admin'):
                continue

            # Ако не е нито едно от горните - няма достъп
            raise AccessError(f'Нямате достъп до разрешение за портфел "{record.wallet_id.name}"')
