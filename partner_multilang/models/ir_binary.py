# -*- coding: utf-8 -*-
import logging
from mimetypes import guess_extension

from odoo import models

from odoo.tools import replace_exceptions

from odoo.exceptions import UserError
from odoo.tools.mimetypes import guess_mimetype, get_extension

_logger = logging.getLogger(__name__)


class IrBinary(models.AbstractModel):
    _inherit = 'ir.binary'

    def _get_stream_from(
        self, record, field_name='raw', filename=None, filename_field='name',
        mimetype=None, default_mimetype='application/octet-stream',
    ):
        """
        Create a :class:odoo.http.Stream: from a record's binary field.

        :param record: the record where to load the data from.
        :param str field_name: the binary field where to load the data
            from.
        :param Optional[str] filename: when the stream is downloaded by
            a browser, what filename it should have on disk. By default
            it is ``{model}-{id}-{field}.{extension}``, the extension is
            determined thanks to mimetype.
        :param Optional[str] filename_field: like ``filename`` but use
            one of the record's char field as filename.
        :param Optional[str] mimetype: the data mimetype to use instead
            of the stored one (attachment) or the one determined by
            magic.
        :param str default_mimetype: the mimetype to use when the
            mimetype couldn't be determined. By default it is
            ``application/octet-stream``.
        :rtype: odoo.http.Stream
        """
        with replace_exceptions(ValueError, by=UserError(f'Expected singleton: {record}')):  # pylint: disable=missing-gettext
            record.ensure_one()

        try:
            field_def = record._fields[field_name]
        except KeyError:
            raise UserError(f"Record has no field {field_name!r}.")  # pylint: disable=missing-gettext
        if field_def.type != 'binary':
            raise UserError(  # pylint: disable=missing-gettext
                f"Field {field_def!r} is type {field_def.type!r} but "
                f"it is only possible to stream Binary or Image fields."
            )

        stream = self._record_to_stream(record, field_name)

        if stream.type in ('data', 'path'):
            if mimetype:
                stream.mimetype = mimetype
            elif not stream.mimetype:
                if stream.type == 'data':
                    head = stream.data[:1024]
                else:
                    with open(stream.path, 'rb') as file:
                        head = file.read(1024)
                stream.mimetype = guess_mimetype(head, default=default_mimetype)

            if filename:
                stream.download_name = filename
            elif filename_field in record:
                field_value = record[filename_field]
                # КРИТИЧНО: Handle dict from translate=True fields
                if isinstance(field_value, dict):
                    try:
                        lang = self.env.context.get('lang') or self.env.user.lang or 'en_US'
                        field_value = field_value.get(lang) or \
                                      field_value.get('en_US') or \
                                      next(iter(field_value.values()), None)
                    except Exception as e:
                        _logger.warning(f"Error extracting string from dict field '{filename_field}': {e}")
                        field_value = None

                # Set download_name only if we have a valid value
                if field_value:
                    stream.download_name = str(field_value)

            if not stream.download_name:
                stream.download_name = f'{record._table}-{record.id}-{field_name}'

            stream.download_name = stream.download_name.replace('\n', '_').replace('\r', '_')
            if (not get_extension(stream.download_name)
                and stream.mimetype != 'application/octet-stream'):
                stream.download_name += guess_extension(stream.mimetype) or ''

        return stream
