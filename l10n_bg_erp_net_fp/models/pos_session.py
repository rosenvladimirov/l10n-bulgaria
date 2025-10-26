# l10n_bg_erp_net_fp/models/pos_session.py
from odoo import models


class PosSession(models.Model):
    _inherit = "pos.session"

    def _load_pos_data_fields(self, config):
        fields_map = super()._load_pos_data_fields(config)

        # Зареждане на необходимите полета за фискален принтер
        fields_map.setdefault("pos.printer", set()).update({
            "name",
            "id",
            "printer_type",
            "l10n_bg_printer_id",  # ID на принтера
            "l10n_bg_proxy_ip",  # IP адрес на ErpNet.FP сървъра
        })

        # Зареждане на данъчни групи
        fields_map.setdefault("account.tax", set()).update({
            "tax_group_id",
            "amount",
            "name"
        })

        fields_map.setdefault("account.tax.group", set()).update({
            "id",
            "name",
            "l10n_bg_fiscal_tax_group",  # Българска данъчна група (А, Б, В, Г)
        })

        return fields_map
