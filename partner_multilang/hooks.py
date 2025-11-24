#  Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging
import cyrtranslit
import base64
import re
import idna

from odoo import models, api
from odoo.addons.partner_multilang.models.res_transliterate import partner_name_translate
from odoo.tools import mail

_logger = logging.getLogger(__name__)

email_addr_escapes_re = re.compile(r'[\\"]')


def formataddr(pair, charset='utf-8'):
    """Pretty format a 2-tuple of the form (realname, email_address).

    If the first element of pair is falsy then only the email address
    is returned.

    Set the charset to ascii to get a RFC-2822 compliant email. The
    realname will be base64 encoded (if necessary) and the domain part
    of the email will be punycode encoded (if necessary). The local part
    is left unchanged thus require the SMTPUTF8 extension when there are
    non-ascii characters.

    >>> formataddr(('John Doe', 'johndoe@example.com'))
    '"John Doe" <johndoe@example.com>'

    >>> formataddr(('', 'johndoe@example.com'))
    'johndoe@example.com'
    """
    name, address = pair

    if not address:
        return ''

    local, _, domain = address.rpartition('@')

    try:
        domain.encode(charset)
    except UnicodeEncodeError:
        # rfc5890 - Internationalized Domain Names for Applications (IDNA)
        domain = idna.encode(domain).decode('ascii')

    # Конвертиране на dict в string
    if isinstance(name, dict):
        try:
            env = api.Environment.current
            if env is not None:
                lang = env.context.get('lang') or env.user.lang or 'en_US'
                name = name.get(lang) or next(iter(name.values()), '')
            else:
                name = next(iter(name.values()), '') if name else ''
        except (AttributeError, RuntimeError, TypeError):
            # Няма активен environment или някакъв друг проблем
            name = next(iter(name.values()), '') if name else ''

    # Гарантираме че name е string след всички трансформации
    if not isinstance(name, str):
        name = str(name) if name else ''

    if name:
        try:
            name.encode(charset)
        except UnicodeEncodeError:
            # charset mismatch, encode as utf-8/base64
            # rfc2047 - MIME Message Header Extensions for Non-ASCII Text
            name = base64.b64encode(name.encode('utf-8')).decode('ascii')
            return f"=?utf-8?b?{name}?= <{local}@{domain}>"
        else:
            # ascii name, escape it if needed
            # rfc2822 - Internet Message Format
            #   #section-3.4 - Address Specification
            name = email_addr_escapes_re.sub(r'\\\g<0>', name)
            return f'"{name}" <{local}@{domain}>'

    return f"{local}@{domain}"


def pre_init_hook(env):
    lang = env['res.lang'].with_context(active_test=False).search([('code', '=', 'bg_BG'), ('active', '=', False)])
    if lang:
        lang.action_unarchive()


def post_init_hook(env):
    languages = cyrtranslit.supported()
    for lang in env['res.lang'].with_context(active_test=False).search([]):
        if f"{lang.code[:2]}" in languages:
            lang.transliterate = True

    languages = env['res.lang'].search([('code', '!=', 'en_US'), ('transliterate', '=', True)])
    partners = env['res.partner'].search([])
    for partner_id in partners.filtered(lambda r: r.name):
        text = partner_id.name
        for lang in languages:
            transliterate_lang = partner_name_translate(text, lang.code[:2], lang.transliterate)
            _logger.info(f"Partner {text} => {transliterate_lang} The {lang.code} and is a transliterate language: {lang.transliterate}")
            partner_id.with_context(lang=lang.code).name = text
            partner_id.with_context(lang="en_US").name = transliterate_lang


def post_load_hook():
    from odoo.tools import mail as odoo_mail

    mail.formataddr = formataddr

    # Патч за email_normalize да обработва None и False стойности
    original_email_normalize = odoo_mail.email_normalize

    def email_normalize_patched(email, strict=True):
        """Патчната версия на email_normalize която обработва None и False."""
        # Обработка на None и False
        if email is None or email is False:
            return None if strict else ''

        # Обработка на празни стрингове
        if not email or (isinstance(email, str) and not email.strip()):
            return None if strict else ''

        # Обработка на не-стринг стойности
        if not isinstance(email, str):
            return None if strict else ''

        return original_email_normalize(email, strict=strict)

    odoo_mail.email_normalize = email_normalize_patched
