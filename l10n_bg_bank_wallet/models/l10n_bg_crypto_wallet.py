import logging
import os
import json
import base64
import uuid

from datetime import datetime
from pathlib import Path
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend

from odoo import models, fields, api, tools
from odoo.exceptions import UserError, AccessError

_logger = logging.getLogger(__name__)

# Constants extracted to improve maintainability
CRYPTO_CONFIG = {
    'SALT_SIZE': 16,
    'KEY_LENGTH': 32,
    'ITERATIONS': 100000,
    'MAX_KEY_SIZE_BYTES': 65536,  # 64KB
    'FILE_PERMISSIONS': 0o600,
    'DIRECTORY_PERMISSIONS': 0o700,
    'WALLET_VERSION': '1.1',
    'KEY_GENERATION_PARAMS': {
        'rsa': {'key_size': 2048, 'public_exponent': 65537},
        'ec': {'curve': 'SECP256R1'}
    }
}

# Updated permission levels with correct group references
PERMISSION_LEVELS = {
    'read': 'l10n_bg_bank_wallet.group_crypto_wallet_read',
    'write': 'l10n_bg_bank_wallet.group_crypto_wallet_write',
    'admin': 'l10n_bg_bank_wallet.group_crypto_wallet_admin',
    'generate': 'l10n_bg_bank_wallet.group_crypto_wallet_generate',
    'export': 'l10n_bg_bank_wallet.group_crypto_wallet_export'
}


class CryptographyManager:
    """Separated cryptography operations for better code organization"""

    @staticmethod
    def generate_salt():
        """Generate cryptographic salt"""
        return os.urandom(CRYPTO_CONFIG['SALT_SIZE'])

    @staticmethod
    def derive_key(password: str, salt: bytes):
        """Derive an encryption key from password and salt"""
        # user-facing → английски (преводимо); коментарите остават български
        if not isinstance(password, str) or not password:
            raise UserError(
                "A master password is required to create or unlock the wallet. "
                "Open the wallet via the unlock wizard and enter your password. "
                "(The Odoo user password is write-only by design, so the master "
                "password cannot be taken automatically from user_id.password.)"
            )
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=CRYPTO_CONFIG['KEY_LENGTH'],
            salt=salt,
            iterations=CRYPTO_CONFIG['ITERATIONS'],
            backend=default_backend()
        )
        return base64.urlsafe_b64encode(kdf.derive(password.encode()))

    @staticmethod
    def encrypt_data(data: str, key: bytes) -> bytes:
        """Encrypt data with Fernet symmetric encryption"""
        f = Fernet(key)
        return f.encrypt(data.encode())

    @staticmethod
    def decrypt_data(encrypted_data: bytes, key: bytes) -> str:
        """Decrypt data with Fernet symmetric encryption"""
        f = Fernet(key)
        return f.decrypt(encrypted_data).decode()

    @classmethod
    def create_wallet_envelope(cls, wallet_data: dict) -> dict:
        """Create initial wallet data structure"""
        return {
            'version': CRYPTO_CONFIG['WALLET_VERSION'],
            'keys': wallet_data.get('keys', {}),
            'metadata': {
                'created': fields.Datetime.now().isoformat(),
                'key_count': len(wallet_data.get('keys', {})),
                'last_modified': fields.Datetime.now().isoformat()
            }
        }


class FileSystemManager:
    """Separated file system operations for better code organization"""

    def __init__(self, env):
        self.env = env

    def get_wallet_directory(self):
        """Get and create a wallet storage directory"""
        db_name = self.env.cr.dbname
        filestore_path = tools.config.filestore(db_name)
        wallet_dir = Path(filestore_path) / 'crypto_wallets'

        wallet_dir.mkdir(mode=CRYPTO_CONFIG['DIRECTORY_PERMISSIONS'], parents=True, exist_ok=True)
        return wallet_dir

    def generate_wallet_filename(self, wallet_record, key_name=None):
        """Generate secure wallet filename with database and user information"""
        wallet_dir = self.get_wallet_directory()

        # Get or create database UUID
        db_uid = self.env['ir.config_parameter'].sudo().get_param('database.uuid')
        if not db_uid:
            db_uid = str(uuid.uuid4())
            self.env['ir.config_parameter'].sudo().set_param('database.uuid', db_uid)

        # Create abbreviated identifiers
        db_short = db_uid[:8]
        user_short = str(wallet_record.user_id.id).zfill(4)
        wallet_short = str(wallet_record.id).zfill(4)

        if key_name:
            safe_key_name = "".join(c for c in key_name if c.isalnum() or c in '-_').lower()
            filename = f"key_{db_short}_{user_short}_{wallet_short}_{safe_key_name}.enc"
        else:
            safe_wallet_name = wallet_record.name.lower().replace(' ', '_')
            filename = f"wallet_{db_short}_{user_short}_{wallet_short}_{safe_wallet_name}.enc"

        return wallet_dir / filename

    def save_encrypted_file(self, file_path: Path, encrypted_data: bytes):
        """Save encrypted data to file with secure permissions"""
        try:
            with open(file_path, 'wb') as f:
                f.write(encrypted_data)
            os.chmod(file_path, CRYPTO_CONFIG['FILE_PERMISSIONS'])
            _logger.info(f"Wallet data saved to disk: {file_path}")
        except Exception as e:
            _logger.error(f"Failed to save wallet to disk: {str(e)}")
            raise UserError(f'Грешка при записването на диск: {str(e)}')

    def load_encrypted_file(self, file_path: Path) -> bytes | None:
        """Load encrypted data from a file"""
        if not file_path.exists():
            return None

        try:
            with open(file_path, 'rb') as f:
                return f.read()
        except Exception as e:
            _logger.error(f"Failed to load wallet from disk: {str(e)}")
            return None


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

    # Virtual fields (not stored in DB)
    master_password = fields.Char('Master password', store=False)
    decrypted_keys = fields.Text(store=False, readonly=True)

    # CryptographyManager е stateless wrapper (всички методи @static/
    # @classmethod) — class-level reference се ползва навсякъде в
    # този модул като `self._crypto_manager.<method>` (вижда се като
    # обикновен class-level attribute).  Запазваме същия достъп; не
    # се прави assignment на instance, защото Odoo ORM блокира
    # __setattr__ за non-field атрибути.
    _crypto_manager = CryptographyManager

    @property
    def crypto_manager(self):
        return CryptographyManager

    # FileSystemManager е env-bound (всеки cursor може да е различен),
    # затова връщаме нов lightweight instance при всяко обръщане —
    # пак БЕЗ да го кешираме на recordset-а (ORM блокира).
    @property
    def filesystem_manager(self):
        return FileSystemManager(self.env)

    # === PERMISSION AND ACCESS CONTROL ===
    def _check_permission_level(self, permission_level):
        """Simplified permission check - only owner or admin"""
        # Check if owner
        if self.user_id == self.env.user:
            return True

        # Check if system admin - using the correct group reference
        if self.env.user.has_group(PERMISSION_LEVELS['admin']):
            return True

        raise AccessError(f'Нямате разрешение за операция: {permission_level}')

    def _validate_record_access(self, operation='read'):
        """Check if the current user has access to this wallet record"""
        if self.user_id != self.env.user and not self.env.user.has_group(PERMISSION_LEVELS['admin']):
            raise AccessError(f'Нямате достъп до портфел "{self.name}"')
        return True

    def check_access(self, operation):
        """Override for record access checks - updated for Odoo 18.0"""
        super().check_access(operation)

        # Additional checks for existing records
        for record in self:
            if not record._validate_record_access(operation):
                raise AccessError(f'Нямате достъп до портфел "{record.name}"')

    # === CORE WALLET OPERATIONS ===
    def _initialize_empty_wallet(self, master_password):
        """Initialize an empty encrypted wallet-extracted method"""
        salt = self.crypto_manager.generate_salt()
        self.salt = base64.b64encode(salt).decode()

        key = self.crypto_manager.derive_key(master_password, salt)
        empty_wallet = self.crypto_manager.create_wallet_envelope({})

        encrypted_data = self.crypto_manager.encrypt_data(json.dumps(empty_wallet), key)
        self.encrypted_data = base64.b64encode(encrypted_data).decode()

        self._persist_wallet_to_disk()
        _logger.info("Initialized crypto wallet '%s' for user %s",
                     self.name, self.user_id.name)

    def _persist_wallet_to_disk(self):
        """Save wallet data to disk - extracted method"""
        file_path = self.filesystem_manager.generate_wallet_filename(self)
        encrypted_data = base64.b64decode(self.encrypted_data)

        self.filesystem_manager.save_encrypted_file(file_path, encrypted_data)
        self.file_path = str(file_path)

    def _load_wallet_from_disk(self):
        """Load wallet data from disk - extracted method"""
        if not self.file_path or not os.path.exists(self.file_path):
            return None

        file_path = Path(self.file_path)
        encrypted_data = self.filesystem_manager.load_encrypted_file(file_path)

        return base64.b64encode(encrypted_data).decode() if encrypted_data else None

    def unlock_wallet_with_password(self, master_password):
        """Unlock wallet with master password - renamed for clarity"""
        self._check_permission_level('read')

        try:
            # Load from disk if needed
            disk_data = self._load_wallet_from_disk()
            if disk_data:
                self.encrypted_data = disk_data

            # Decrypt wallet data
            salt = base64.b64decode(self.salt)
            key = self._crypto_manager.derive_key(master_password, salt)

            encrypted_data = base64.b64decode(self.encrypted_data)
            decrypted_json = self._crypto_manager.decrypt_data(encrypted_data, key)
            wallet_data = json.loads(decrypted_json)

            # Update session state
            self._update_session_state(key, wallet_data)

            _logger.debug(f"Wallet '{self.name}' unlocked successfully")
            return wallet_data

        except Exception as e:
            _logger.error(f"Failed to unlock wallet '{self.name}': {str(e)}")
            raise UserError('Грешна главна парола или повредени данни в портфела')

    def _update_session_state(self, encryption_key, wallet_data):
        """Update session state after successful unlock - extracted method"""
        self.is_locked = False
        self.last_accessed = fields.Datetime.now()
        self.decrypted_keys = json.dumps(wallet_data, indent=2)
        self.env.context = dict(self.env.context, wallet_key=encryption_key.decode())

    def lock_wallet(self):
        """Lock the wallet"""
        self._check_permission_level('read')
        self.is_locked = True
        self.decrypted_keys = False
        # Clear key from context
        if 'wallet_key' in self.env.context:
            self.env.context = {k: v for k, v in self.env.context.items() if k != 'wallet_key'}
        _logger.debug(f"Wallet '{self.name}' locked")

    # === SIMPLIFIED USER INTERFACE METHODS ===
    @staticmethod
    def _read_bcrypt_hash(env, user_id):
        """Връща bcrypt hash-а на потребителя от колоната res_users.password.

        res.users.password през ORM в Odoo 17+ е write-only и при четене
        ВИНАГИ е False.  Реалният bcrypt hash (с който се ключира
        портфелът — виж res_users._create_initial_wallet) живее в
        колоната res_users.password; привилегированият wallet код го чете
        директно през SQL.  Това е master password-ът на портфела —
        консистентно при създаване, отключване и cron.
        """
        if not user_id:
            return False
        env.cr.execute(
            "SELECT password FROM res_users WHERE id = %s", (user_id,))
        row = env.cr.fetchone()
        return row[0] if row and row[0] else False

    def get_user_master_password(self):
        """Get master password for current user - renamed for clarity"""
        self._check_permission_level('read')
        return self._read_bcrypt_hash(self.env, self.user_id.id)

    def unlock_with_user_password(self):
        """Unlock wallet using user's master password"""
        self._check_permission_level('read')
        master_password = self.get_user_master_password()
        return self.unlock_wallet_with_password(master_password)

    # === KEY MANAGEMENT OPERATIONS ===
    def add_key_with_user_password(self, key_name, key_type, key_data):
        """Add key using user's master password"""
        self._check_permission_level('write')
        master_password = self.get_user_master_password()
        return self._add_key_to_wallet(key_name, key_type, key_data, master_password)

    def get_key_with_user_password(self, key_name):
        """Get key using user's password"""
        self._check_permission_level('read')
        master_password = self.get_user_master_password()
        return self._get_key_from_wallet(key_name, master_password)

    def remove_key_with_user_password(self, key_name):
        """Remove key using user's password"""
        self._check_permission_level('write')
        master_password = self.get_user_master_password()
        return self._remove_key_from_wallet(key_name, master_password)

    def list_keys_with_user_password(self):
        """List keys using user's password"""
        self._check_permission_level('read')
        master_password = self.get_user_master_password()
        return self._list_wallet_keys(master_password)

    # === INTERNAL KEY OPERATIONS ===
    def _add_key_to_wallet(self, key_name, key_type, key_data, master_password):
        """Internal method to add key to wallet - extracted for reuse"""
        wallet_data = self._get_or_unlock_wallet(master_password)

        wallet_data['keys'][key_name] = {
            'type': key_type,
            'data': key_data,
            'created': fields.Datetime.now().isoformat(),
            'metadata': {}
        }

        self._update_wallet_metadata(wallet_data)
        self._save_wallet_data(wallet_data)
        self._save_individual_key_to_disk(key_name, wallet_data['keys'][key_name])

        _logger.debug(f"Added key '{key_name}' of type '{key_type}' to wallet '{self.name}'")
        return True

    def _get_key_from_wallet(self, key_name, master_password):
        """Internal method to get key from wallet"""
        # First try to load from individual file
        individual_key_data = self._load_individual_key_from_disk(key_name)
        if individual_key_data:
            return individual_key_data

        # If no individual file, use main wallet
        wallet_data = self._get_or_unlock_wallet(master_password)

        if key_name not in wallet_data['keys']:
            raise UserError(f'Ключ "{key_name}" не съществува в портфела')

        return wallet_data['keys'][key_name]

    def _remove_key_from_wallet(self, key_name, master_password):
        """Internal method to remove key from wallet"""
        wallet_data = self._get_or_unlock_wallet(master_password)

        if key_name not in wallet_data['keys']:
            raise UserError(f'Ключ "{key_name}" не съществува в портфела')

        # Remove key
        del wallet_data['keys'][key_name]
        self._update_wallet_metadata(wallet_data)
        self._save_wallet_data(wallet_data)

        # Remove individual file if exists
        individual_key_path = self.filesystem_manager.generate_wallet_filename(self, key_name)
        if individual_key_path.exists():
            try:
                individual_key_path.unlink()
                _logger.info(f"Removed individual key file: {individual_key_path}")
            except Exception as e:
                _logger.error(f"Failed to remove individual key file: {str(e)}")

        _logger.debug(f"Removed key '{key_name}' from wallet '{self.name}'")
        return True

    def _list_wallet_keys(self, master_password):
        """Internal method to list wallet keys"""
        wallet_data = self._get_or_unlock_wallet(master_password)

        keys_info = []
        for key_name, key_info in wallet_data['keys'].items():
            keys_info.append({
                'name': key_name,
                'type': key_info['type'],
                'created': key_info['created']
            })

        return keys_info

    def _get_or_unlock_wallet(self, master_password):
        """Get wallet data, unlock if necessary - extracted method"""
        if self.is_locked:
            return self.unlock_wallet_with_password(master_password)

        wallet_key = self.env.context.get('wallet_key')
        if not wallet_key:
            return self.unlock_wallet_with_password(master_password)

        encrypted_data = base64.b64decode(self.encrypted_data)
        decrypted_json = self._crypto_manager.decrypt_data(encrypted_data, wallet_key.encode())
        return json.loads(decrypted_json)

    def _update_wallet_metadata(self, wallet_data):
        """Update wallet metadata - extracted method"""
        wallet_data['metadata']['key_count'] = len(wallet_data['keys'])
        wallet_data['metadata']['last_modified'] = fields.Datetime.now().isoformat()

    def _save_wallet_data(self, wallet_data):
        """Save wallet data with current encryption key - extracted method"""
        wallet_key = self.env.context.get('wallet_key')
        if not wallet_key:
            master_password = self.get_user_master_password()
            self.unlock_wallet_with_password(master_password)
            wallet_key = self.env.context.get('wallet_key')

        encrypted_data = self._crypto_manager.encrypt_data(json.dumps(wallet_data), wallet_key.encode())
        self.encrypted_data = base64.b64encode(encrypted_data).decode()

        self._persist_wallet_to_disk()
        self.decrypted_keys = json.dumps(wallet_data, indent=2)

    # === INDIVIDUAL KEY FILE MANAGEMENT ===
    def _save_individual_key_to_disk(self, key_name, key_data):
        """Save individual key to separate file - simplified"""
        file_path = self.filesystem_manager.generate_wallet_filename(self, key_name)

        key_envelope = {
            'key_name': key_name,
            'wallet_id': self.id,
            'user_id': self.user_id.id,
            'created': fields.Datetime.now().isoformat(),
            'data': key_data
        }

        master_password = self.get_user_master_password()
        salt = self._crypto_manager.generate_salt()
        key = self._crypto_manager.derive_key(master_password, salt)

        encrypted_envelope = {
            'salt': base64.b64encode(salt).decode(),
            'data': base64.b64encode(self._crypto_manager.encrypt_data(json.dumps(key_envelope), key)).decode()
        }

        # Save as JSON file
        with open(file_path, 'w') as file:
            json.dump(encrypted_envelope, file)
        os.chmod(file_path, CRYPTO_CONFIG['FILE_PERMISSIONS'])

        _logger.info(f"Individual key saved to disk: {file_path}")
        return str(file_path)

    def _load_individual_key_from_disk(self, key_name):
        """Load individual key from disk"""
        file_path = self.filesystem_manager.generate_wallet_filename(self, key_name)

        if not file_path.exists():
            return None

        try:
            with open(file_path, 'r') as file:
                encrypted_envelope = json.load(file)

            # Decrypt data
            master_password = self.get_user_master_password()
            salt = base64.b64decode(encrypted_envelope['salt'])
            key = self._crypto_manager.derive_key(master_password, salt)

            decrypted_data = self._crypto_manager.decrypt_data(
                base64.b64decode(encrypted_envelope['data']), key
            )
            key_envelope = json.loads(decrypted_data)

            return key_envelope['data']

        except Exception as e:
            _logger.error(f"Failed to load individual key from disk: {str(e)}")
            return None

    # === CRYPTOGRAPHIC KEY GENERATION ===
    def generate_keypair(self, key_name, key_type='rsa'):
        """Generate keypair (public/private)"""
        self._check_permission_level('generate')

        from cryptography.hazmat.primitives.asymmetric import rsa, ec
        from cryptography.hazmat.primitives import serialization

        try:
            if key_type.lower() == 'rsa':
                # Generate RSA keypair
                private_key = rsa.generate_private_key(
                    public_exponent=CRYPTO_CONFIG['KEY_GENERATION_PARAMS']['rsa']['public_exponent'],
                    key_size=CRYPTO_CONFIG['KEY_GENERATION_PARAMS']['rsa']['key_size'],
                    backend=default_backend()
                )
                public_key = private_key.public_key()

                # Serialize keys
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
                # Generate elliptic curve keypair
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

            # Save private key
            self.add_key_with_user_password(
                f'{key_name}_private',
                f'{key_type}_private',
                private_pem.decode('utf-8')
            )

            # Save public key
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

    # === USER WALLET MANAGEMENT ===
    @api.model
    def get_user_wallet_or_create(self, user_id=None):
        """Get user wallet, create if doesn't exist."""
        if not user_id:
            user_id = self.env.user.id

        user = self.env['res.users'].browse(user_id)
        current_hash = user.password

        wallet = self.search([('user_id', '=', user_id), ('name', '=', 'System Keys')], limit=1)

        if not wallet:
            if not self.env.user.has_group(PERMISSION_LEVELS['write']):
                raise AccessError('Нямате права за създаване на портфейл')

            wallet = self.create({
                'name': 'System Keys',
                'user_id': user_id,
                'master_password': current_hash
            })
            _logger.info("Created new crypto wallet for user %s", user_id)
        else:
            # Verify wallet sync
            try:
                wallet.unlock_wallet_with_password(current_hash)
                _logger.debug("Wallet sync verified for user %s", user_id)
            except Exception:
                _logger.warning("Wallet desync for user %s, reinitializing", user_id)
                wallet._initialize_empty_wallet(current_hash)

        return wallet

    @api.model
    def get_user_wallet(self, user_id=None):
        """Get a user wallet without creating if it doesn't exist."""
        if not user_id:
            user_id = self.env.user.id

        wallet = self.search([('user_id', '=', user_id), ('name', '=', 'System Keys')], limit=1)

        if not wallet:
            raise UserError('Няма създаден портфейл за потребител с ID %s' % user_id)

        return wallet

    def quick_access(self, key_name, user_id=None):
        """Quick access to the key"""
        wallet = self.get_user_wallet_or_create(user_id)
        wallet._check_permission_level('read')
        user = self.env['res.users'].browse(user_id or self.env.user.id)
        return wallet._get_key_from_wallet(key_name, user.password)

    def quick_store(self, key_name, key_type, key_data, user_id=None):
        """Quick key storage"""
        wallet = self.get_user_wallet_or_create(user_id)
        wallet._check_permission_level('write')
        user = self.env['res.users'].browse(user_id or self.env.user.id)
        return wallet._add_key_to_wallet(key_name, key_type, key_data, user.password)

    # === WALLET LIFECYCLE METHODS ===
    @api.model_create_multi
    def create(self, vals_list):
        """Create new crypto wallet records"""

        processed_vals_list = []
        master_passwords = []

        for vals in vals_list:
            processed_vals = vals.copy()
            master_password = processed_vals.pop('master_password', None) or self.get_user_master_password()
            # get_user_master_password() връща user_id.password, който в Odoo е
            # write-only и при четене ВИНАГИ е False. Затова при създаване без
            # изрично подадена master_password няма как да инициализираме портфела —
            # отказваме ясно вместо krash в derive_key (bool.encode()).
            if not isinstance(master_password, str) or not master_password:
                raise UserError(
                    "The wallet cannot be created without a master password. "
                    "Create/unlock it via the wizard (Wallet → Unlock) or pass "
                    "an explicit \"master_password\" on creation. The Odoo user "
                    "password is write-only by design and cannot be read back."
                )

            master_passwords.append(master_password)
            processed_vals_list.append(processed_vals)

        wallets = super().create(processed_vals_list)

        for wallet, master_password in zip(wallets, master_passwords):
            wallet._initialize_empty_wallet(master_password)

        return wallets

    def write(self, vals):
        """Update crypto wallet records"""
        self._check_permission_level('write')

        if 'master_password' in vals:
            master_password = vals.pop('master_password')

            # First standard update
            result = super().write(vals)

            # Then handle master_password for each record
            for wallet in self:
                if wallet.encrypted_data:
                    # If wallet has data, re-encrypt with new password
                    try:
                        current_password = wallet.get_user_master_password()
                        wallet_data = wallet.unlock_wallet_with_password(current_password)
                        wallet._reencrypt_wallet_with_new_key(wallet_data, master_password)
                    except Exception as e:
                        _logger.error(f"Failed to reencrypt wallet during write: {str(e)}")
                        # Fallback - create new wallet
                        wallet._initialize_empty_wallet(master_password)
                else:
                    # If no data, just initialize
                    wallet._initialize_empty_wallet(master_password)

            return result
        else:
            # Standard update without master_password
            return super().write(vals)

    def unlink(self):
        """Remove wallet and file from disk"""
        self._check_permission_level('admin')

        for wallet in self:
            if wallet.file_path and os.path.exists(wallet.file_path):
                try:
                    os.remove(wallet.file_path)
                    _logger.info(f"Deleted wallet file: {wallet.file_path}")
                except Exception as e:
                    _logger.error(f"Failed to delete wallet file: {str(e)}")

        return super().unlink()

    # === PASSWORD MANAGEMENT ===
    def change_master_password(self, old_password, new_password):
        """Change wallet master password"""
        self._check_permission_level('admin')

        # First unlock with old password
        wallet_data = self.unlock_wallet_with_password(old_password)

        # Re-encrypt with a new password
        self._reencrypt_wallet_with_new_key(wallet_data, new_password)

        _logger.info(f"Master password changed for wallet '{self.name}'")
        return True

    def _reencrypt_wallet_with_new_key(self, wallet_data, new_master_password):
        """Re-encrypt wallet with new master key"""
        # Generate new salt
        salt = self._crypto_manager.generate_salt()
        self.salt = base64.b64encode(salt).decode()

        # Create new encryption key
        new_key = self._crypto_manager.derive_key(new_master_password, salt)

        # Update metadata
        wallet_data['metadata']['reencrypted'] = fields.Datetime.now().isoformat()
        wallet_data['metadata']['reencryption_reason'] = 'password_change'

        # Encrypt with a new key
        encrypted_data = self._crypto_manager.encrypt_data(json.dumps(wallet_data), new_key)
        self.encrypted_data = base64.b64encode(encrypted_data).decode()

        # Save to disk
        self._persist_wallet_to_disk()

        # Update context
        self.env.context = dict(self.env.context, wallet_key=new_key.decode())
        self.is_locked = False

        _logger.debug(f"Wallet '{self.name}' reencrypted successfully")

    def auto_reencrypt_on_password_change(self, old_password, new_password):
        """Re-encrypt wallet when user password changes (called from login)."""
        self.ensure_one()
        try:
            wallet_data = self.unlock_wallet_with_password(old_password)
            self._reencrypt_wallet_with_new_key(wallet_data, new_password)
            _logger.info("Auto-reencrypted wallet '%s' on password change", self.name)
            return True
        except Exception:
            _logger.exception("Auto-reencrypt failed for wallet '%s'", self.name)
            return False

    # === EXPORT FUNCTIONALITY ===
    def export_wallet(self, master_password=None, export_password=None):
        """Export wallet for backup"""
        self._check_permission_level('export')

        if not master_password:
            master_password = self.get_user_master_password()

        wallet_data = self.unlock_wallet_with_password(master_password)

        export_data = {
            'wallet_name': self.name,
            'export_date': fields.Datetime.now().isoformat(),
            'data': wallet_data
        }

        if export_password:
            # Encrypt export with different password
            salt = self._crypto_manager.generate_salt()
            key = self._crypto_manager.derive_key(export_password, salt)

            encrypted_export = self._crypto_manager.encrypt_data(json.dumps(export_data), key)

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

    # === FILE SYSTEM UTILITIES ===
    def list_wallet_files_on_disk(self):
        """Show all wallet files on disk"""
        self._check_permission_level('admin')

        wallet_dir = self.filesystem_manager.get_wallet_directory()
        db_uid = self.env['ir.config_parameter'].sudo().get_param('database.uuid', 'unknown')
        db_short = db_uid[:8]
        user_short = str(self.user_id.id).zfill(4)
        wallet_short = str(self.id).zfill(4)

        # Search all files related to this wallet
        pattern = f"{db_short}_{user_short}_{wallet_short}_*"
        files = list(wallet_dir.glob(f"*{pattern}*"))

        file_info = []
        for file_path in files:
            stat = file_path.stat()
            file_info.append({
                'name': file_path.name,
                'path': str(file_path),
                'size': stat.st_size,
                'created': datetime.fromtimestamp(stat.st_ctime),
                'modified': datetime.fromtimestamp(stat.st_mtime),
                'permissions': oct(stat.st_mode)[-3:]
            })

        return file_info

    def cleanup_orphaned_files(self):
        """Clean up files without corresponding records in database"""
        self._check_permission_level('admin')

        wallet_dir = self.filesystem_manager.get_wallet_directory()
        all_files = list(wallet_dir.glob("*.enc"))

        # Get all active wallets
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
            file_pattern = "_".join(file_path.stem.split("_")[1:4])  # take db_user_wallet part
            if file_pattern not in active_patterns:
                orphaned_files.append(file_path)

        # Remove orphaned files
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

    # === BUTTON ACTIONS FOR UI ===
    def action_unlock_wallet(self):
        """Action for 'Unlock Wallet' button - opens wizard"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Отключи портфела',
            'res_model': 'crypto.wallet.unlock.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_wallet_id': self.id},
        }

    def action_change_master_password(self):
        """Action for 'Change Master Password' button - opens wizard"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Промени главната парола',
            'res_model': 'crypto.wallet.change.password.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_wallet_id': self.id},
        }

    def action_export_wallet(self):
        """Action for 'Export Wallet' button - opens wizard"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Export wallet',
            'res_model': 'crypto.wallet.export.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_wallet_id': self.id},
        }

    def action_import_wallet_from_zip(self):
        # Отваря import wizard-а за качване на AES-256 ZIP файл
        # с keys и flatten в текущия портфейл.
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Import keys from ZIP',
            'res_model': 'crypto.wallet.import.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_wallet_id': self.id},
        }

    def action_manage_keys(self):
        """Action for the 'Manage Keys' button-shows key management interface"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': f'Ключове в портфел "{self.name}"',
            'res_model': 'crypto.wallet.key.manager',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_wallet_id': self.id},
        }

    def action_add_key(self):
        """Action for 'Add Key' button - opens wizard"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Добави ключ',
            'res_model': 'crypto.wallet.add.key.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_wallet_id': self.id},
        }

    def action_list_keys(self):
        """Action for the 'Show All Keys' button - shows a detailed list"""
        self.ensure_one()
        try:
            keys_info = self.list_keys_with_user_password()

            if not keys_info:
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': 'Информация',
                        'message': 'Няма съхранени ключове в този портфел.',
                        'type': 'info',
                        'sticky': False,
                    }
                }

            # Generate text representation of keys
            keys_text = []
            for key_info in keys_info:
                keys_text.append(f"• {key_info['name']} ({key_info['type']}) - създаден {key_info['created']}")

            message = f"""
            <strong>Ключове в портфел "{self.name}":</strong><br/>
            <br/>
            {('<br/>'.join(keys_text))}
            <br/><br/>
            <strong>Общо: {len(keys_info)} ключа</strong>
            """

            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': f'Ключове в портфел "{self.name}"',
                    'message': message,
                    'type': 'info',
                    'sticky': True,
                }
            }

        except Exception as e:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Грешка',
                    'message': f'Не може да се заредят ключовете: {str(e)}',
                    'type': 'danger',
                    'sticky': False,
                }
            }

    # === COPY KEY FUNCTIONALITY ===
    def copy_key_to_user(self, key_name, target_user_id):
        """Copy key to another user's wallet"""
        self._check_permission_level('admin')  # Only admins can copy keys between users

        # Get key from current wallet
        my_key_data = self.get_key_with_user_password(key_name)

        # Find/create a target user's wallet
        target_wallet = self.get_user_wallet_or_create(target_user_id)

        # Add copy of key to their wallet (encrypted with their password)
        target_wallet.add_key_with_user_password(
            key_name=f"shared_{key_name}",
            key_type=my_key_data['type'],
            key_data=my_key_data['data']
        )

        _logger.info(f"Copied key '{key_name}' from user {self.user_id.id} to user {target_user_id}")
        return True

    # === AES-256 PASSWORD-PROTECTED ZIP EXPORT / IMPORT ===

    @staticmethod
    def _classify_keys_into_sections(raw_keys):
        # Групира flat keys dict в три именувани section-а за
        # readability при manual editing на JSON-а.  Heuristic:
        # `infopay_admin_*` → admin, други `infopay_*` → user, всичко
        # друго → other.  Import-ът flatten-ва обратно — имената на
        # ключовете остават меродавни, sections са само label.
        sections = {
            'user': {
                'description':
                    'User-side credentials — payment-initiation '
                    'scope (e.g. InfoPay).  Decrypts with the wallet '
                    'owner password; used in interactive flows.',
                'keys': {},
            },
            'admin': {
                'description':
                    'Admin-side credentials — read-only scope (e.g. '
                    'InfoPay).  Used by cron / server-side polling '
                    'via sudo to the wallet owner.',
                'keys': {},
            },
            'other': {
                'description':
                    'Other keys not matching a known naming '
                    'convention (RSA / SSH / PGP / certificates / '
                    'arbitrary).',
                'keys': {},
            },
        }
        if not isinstance(raw_keys, dict):
            return sections
        for name, info in raw_keys.items():
            if not isinstance(info, dict):
                continue
            # Sections heuristic — string prefix-based
            if name.startswith('infopay_admin_'):
                sect = 'admin'
            elif name.startswith('infopay_'):
                sect = 'user'
            else:
                sect = 'other'
            sections[sect]['keys'][name] = info
        return sections

    def export_keys_to_zip_bytes(self, master_password=None,
                                  zip_password=None):
        """Връща bytes на AES-256 ZIP архив, който съдържа JSON със
        всички ключове на портфейла.

        Параметри:
            master_password: парола за отключване на портфейла.  Ако
                е None — взима се bcrypt hash на текущия user.
            zip_password: парола за защита на ZIP файла (AES-256).
                Задължително.

        Връща:
            bytes (целия ZIP файл, готов за download).
        """
        # Проверка на права за експорт
        self._check_permission_level('export')

        if not zip_password:
            raise UserError("ZIP password is required.")

        # pyzipper е external dep — error при липса
        try:
            import pyzipper
        except ImportError as exc:
            raise UserError(
                "pyzipper Python library is required for AES-256 ZIP "
                "export.  Install it: pip install pyzipper",
            ) from exc

        # Отключваме wallet-а с master password
        if not master_password:
            master_password = self.get_user_master_password()
        wallet_data = self.unlock_wallet_with_password(master_password)

        # JSON payload вътре в ZIP-а: groupiranи sections (admin/user/other)
        # + metadata.  Sections са за човешка readability при ръчна
        # подготовка на файла; import-ът ги flatten-ва обратно в
        # wallet keys dict (имената остават unchanged).
        raw_keys = wallet_data.get('keys', {})
        sections = self._classify_keys_into_sections(raw_keys)
        payload = {
            'wallet_name': self.name,
            'wallet_user_login': self.user_id.login,
            'export_date': fields.Datetime.now().isoformat(),
            'wallet_version': CRYPTO_CONFIG['WALLET_VERSION'],
            'sections': sections,
        }
        json_bytes = json.dumps(payload, ensure_ascii=False,
                                indent=2).encode('utf-8')

        # AES-256 ZIP — pyzipper AESZipFile + WZ_AES = WinZip AES
        import io
        buf = io.BytesIO()
        with pyzipper.AESZipFile(
            buf, 'w',
            compression=pyzipper.ZIP_DEFLATED,
            encryption=pyzipper.WZ_AES,
        ) as zf:
            zf.setpassword(zip_password.encode('utf-8'))
            zf.writestr('wallet_export.json', json_bytes)

        total_keys = sum(
            len(s.get('keys') or {})
            for s in sections.values() if isinstance(s, dict)
        )
        _logger.info(
            "Wallet '%s' exported to AES-256 ZIP (%d keys, %d bytes).",
            self.name, total_keys, buf.tell(),
        )
        return buf.getvalue()

    def import_keys_from_zip_bytes(self, zip_bytes, zip_password,
                                    master_password=None,
                                    overwrite=False):
        """Импортира ключове от AES-256 ZIP в текущия портфейл.

        Параметри:
            zip_bytes: bytes на ZIP файла (binary upload).
            zip_password: паролата за разкодиране на ZIP-а.
            master_password: master password за wallet-а.  Ако е None
                — взима bcrypt hash на текущия user.
            overwrite: ако True — презаписва ключове със същото име.
                По default skip-ва дубликатите.

        Връща dict: ``{'imported': int, 'skipped': int, 'overwritten':
        int, 'keys_imported': [names], 'keys_skipped': [names]}``.
        """
        # Проверка на права за писане
        self._check_permission_level('write')

        if not zip_password:
            raise UserError("ZIP password is required.")
        if not zip_bytes:
            raise UserError("ZIP content is empty.")

        try:
            import pyzipper
        except ImportError as exc:
            raise UserError(
                "pyzipper Python library is required for AES-256 ZIP "
                "import.  Install it: pip install pyzipper",
            ) from exc

        # Разкодираме ZIP-а
        import io
        buf = io.BytesIO(zip_bytes)
        try:
            with pyzipper.AESZipFile(buf) as zf:
                zf.setpassword(zip_password.encode('utf-8'))
                names = zf.namelist()
                if 'wallet_export.json' not in names:
                    raise UserError(
                        "ZIP does not contain 'wallet_export.json'. "
                        "File: %s" % ", ".join(names),
                    )
                raw = zf.read('wallet_export.json')
        except RuntimeError as exc:
            # pyzipper хвърля RuntimeError при грешна парола
            raise UserError(
                "Cannot decrypt ZIP — wrong password or corrupted file.",
            ) from exc

        try:
            payload = json.loads(raw.decode('utf-8'))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise UserError(
                "wallet_export.json is malformed.",
            ) from exc

        # Поддържаме два формата:
        #   - новият (1.0.6+): payload['sections'] = {admin: {keys},
        #     user: {keys}, other: {keys}} — flatten-ваме обратно
        #   - legacy: payload['keys'] = flat dict (1.0.6 RC builds)
        keys = {}
        sections = payload.get('sections')
        if isinstance(sections, dict):
            for sect_data in sections.values():
                if isinstance(sect_data, dict):
                    sect_keys = sect_data.get('keys') or {}
                    if isinstance(sect_keys, dict):
                        keys.update(sect_keys)
        elif isinstance(payload.get('keys'), dict):
            keys = payload['keys']

        if not keys:
            raise UserError(
                "Export payload has no keys (neither 'sections' nor "
                "'keys' contain entries).",
            )

        # Подсигурявам че wallet-ът съществува и е достъпен с master.
        # Три случая:
        #   1. Wallet е initialized с правилен master → list_keys успява
        #   2. Wallet record exists но encrypted_data е празно (never
        #      initialized) → list_keys fails с decrypt error → ние
        #      initialize-ваме empty wallet със master_password
        #   3. Wallet е initialized с друг master → не можем нищо;
        #      пробрасваме informative error
        if not master_password:
            master_password = self.get_user_master_password()
        try:
            existing = self._list_wallet_keys(master_password) or []
            existing_names = {k.get('name') for k in existing
                              if isinstance(k, dict)}
        except UserError:
            # Случай 2 или 3 — пробваме auto-initialize.  Ако wallet-ът
            # реално е initialized със стара парола, _initialize_empty_wallet
            # ще го пренапише — затова правим това САМО ако encrypted_data
            # е празно.
            if not (self.encrypted_data and self.salt):
                self._initialize_empty_wallet(master_password)
                _logger.info(
                    "Auto-initialized empty wallet '%s' for import.",
                    self.name,
                )
                existing = []
                existing_names = set()
            else:
                # Случай 3 — wallet е initialized но master не пасва.
                # Не можем silently to overwrite — operator-ът трябва
                # първо да го отключи или да смени password обратно.
                raise UserError(
                    "Wallet '%s' is encrypted with a different master "
                    "password than the one provided.  Unlock it first "
                    "(or use the original master password)." % self.name,
                )

        imported = []
        skipped = []
        overwritten = []
        for name, info in keys.items():
            if not isinstance(info, dict) or 'data' not in info:
                # Skip-ваме malformed entries
                skipped.append(name)
                continue
            key_type = info.get('type', 'custom')
            key_data = info['data']
            if name in existing_names:
                if not overwrite:
                    skipped.append(name)
                    continue
                # Презаписваме — изтриваме старите и добавяме нови
                self._remove_key_from_wallet(name, master_password)
                self._add_key_to_wallet(name, key_type, key_data,
                                         master_password)
                overwritten.append(name)
            else:
                self._add_key_to_wallet(name, key_type, key_data,
                                         master_password)
                imported.append(name)

        _logger.info(
            "Wallet '%s' import done: +%d imported, %d skipped, "
            "%d overwritten.",
            self.name, len(imported), len(skipped), len(overwritten),
        )
        return {
            'imported': len(imported),
            'skipped': len(skipped),
            'overwritten': len(overwritten),
            'keys_imported': imported,
            'keys_skipped': skipped,
            'keys_overwritten': overwritten,
        }
