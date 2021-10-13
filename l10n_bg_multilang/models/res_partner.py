# coding: utf-8

from odoo import api, fields, models, tools, _
from odoo.addons.base.res.res_partner import Partner as ResPartner
from odoo.osv.expression import get_unaccent_wrapper

import logging
_logger = logging.getLogger(__name__)

DIFFEREND_LETTERS = [
                    'display_name_bg',
                    'display_name_ru',
                    'display_name_el'
                    ]

class Partner(models.Model):
    _inherit = ['res.partner']
    _name = 'res.partner'
    _order = "display_name_en,display_name_bg,display_name_el"

    name = fields.Char(translate=True)
    company_name = fields.Char(translate=True)
    commercial_company_name = fields.Char(translate=True)

    street = fields.Char(translate=True)
    street2 = fields.Char(translate=True)
    street_name = fields.Char(translate=True)
    street_number = fields.Char(translate=True)
    street_number2 = fields.Char(translate=True)
    city = fields.Char(translate=True)
    function = fields.Char(translate=True)
    name_with_title = fields.Char("Partner name with title", compute="_compute_name_with_title")

    display_name = fields.Char(compute='_compute_display_name', search='_name_search_ext', store=False, index=False)
    display_name_en = fields.Char("SRC Name", index=True, readonly=True, copy=False)
    display_name_bg = fields.Char("BG Name", index=True, readonly=True, copy=False)
    display_name_el = fields.Char("GR Name", index=True, readonly=True, copy=False)
    display_lang = fields.Char(compute='_compute_display_lang')

    @api.multi
    def _compute_name_with_title(self):
        country = self.env.user.partner_id.country_id
        for partner in self:
            if country.title_format:
                format = country.get_title_fields()
                academic_title_display = partner.academic_title_display
                if 'contact_id' in partner._fields:
                    academic_title_display = partner.contact_id and partner.contact_id.academic_title_display or academic_title_display
                arg_new = {}
                arg = {
                    'shortcut': partner.title and partner.title.shortcut or '',
                    'title': partner.title and partner.title.name or '',
                    'partner': partner.name,
                    'academic_title_display': academic_title_display,
                }
                for k, v in arg.items():
                    if k in format:
                        arg_new[k] = v
                if arg_new:
                    partner.name_with_title = country.title_format % arg_new
                else:
                    partner.name_with_title = partner.name
            else:
                partner.name_with_title = partner.name

    @api.multi
    def write(self, vals):
        result = super(Partner, self).write(vals)
        if 'name' in vals:
            self._compute_display_name_save(force_name=vals['name'])
        return result

    @api.model
    def create(self, vals):
        res = super(Partner, self).create(vals)
        res._compute_display_name_save(force_name=vals['name'])
        return res

    @api.depends('company_name', 'parent_id.is_company', 'commercial_partner_id.name')
    @api.onchange('name')
    def _onchange_name(self):
        for partner in self:
            partner._compute_commercial_company_name()

    def _name_search_ext(self, operator, value):
        display_name = 'display_name_en'
        lang = self.env.user.sudo().lang
        lang_name = 'display_name_%s' % lang.split("_")[0]
        if lang_name in DIFFEREND_LETTERS and lang_name in self._fields and len(value.encode('ascii', 'ignore')) != len(value):
            display_name = lang_name
        if operator in ('ilike') and len(value.split()) > 1:
            operator = '%'
        return [(display_name, operator, value)]

    def _compute_display_lang(self):
        lang = self.env.user.sudo().lang
        display_lang = 'display_name_en'
        lang_name = 'display_name_%s' % lang.split("_")[0]
        if lang_name in DIFFEREND_LETTERS and lang_name in self._fields:
            display_lang = lang_name
        for partner in self:
            partner.display_lang = display_lang

    def _compute_display_name_ext(self, display=False, force_name=False):
        lang_name = self.display_lang
        lang = self.env.user.sudo().lang.split("_")[0]
        if display:
            diff_ext = dict(self._context, show_address=None, show_address_only=None, show_email=None)
            # if self._context.get('attached'):
            #     display_lang_name = self.with_context(**diff_ext).contact_id_name
            # else:
            names_ext = dict(self.with_context(**diff_ext).name_get())
            display_lang_name = names_ext.get(self.id)
            return self.display_name_en, display_lang_name, lang_name, (lang_name in DIFFEREND_LETTERS and lang_name in self._fields)
        diff_en = dict(lang='en', show_address=None, show_address_only=None, show_email=None)
        names_en = dict(self.with_context(**diff_en).name_get())
        name = names_en.get(self.id)
        name_lang = name
        lang_name_ret = {'display_name_en': name_lang}
        is_lang = False
        if lang_name in DIFFEREND_LETTERS and lang_name in self._fields:
            if force_name:
                diff_ext = dict(force_name=force_name, show_address=None, show_address_only=None, show_email=None)
            else:
                diff_ext = dict(show_address=None, show_address_only=None, show_email=None)
            for lang_curr in DIFFEREND_LETTERS:
                if lang_curr in self._fields and lang_curr != lang_name:
                    lang_adds = lang_curr[-2:]
                    diff_curr = dict(lang=lang_adds, show_address=None, show_address_only=None, show_email=None)
                    names_ext = dict(self.with_context(**diff_curr).name_get())
                    lang_name_ret[lang_curr] = names_ext.get(self.id)
            names_ext = dict(self.with_context(**diff_ext).name_get())
            name_lang = names_ext.get(self.id)
            lang_name_ret[lang_name] = name_lang
            is_lang = True
        elif lang_name not in DIFFEREND_LETTERS and lang != 'en':
            diff_ext = dict(show_address=None, show_address_only=None, show_email=None)
            for lang_curr in DIFFEREND_LETTERS:
                if lang_curr in self._fields:
                    lang_adds = lang_curr[-2:]
                    diff_curr = dict(lang=lang_adds, show_address=None, show_address_only=None, show_email=None)
                    names_ext = dict(self.with_context(**diff_curr).name_get())
                    lang_name_ret[lang_curr] = names_ext.get(self.id)
            names_ext = dict(self.with_context(**diff_ext).name_get())
            name_lang = names_ext.get(self.id)
            lang_name_ret[lang_name] = name_lang
            is_lang = True
        return name, name_lang, lang_name_ret, is_lang

    @api.multi
    @api.depends('is_company', 'name', 'parent_id.name', 'type', 'company_name')
    def _compute_display_name_save(self, force_name=False):
        for partner in self:
            display_name_en, display_name_ext, field_name, is_lang = partner._compute_display_name_ext(force_name=force_name)
            if is_lang:
                partner.write(field_name)
            else:
                partner.write({'display_name_en':display_name_en})
            #_logger.info("NAME SAVE %s:%s:%s:%s" % (display_name_en, display_name_ext, field_name, is_lang))

    @api.multi
    @api.depends('is_company', 'name', 'parent_id.name', 'type', 'company_name')
    def _compute_display_name(self):
        for partner in self:
            name_en, partner.display_name, lang_name, is_lang = partner._compute_display_name_ext(display=True)
            country = self.env.user.partner_id.country_id
            if country.title_format:
                format = country.get_title_fields()
                arg_new = {}
                arg = {
                    'shortcut': partner.title and partner.title.shortcut or '',
                    'title': partner.title and partner.title.name or '',
                    'partner': partner.display_name,
                    'academic_title_display': partner.academic_title_display,
                }
                for k, v in arg.items():
                    if k in format:
                        arg_new[k] = v
                if arg_new:
                    partner.display_name = country.title_format % arg_new
            #_logger.info("NAME %s:%s:%s:%s" % (name_en, partner.display_name, lang_name, is_lang))

    @api.model
    def __name_search(self, name, display_name):
        multi_display_name = "display_name_en {operator} {percent}"
        lang = self.env.user.sudo().lang
        lang_name = 'display_name_%s' % lang.split("_")[0]
        count_lang = 0
        if lang_name in self._fields and len(name.encode('ascii', 'ignore')) != len(name):
            multi_display_name = "display_name_en {operator} {percent} OR %s {operator} {percent}" % lang_name
            display_name = lang_name
            count_lang = 1
        return multi_display_name, display_name, count_lang

    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=100):
        if args is None:
            args = []
        if name and operator in ('=', 'ilike', '=ilike', 'like', '=like'):
            self.check_access_rights('read')
            where_query = self._where_calc(args)
            self._apply_ir_rules(where_query, 'read')
            from_clause, where_clause, where_clause_params = where_query.get_sql()
            where_str = where_clause and (" WHERE %s AND " % where_clause) or ' WHERE '

            # search on the name of the contacts and of its company
            search_name = name
            if operator in ('ilike', 'like'):
                search_name = '%%%s%%' % name
            if operator in ('=ilike', '=like'):
                operator = operator[1:]

            unaccent = get_unaccent_wrapper(self.env.cr)
            display_name = 'display_name_en'
            multi_display_name, display_name, count_search_name = self.__name_search(name, display_name)
            #_logger.info("Searh __%s:%s:%s:%s" % (display_name, lang_name, lang, name.encode('ascii', 'ignore')))
            query = """SELECT id
                         FROM res_partner
                      {where} ({email} {operator} {percent}
                           OR {multi_display_name}
                           OR {reference} {operator} {percent}
                           OR {vat} {operator} {percent})
                           -- don't panic, trust postgres bitmap
                     ORDER BY {display_name} {operator} {percent} desc,
                              {display_name}
                    """.format(where=where_str,
                               operator=operator,
                               email=unaccent('email'),
                               multi_display_name=unaccent(multi_display_name.format(operator=operator, percent=unaccent('%s'))),
                               reference=unaccent('ref'),
                               percent=unaccent('%s'),
                               vat=unaccent('vat'),
                               display_name=unaccent(display_name),)
            where_clause_params += [search_name]*(5+count_search_name)
            #_logger.info("Select __________ %s:%s" % (query, where_clause_params))
            if limit:
                query += ' limit %s'
                where_clause_params.append(limit)
            self.env.cr.execute(query, where_clause_params)
            partner_ids = [row[0] for row in self.env.cr.fetchall()]

            if partner_ids:
                return self.browse(partner_ids).name_get()
            else:
                return []
        return super(ResPartner, self).name_search(name, args, operator=operator, limit=limit)


#    @api.multi
#    def name_get(self):
#
#        def name_get_lang(self, partner):
#            lang_name = partner.display_lang
#            lang = self.env.user.sudo().lang.split("_")[0]
#            if lang_name not in DIFFEREND_LETTERS and lang != 'en':
#                display_lang_name = partner.name
#            else:
#                display_lang_name = getattr(partner, lang_name)
#            return partner.display_name_en, display_lang_name, lang_name, (lang_name in DIFFEREND_LETTERS and lang_name in self._fields)
#
#        res = []
#        for partner in self:
#            name_en, name, lang_name, is_lang = name_get_lang(self, partner)
#            if partner.company_name or partner.parent_id:
#                if not name and partner.type in ['invoice', 'delivery', 'other']:
#                    name = dict(self.fields_get(['type'])['type']['selection'])[partner.type]
#                if not partner.is_company:
#                    name = "%s, %s" % (partner.commercial_company_name or partner.parent_id.name, is_lang and name or name_en)
#            else:
#                name = is_lang and name or name_en
#            if self._context.get('show_address_only'):
#                name = partner._display_address(without_company=True)
#            if self._context.get('show_address'):
#                name = name + "\n" + partner._display_address(without_company=True)
#            name = name.replace('\n\n', '\n')
#            name = name.replace('\n\n', '\n')
#            if self._context.get('show_email') and partner.email:
#                name = "%s <%s>" % (name, partner.email)
#            if self._context.get('html_format'):
#                name = name.replace('\n', '<br/>')
#            res.append((partner.id, name))
#        return res
