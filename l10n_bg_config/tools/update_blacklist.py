#!/usr/bin/env python3
"""
BLC Blacklist Manager — инструмент за Росен/BLC

Употреба:
    # Генерира нов Fernet ключ (за нова инсталация)
    python3 update_blacklist.py --generate-key

    # Показва текущия списък (decrypt)
    python3 update_blacklist.py --key <KEY> --show

    # Добавя ДДС номера и обновява файла
    python3 update_blacklist.py --key <KEY> --add BG123456789 BG987654321

    # Задава нов списък (заменя стария)
    python3 update_blacklist.py --key <KEY> --set BG111111111 BG222222222

    # Премахва ДДС номер
    python3 update_blacklist.py --key <KEY> --remove BG123456789

    # Задава съобщение
    python3 update_blacklist.py --key <KEY> --message "Contact support@odoo-shell.dev"

    # Пълен rebuild
    python3 update_blacklist.py --key <KEY> --set BG123 --message "Not licensed"

ВАЖНО:
    Ключът се взима от Odoo → Settings → Technical → System Parameters:
    Key: l10n_bg.blacklist_key

    НИКОГА не commit-вай ключа в репото.
    Commit-вай само data/blacklist.enc.
"""

import argparse
import json
import os
import sys

BLACKLIST_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    'data', 'blacklist.enc',
)


def get_fernet(key: str):
    try:
        from cryptography.fernet import Fernet
        return Fernet(key.encode())
    except ImportError:
        print('ERROR: pip install cryptography', file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f'ERROR: Invalid key — {e}', file=sys.stderr)
        sys.exit(1)


def load_data(f, path: str) -> dict:
    if not os.path.isfile(path):
        return {'vat': [], 'message': ''}
    try:
        with open(path, 'rb') as fh:
            return json.loads(f.decrypt(fh.read()).decode('utf-8'))
    except Exception as e:
        print(f'ERROR: Cannot decrypt existing file — {e}', file=sys.stderr)
        print('Use --set to overwrite with a new list.', file=sys.stderr)
        sys.exit(1)


def save_data(f, path: str, data: dict):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    encrypted = f.encrypt(json.dumps(data, ensure_ascii=False).encode('utf-8'))
    with open(path, 'wb') as fh:
        fh.write(encrypted)
    print(f'✓ {path} updated — {len(data["vat"])} entries')


def normalise(vat: str) -> str:
    return vat.replace(' ', '').upper()


def main():
    parser = argparse.ArgumentParser(
        description='BLC Blacklist Manager',
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument('--generate-key', action='store_true',
                        help='Generate a new Fernet key and print it')
    parser.add_argument('--key', metavar='KEY',
                        help='Fernet key (from ir.config_parameter l10n_bg.blacklist_key)')
    parser.add_argument('--file', metavar='PATH', default=BLACKLIST_FILE,
                        help=f'Path to blacklist.enc (default: {BLACKLIST_FILE})')
    parser.add_argument('--show', action='store_true',
                        help='Print current blacklist as JSON')
    parser.add_argument('--add', nargs='+', metavar='VAT',
                        help='Add VAT number(s) to the blacklist')
    parser.add_argument('--remove', nargs='+', metavar='VAT',
                        help='Remove VAT number(s) from the blacklist')
    parser.add_argument('--set', nargs='*', metavar='VAT',
                        help='Replace entire VAT list (use with no args to clear)')
    parser.add_argument('--message', metavar='MSG',
                        help='Set the warning message shown to blacklisted users')

    args = parser.parse_args()

    # ── generate-key ─────────────────────────────────────────────────────────
    if args.generate_key:
        try:
            from cryptography.fernet import Fernet
        except ImportError:
            print('ERROR: pip install cryptography', file=sys.stderr)
            sys.exit(1)
        key = Fernet.generate_key()
        print(f'Generated key:\n  {key.decode()}')
        print()
        print('Store this in Odoo → Settings → Technical → System Parameters:')
        print('  Key:   l10n_bg.blacklist_key')
        print('  Value: <the key above>')
        print()
        print('Then run update_blacklist.py --key <key> --set to re-encrypt the file.')
        return

    if not args.key:
        parser.error('--key is required (except with --generate-key)')

    f = get_fernet(args.key)
    path = args.file
    data = load_data(f, path)

    modified = False

    if args.show:
        print(json.dumps(data, indent=2, ensure_ascii=False))
        return

    if args.set is not None:
        data['vat'] = [normalise(v) for v in args.set]
        modified = True

    if args.add:
        existing = {normalise(v) for v in data['vat']}
        for vat in args.add:
            n = normalise(vat)
            if n not in existing:
                data['vat'].append(n)
                existing.add(n)
                print(f'  + {n}')
            else:
                print(f'  = {n} (already present)')
        modified = True

    if args.remove:
        before = len(data['vat'])
        to_remove = {normalise(v) for v in args.remove}
        data['vat'] = [v for v in data['vat'] if normalise(v) not in to_remove]
        removed = before - len(data['vat'])
        print(f'  - {removed} entries removed')
        modified = True

    if args.message is not None:
        data['message'] = args.message
        modified = True

    if modified:
        save_data(f, path, data)
        print()
        print('Next steps:')
        print('  git add data/blacklist.enc && git commit -m "[UPD] blacklist"')
        print('  Deploy to servers (git pull + module upgrade)')
    else:
        print('Nothing to do. Use --show, --add, --set, --remove, or --message.')


if __name__ == '__main__':
    main()
