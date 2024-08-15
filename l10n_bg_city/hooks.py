# Part of Odoo. See LICENSE file for full copyright and licensing details.
import csv
import logging
import os
from collections import OrderedDict

from odoo import addons, _
from odoo.exceptions import UserError
from odoo.tools.translate import code_translations, TranslationImporter

_logger = logging.getLogger(__name__)


def post_init_hook(env):
    # country_id = env.ref("base.bg")
    module = __name__.split("addons.")[1].split(".")[0]
    module_path = ""
    for adp in addons.__path__:
        module_path = adp + os.sep + module
        if os.path.isdir(module_path):
            break
    module_path += os.sep + "data"
    files = {
        "res.country.state": (1, os.path.join(module_path, "res.country.state.csv")),
        "res.city.municipality": (2, os.path.join(module_path, "res.city.municipality.csv")),
        "res.city.cityhall": (3, os.path.join(module_path, "res.city.cityhall.csv")),
        "res.city": (4, os.path.join(module_path, "res.city.csv")),
    }
    files = OrderedDict(sorted(files.items(), key=lambda r: r[1][0]))

    langs = [code for code, _name in env['res.lang'].get_installed()]
    translation_importer = TranslationImporter(env.cr, verbose=False)

    for mname, file_name in files.items():
        if mname.startswith('res.city'):
            mname = 'res.city'
        inx, file_name = file_name
        with open(file=file_name) as csv_file:
            cn_codes = csv.DictReader(csv_file, delimiter=",")
            for row in cn_codes:
                values = {}
                create_xml_id = record_xml_id = False
                for fname_row, value in row.items():
                    if not value:
                        continue
                    fname_split = fname_row.split("@")
                    fname_check, lang_row = len(fname_split) > 1 and fname_split or fname_split + ['en_US']
                    fname_check = fname_check.split("/")

                    if len(fname_check) > 1:
                        fname, row_id = fname_check[0], fname_check[1]
                    else:
                        fname = fname_check[0]

                    field = env[mname]._fields.get(fname)

                    if not field:
                        continue

                    try:
                        integer_value = int(float(value))
                    except ValueError:
                        integer_value = 0

                    if fname == 'id' and integer_value == 0:
                        record_xml_id = value
                        xml_id = env.ref(value, raise_if_not_found=False)
                        if xml_id:
                            value = xml_id.id

                    if field.type == 'boolean':
                        value = value.lower() in ['true', '1', 'yes']
                    elif field.type == 'integer' and field.name != 'id':
                        value = integer_value
                    elif field.type == 'many2one' and integer_value == 0:
                        xml_id = env.ref(value, raise_if_not_found=False)
                        if xml_id:
                            value = xml_id.id
                        else:
                            raise UserError(_(f"The xml_id: {value} missing"))
                    if not (field.name == 'name' and lang_row == 'bg_BG'):
                        values[field.name] = value

                    if record_xml_id and field.translate and len(fname_row.split("@")) > 1:
                        for lang in filter(lambda r: r == lang_row, langs):
                            value_translated = code_translations. \
                                get_python_translations(module, lang).get(value)
                            if not value_translated:  # manage generic locale (i.e. `fr` instead of `fr_BE`)
                                value_translated = code_translations. \
                                    get_python_translations(module, lang.split('_')[0]).get(value)
                            if value_translated:
                                translation_importer. \
                                    model_translations[mname][field.name][record_xml_id][lang] = value_translated
                            else:
                                translation_importer. \
                                    model_translations[mname][field.name][record_xml_id][lang] = value

                if isinstance(values['id'], str):
                    create_xml_id = values['id']
                    del values['id']
                    record = env[mname].create(values)
                else:
                    record = env[mname].browse(values['id'])
                    del values['id']
                    record.write(values)
                if create_xml_id:
                    env['ir.model.data']._update_xmlids([{
                        'xml_id': create_xml_id,
                        'record': record,
                        'noupdate': True,
                    }])
    translation_importer.save(overwrite=False)
