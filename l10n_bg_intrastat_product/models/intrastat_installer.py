# Copyright 2009-2019 dXFactory
# Copyright 2009-2019 Noviat.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import csv
import io
import os
from chardet.universaldetector import UniversalDetector

from odoo import api, fields, models, _
from odoo.modules.module import ad_paths

import logging
_logger = logging.getLogger(__name__)

CN_file_year = '2019'
CN_file_delimiter = ';'


class IntrastatInstaller(models.TransientModel):
    _name = 'intrastat.installer.bg'
    _inherit = 'res.config.installer'

    @api.model
    def _get_CN_file(self):
        return [(CN_file_year + '_en', CN_file_year + ' ' + _('English')),
                (CN_file_year + '_bg', CN_file_year + ' ' + _('Bulgarian / български език'))]

    @api.model
    def _default_CN_file(self):
        lang = self.env.user.lang[:2]
        if lang in ['bg', 'en']:
            return CN_file_year + '_' + lang
        else:
            return CN_file_year + '_en'

    CN_file = fields.Selection(
        '_get_CN_file', string='Intrastat Code File',
        required=True, default=_default_CN_file)

    @api.model
    def _load_code(self, row):
        code_obj = self.env['hs.code']
        vals = {'description': row['description']}
        cn_unit_id = row['unit_id']
        if cn_unit_id:
            cn_unit_ref = 'intrastat_product.' + cn_unit_id
            cn_unit = self.env.ref(cn_unit_ref)
            vals['intrastat_unit_id'] = cn_unit.id
        cn_code = row['code']
        cn_code_i = self.cn_lookup.get(cn_code)
        if isinstance(cn_code_i, int):
            self.cn_codes[cn_code_i].write(vals)
        else:
            vals['local_code'] = cn_code
            code_obj.create(vals)

    @api.multi
    def execute(self):
        detector = UniversalDetector()
        res = super().execute()
        company = self.env.user.company_id
        if company.country_id.code not in ('BG', 'bg'):
            return res

        # set company defaults
        module = __name__.split('addons.')[1].split('.')[0]
        transaction = self.env.ref(
            '%s.intrastat_transaction_1' % 'intrastat_product')
        if not company.intrastat_transaction_out_invoice:
            company.intrastat_transaction_out_invoice = transaction
        if not company.intrastat_transaction_out_refund:
            company.intrastat_transaction_out_refund = transaction
        if not company.intrastat_transaction_in_invoice:
            company.intrastat_transaction_in_invoice = transaction
        if not company.intrastat_transaction_in_refund:
            company.intrastat_transaction_in_refund = transaction

        # Load transaction codes and description

        # load intrastat_codes
        self.cn_codes = self.env['hs.code'].search([])
        self.cn_lookup = {}
        for i, c in enumerate(self.cn_codes):
            self.cn_lookup[c.local_code] = i
        for adp in ad_paths:
            module_path = adp + os.sep + module
            if os.path.isdir(module_path):
                break
        CN_fn = '%s_intrastat_codes.csv' % self.CN_file
        CN_fqn = os.path.join(module_path, 'data', CN_fn)
        for line in open(CN_fqn, 'rb'):
            detector.feed(line)
        CN_codepage = detector.close()['encoding']
        _logger.info("Load file %s:%s" % (CN_fqn, CN_codepage))
        if not CN_codepage or self.env.user.lang[:2] == 'en':
            CN_codepage = 'utf-8'
        with io.open(CN_fqn, mode='r', encoding=CN_codepage) as CN_file:
            cn_codes = csv.DictReader(CN_file, delimiter=CN_file_delimiter)
            for row in cn_codes:
                #_logger.info("Load code: %s" % row)
                self._load_code(row)
        return res
