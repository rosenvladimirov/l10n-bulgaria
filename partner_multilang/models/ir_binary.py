# -*- coding: utf-8 -*-
import logging
from mimetypes import guess_extension

from odoo import models
from odoo.tools.mimetypes import get_extension

_logger = logging.getLogger(__name__)


class IrBinary(models.AbstractModel):
    _inherit = 'ir.binary'

    def _get_stream_from(
        self, record, field_name='raw', filename=None, filename_field='name',
        mimetype=None, default_mimetype='application/octet-stream',
    ):
        """Delegate to core (keeps all robustness: missing-file / placeholder
        fallback handled by ir.binary._get_image_stream_from and the
        controllers). Only fix the download name when ``filename_field`` is a
        translate=True field returning a {lang: value} dict — the sole purpose
        of this module's override. Previously the whole method was
        reimplemented, which broke core's graceful handling and turned missing
        / legacy attachments into hard HTTP 500s.
        """
        stream = super()._get_stream_from(
            record, field_name=field_name, filename=filename,
            filename_field=filename_field, mimetype=mimetype,
            default_mimetype=default_mimetype,
        )
        if filename or not filename_field:
            return stream
        try:
            if filename_field not in record._fields:
                return stream
            field_value = record[filename_field]
            if isinstance(field_value, dict):
                lang = self.env.context.get('lang') or self.env.user.lang or 'en_US'
                field_value = (field_value.get(lang)
                               or field_value.get('en_US')
                               or next(iter(field_value.values()), None))
                if field_value:
                    name = str(field_value).replace('\n', '_').replace('\r', '_')
                    if (not get_extension(name) and stream.mimetype
                            and stream.mimetype != 'application/octet-stream'):
                        name += guess_extension(stream.mimetype) or ''
                    stream.download_name = name
        except Exception as exc:  # never break streaming over a filename tweak
            _logger.warning(
                "partner_multilang: download_name tweak skipped for "
                "%s.%s: %s", record._name, filename_field, exc)
        return stream
