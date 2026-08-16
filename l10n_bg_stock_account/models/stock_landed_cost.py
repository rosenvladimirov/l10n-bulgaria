from odoo import fields, models


class StockLandedCost(models.Model):
    _inherit = 'stock.landed.cost'

    # Отделен BG запис за auto_post продукти — core-ът създава
    # account_move_id само за real_time редовете; тук допълваме
    # periodic + l10n_bg_stock_auto_post редовете със собствен запис.
    l10n_bg_account_move_id = fields.Many2one(
        'account.move',
        string='BG Journal Entry',
        copy=False,
        readonly=True,
        help='Journal entry created for products with BG auto-post '
             'stock accounting (periodic valuation). Standard Odoo '
             'skips journal entries for non real-time products; this '
             'entry capitalizes the landed cost into the stock '
             'valuation account for such products.',
    )

    def button_validate(self):
        """Допълва core валидацията на Landed Cost за BG auto_post.

        Core-ът (stock_landed_costs) прескача счетоводния запис за
        продукти с ``valuation != 'real_time'`` (hard-coded ``continue``
        в ``button_validate``), но стойността на move-а СЕ актуализира
        (``_set_value()``). За BG auto_post категории (periodic) това
        оставя GL 302/303 разминат със складовата оценка и разходът се
        брои двойно — веднъж по фактурата за услугата и втори път в
        по-високата отчетна стойност при изписване.

        Тук, СЛЕД core записа, генерираме допълнителен запис за
        auto_post продуктите по същата core логика
        (``_create_accounting_entries``), пропорционално на останалото
        на склад количество:

            Dr. Stock Valuation (302/303)
            Cr. сметката от cost line-а (напр. 301 GRNI)

        Чист periodic (без BG чекчето) остава стандартно — без запис.
        Идемпотентно през ``l10n_bg_account_move_id``.
        """
        res = super().button_validate()
        for cost in self:
            cost = cost.with_company(cost.company_id)
            if cost.l10n_bg_account_move_id:
                continue
            line_ids = []
            for line in cost.valuation_adjustment_lines.filtered(
                lambda adj: adj.move_id
            ):
                product = line.move_id.product_id
                # real_time е обработен от core; periodic без BG
                # чекчето запазва стандартното поведение (без запис).
                if product.valuation == 'real_time':
                    continue
                if not product.categ_id.sudo().l10n_bg_stock_auto_post:
                    continue
                entries = line._create_accounting_entries(
                    line.move_id.remaining_qty
                )
                if entries:
                    line_ids += entries
            if not line_ids:
                continue
            move = self.env['account.move'].create({
                'journal_id': cost.account_journal_id.id,
                'date': cost.date,
                'ref': cost.name,
                'move_type': 'entry',
                'line_ids': line_ids,
            })
            move._post()
            cost.l10n_bg_account_move_id = move.id
        return res
