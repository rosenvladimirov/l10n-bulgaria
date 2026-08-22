# Copyright 2026 Rosen Vladimirov, Terraros Commerce Ltd.
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
"""Съживява мъртвия гард в `bootstrap_translations`.

Ядрото (`web/controllers/webclient.py:38`) пише:

    f_name = file_path(f'{addon_name}/i18n/{lang}.po')
    if not f_name:
        continue

Намерението е ясно: липсва ли каталог, модулът се прескача. Само че `file_path`
ХВЪРЛЯ `FileNotFoundError`, вместо да върне празно (`tools/misc.py:196`), тъй че
редът `if not f_name` не се стига НИКОГА.

Последицата не е козметична: клиентът чака точно този отговор при зареждане, а
JSON-RPC връща HTTP 200 с грешка вътре — тоест в лога изглежда като успешна
заявка. Един bootstrap модул без превод за един активен език и всички сесии
получават бял екран.

⚠️ Защо се пипа символът, а не методът: пренаписването на метода дублира
ядрена логика, която ще се разминава при всяко обновяване. Тук се сменя само
`file_path`, както е ИМПОРТНАТ в този модул — в него той се ползва на едно
единствено място (проверено: ред 9 импорт, ред 38 употреба). Извън контролера
поведението остава непроменено.
"""

import logging

from odoo.addons.web.controllers import webclient
from odoo.tools.misc import file_path as _core_file_path

_logger = logging.getLogger(__name__)

#: Пази се, за да е ясно, че кръпката е идемпотентна — второ зареждане на
#: модула не увива обвивката в обвивка.
_PATCH_FLAG = "_l10n_bg_missing_catalogue_guard"


def _file_path_or_none(path, *args, **kwargs):
    try:
        return _core_file_path(path, *args, **kwargs)
    except FileNotFoundError:
        # Не е предупреждение: липсващ превод е НОРМАЛНО състояние за модул,
        # който не е превеждан. Шум на всяко зареждане на клиента не помага.
        _logger.debug("bootstrap_translations: няма каталог %s — прескачам", path)
        return None


if not getattr(webclient.file_path, _PATCH_FLAG, False):
    setattr(_file_path_or_none, _PATCH_FLAG, True)
    webclient.file_path = _file_path_or_none
    _logger.info(
        "bootstrap_translations: липсващият каталог вече се прескача, "
        "вместо да чупи зареждането на клиента")
