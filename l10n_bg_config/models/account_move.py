#  Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, _, fields


def get_doc_type():
    return [
        ('01', _('Invoice')),
        ('02', _('Debit note')),
        ('03', _('Credit note')),
        ('04', _('Storeable goods sent to EU')),
        # Register of goods under the regime of storage of goods on demand,
        # sent or transported from the territory of the country to the territory of another member state
        ('05', _('Storeable goods receive from EU')),
        ('07', _('Customs declarations')),
        # Customs declaration/customs document certifying completion of customs formalities
        ('09', _('Protocols or other')),
        ('11', _('Invoice - cash reporting')),
        ('12', _('Debit notice - cash reporting')),
        ('13', _('Credit notice - cash statement')),
        ('50', _('Protocols fuel supplies')),
        ('81', _('Sales report - tickets')),
        ('82', _('Special tax order')),  # Report on the sales made under a special tax order
        ('83', _('sales of bread')),  # Report on the sales of bread
        ('84', _('Sales of flour')),  # Report on the sales of flour
        ('23', _('Credit note art. 126b')),  # Credit notification under Art. 126b, para. 1 of VAT
        ('29', _('Protocol under Art. 126b')),  # Protocol under Art. 126b, para. 2 and 7 of VAT
        ('91', _('Protocol under Art. 151c')),  # Protocol for the required tax under Art. 151c, para. 3 of the law
        ('92', _('Protocol under Art. 151g')),
        # Protocol on the tax credit under Art. 151g,
        # para. 8 of the law or a report under Art. 104g, para. 14
        ('93', _('Protocol under Art. 151c')),
        # Protocol for the required tax under Art. 151c,
        # para. 7 of the law with a delivery recipient who does not apply the special regime
        ('94', _('Protocol under Art. 151c, para. 7')),
        # Protocol for the required tax under Art. 151c,
        # para. 7 of the law with a delivery recipient, a person who applies the special regime
        ('95', _('Protocol for free provision of foodstuffs')),
        # Protocol for free provision of foodstuffs, to which Art. 6, para. 4, item 4 VAT
    ]


def get_type_vat():
    return [
        ('standard', _('Accounting document')),
        ('117_protocol', _('Art. 117 - Protocols')),
        ('in_customs', _('Import Customs declaration')),
        ('out_customs', _('Export Customs declaration')),
        ('dropship', _('Dropship/Try party deal'))
    ]


def get_delivery_type():
    return [
        ('01', _('Delivery under Part I of Annex 2 of VAT')),
        ('02', _('Delivery under Part II of Annex 2 of VAT')),
        ('03', _('Import under Annex 3 of VAT')),
        ('07', _('Supply, import or IC acquisition of bread')),
        ('08', _('Supply, import or IC acquisition of flour')),
        ('51',
         _('Arrival of goods on the territory of the country under the regime of storage of goods until demand under Art. 15a of VAT')),
        ('53',
         _('Replacement of the person for whom the goods were intended without termination of the contract under Art. 15a, para. 4 of VAT')),
        ('54', _('Marriage/absence/destruction of goods under Art. 15a, para. 10 of VAT')),
        (
        '58', _('Termination of the contract under the mode of storage of goods until requested under Art. 15a of VAT'))
    ]


class AccountMove(models.Model):
    _inherit = 'account.move'

    l10n_bg_name = fields.Char('Number of locale document', index='trigram', tracking=True, copy=False)
    l10n_bg_narration = fields.Char('Narration for audit report', translate=True, copy=False)
    l10n_bg_type_vat = fields.Selection(selection=get_type_vat(),
                                        string="Type of numbering",
                                        default='standard',
                                        copy=False,
                                        index=True,
                                        )
    l10n_bg_doc_type = fields.Selection(selection=get_doc_type(),
                                        string="Vat type document",
                                        default='01',
                                        copy=False)
    l10n_bg_delivery_type = fields.Selection(selection=get_delivery_type(),
                                             string="Vat type delivery",
                                             copy=False)
