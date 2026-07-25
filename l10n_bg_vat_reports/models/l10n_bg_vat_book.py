# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import tempfile
import zipfile

from odoo import _, api, models
from odoo.tools.float_utils import float_is_zero
from odoo.tools.misc import formatLang

from odoo.addons.l10n_bg_vat_reports.report import l10n_bg_file_helper

_logger = logging.getLogger(__name__)


class BulgarianTaxReportDeclartionCustomHandler(models.AbstractModel):
    _name = "bg.account.report.vat.declaration.custom.handler"
    _inherit = "account.generic.tax.report.handler"
    _description = "Bulgarian Tax Report Custom Handler (VAT Report-declaration)"

    def _custom_options_initializer(self, report, options, previous_options=None):
        super()._custom_options_initializer(
            report, options, previous_options=previous_options
        )
        for column in options["columns"]:
            column["style"] = column["style"].replace(
                "white-space: nowrap;", "word-wrap: break-word;"
            )
        # self._init_core_custom_options(report, options, previous_options)
        # _logger.info(f"OPTIONS: {options}")
        # _logger.info(f"PREVISION OPTIONS: {previous_options}")
        # Add export button
        options["buttons"].append(
            {
                "name": _("VAT Book (ZIP)"),
                "sequence": 30,
                "action": "export_file",
                "action_param": "l10n_bg_export_csvs_zip",
                "file_export_type": _("ZIP"),
            }
        )

    def _caret_options_initializer(self):
        return {
            "account_move": [
                {
                    "name": _("Open Journal Entry"),
                    "action": "caret_option_open_record_form",
                },
            ],
        }

    @api.model
    def get_csvs(self, report, options, tax_report):
        options["get_file_data"] = True
        lines = []
        fields_to_export = l10n_bg_file_helper.L10N_BG_DECLARATION_FIELDS
        if tax_report == "declaration":
            fields_to_export = l10n_bg_file_helper.L10N_BG_DECLARATION_FIELDS
        elif tax_report == "purchases":
            fields_to_export = l10n_bg_file_helper.L10N_BG_PURCHASES_FIELDS
        elif tax_report == "sales":
            fields_to_export = l10n_bg_file_helper.L10N_BG_SALES_FIELDS
        elif tax_report == "vies":
            fields_to_export = l10n_bg_file_helper.L10N_BG_VIES_FIELDS
        elif tax_report == "vies_lines":
            fields_to_export = l10n_bg_file_helper.L10N_BG_VIES_LINES_FIELDS

        for line in self._get_results(report, options, tax_report):
            new_line = {}
            for field, helper in fields_to_export.items():
                new_line[field] = helper(line[field])
            lines.append(new_line)

        line_csv = []
        for val in lines:
            content = ""
            for field in fields_to_export.keys():
                content += val[field]
            line_csv.append(content)
            # _logger.info(f"val: {val} content: {content}")

        if line_csv:
            return ["\r\n".join(line_csv) + "\r\n"]
        else:
            return [""]

    def l10n_bg_export_csvs_zip(self, options):
        l10n_bg_vat_declaration_report = self.env["account.report"].browse(
            options["report_id"]
        )
        l10n_bg_vat_declaration_csvs = self.get_csvs(
            l10n_bg_vat_declaration_report, options, "declaration"
        )

        l10n_bg_vat_purchase_report = self.env["account.report"].browse(
            self.env.ref("l10n_bg_vat_reports.l10n_bg_nra_tax_report_purchases").ids
        )
        l10n_bg_vat_purchase_csvs = self.get_csvs(
            l10n_bg_vat_purchase_report, options, "purchases"
        )
        # _logger.info(f"l10n_bg_vat_purchase_csvs {l10n_bg_vat_purchase_csvs}")

        l10n_bg_vat_sales_report = self.env["account.report"].browse(
            self.env.ref("l10n_bg_vat_reports.l10n_bg_nra_tax_report_sales").ids
        )
        l10n_bg_vat_sales_csvs = self.get_csvs(
            l10n_bg_vat_sales_report, options, "sales"
        )
        # _logger.info(f"l10n_bg_vat_sales_csvs {l10n_bg_vat_sales_csvs}")

        l10n_bg_tax_vies_report = self.env["account.report"].browse(
            self.env.ref("l10n_bg_vat_reports.l10n_bg_nra_tax_report_vies").ids
        )
        l10n_bg_vat_vies_csvs = self.get_csvs(l10n_bg_tax_vies_report, options, "vies")
        # _logger.info(f"l10n_bg_vat_vies_csvs {l10n_bg_vat_vies_csvs}")

        l10n_bg_vat_vies_lines_csvs = self.get_csvs(
            l10n_bg_tax_vies_report, options, "vies_lines"
        )
        if len(l10n_bg_vat_vies_csvs) > 0 and len(l10n_bg_vat_vies_lines_csvs) > 0:
            l10n_bg_vat_vies_csvs = [
                l10n_bg_vat_vies_csvs[0] + l10n_bg_vat_vies_lines_csvs[0]
            ]
            # _logger.info(f"l10n_bg_vat_vies_csvs {l10n_bg_vat_vies_csvs}")

        with tempfile.NamedTemporaryFile() as buf:
            with zipfile.ZipFile(
                buf, mode="w", compression=zipfile.ZIP_DEFLATED, allowZip64=False
            ) as zip_buffer:
                for i, csv in enumerate(l10n_bg_vat_declaration_csvs):
                    zip_buffer.writestr(
                        "Deklar.txt", csv.encode("cp1251", errors="ignore")
                    )
                for i, csv in enumerate(l10n_bg_vat_purchase_csvs):
                    zip_buffer.writestr(
                        "Pokupki.txt", csv.encode("cp1251", errors="ignore")
                    )
                for i, csv in enumerate(l10n_bg_vat_sales_csvs):
                    zip_buffer.writestr(
                        "Prodagbi.txt", csv.encode("cp1251", errors="ignore")
                    )
                for i, csv in enumerate(l10n_bg_vat_vies_csvs):
                    zip_buffer.writestr(
                        "Vies.txt", csv.encode("cp1251", errors="ignore")
                    )
            buf.seek(0)
            res = buf.read()

        return {
            "file_name": l10n_bg_vat_declaration_report.get_default_report_filename(
                "ZIP"
            ),
            "file_content": res,
            "file_type": "zip",
        }

    def _get_results(self, report, options, tax_report):
        full_query = self._build_query(options, tax_report)
        # Execute the queries and fetch results
        self._cr.execute(full_query, [])
        results = self._cr.dictfetchall()
        # if tax_report == 'vies':
        #     lines_results = self._get_results(report, options, 'vies_lines')
        #     for line_lines in lines_results:
        #         for line in results:
        #             line.update(line_lines)
        return results

    def _dynamic_lines_generator(
        self, report, options, all_column_groups_expression_totals
    ):
        # _logger.info(f"GET DINAMIC LINES {all_column_groups_expression_totals}")
        return self._get_dynamic_lines(report, options, "declaration")

    def _get_dynamic_lines(self, report, options, tax_report):
        lines = []
        bulgaria_id = self.env.ref("base.bg")
        country_id = self.env.company.country_id or bulgaria_id
        if country_id != bulgaria_id:
            country_id = bulgaria_id
        unique_key_tags = set()
        tags = self.env["account.account.tag"]
        for tag in self.env["account.account.tag"].search(
            [("country_id", "=", country_id.id), ("applicability", "=", "taxes")]
        ):
            if tag.description and tag.l10n_bg_code not in unique_key_tags:
                unique_key_tags.add(tag.l10n_bg_code)
                tags |= tag

        # Build queries for each column group and initialize total values dictionary
        full_query = self._build_query(options, tax_report)
        # Execute the queries and fetch results
        self._cr.execute(full_query, [])
        results = self._cr.dictfetchall()
        # _logger.info(f"{results}")
        # Generate report lines
        # Declaration construction
        if tax_report == "declaration":
            lines = self._get_report_declaration(report, options, results, tags=tags)
        elif tax_report == "purchases":
            lines = self._get_report_sales_purchases(
                report, options, results, tax_report=tax_report, tags=tags
            )
        elif tax_report == "sales":
            lines = self._get_report_sales_purchases(
                report, options, results, tax_report=tax_report, tags=tags
            )
        elif tax_report == "vies":
            # _logger.info(f"{full_query}")
            full_query = self._build_query(options, "vies_lines")
            # _logger.info(f"{full_query}")
            # Execute the queries and fetch results
            self._cr.execute(full_query, [])
            lines_results = self._cr.dictfetchall()
            lines = self._get_report_vies(
                report, results, lines_results, options, tags=tags
            )
            # _logger.info(f"{lines}")
        return lines

    def _build_query(self, options, tax_report):
        """
        Build a query to retrieve data for a VAT report.

        Parameters:
        - report: The VAT report object.
        - options: Options for the query.
        - column_group_key: The key for grouping columns.

        Returns:
        A query for retrieving data.
        """
        full_query = ""
        if tax_report == "sales":
            full_query = (
                self.env["account.bg.info.sale.line"]
                .with_context(**dict(self._context, report_options=options))
                ._table_query
            )
        elif tax_report == "purchases":
            full_query = (
                self.env["account.bg.info.purchases.line"]
                .with_context(**dict(self._context, report_options=options))
                ._table_query
            )
        elif tax_report == "declaration":
            full_query = (
                self.env["account.bg.vat.info.declar"]
                .with_context(**dict(self._context, report_options=options))
                ._table_query
            )
        elif tax_report == "vies":
            full_query = (
                self.env["account.bg.vies.info.declar"]
                .with_context(**dict(self._context, report_options=options))
                ._table_query
            )
        elif tax_report == "vies_lines":
            full_query = (
                self.env["account.bg.calc.vies.line"]
                .with_context(**dict(self._context, report_options=options))
                ._table_query
            )
        # _logger.info(f"SQL QUERY: {full_query}")
        return full_query

    def _get_report_declaration(self, report, options, results, tags=False):
        lines = []
        for result in results:
            report_line = self._get_report_line_declaration(
                report, options, result, tags=tags
            )
            lines.append((0, report_line))
        return lines

    def _get_report_line_declaration(self, report, options, result, tags=False):
        column_values = {}
        company_id = result["company_id"]
        for key, value in result.items():
            if key == "company_id":
                continue
            # _logger.info(f"{key}: {value}")
            if key.startswith("account_tag_"):
                name = "" if value is None else formatLang(self.env, value, digits=2)
                column_values.update(
                    {
                        key: {
                            "name": name,
                            "no_format": value,
                            "class": "font-monospace number",
                        }
                    }
                )
            else:
                column_values.update(
                    {
                        key: {
                            "name": value,
                            "no_format": value,
                            "class": "font-monospace text-left",
                        }
                    }
                )
        return {
            "id": report._get_generic_line_id("res.company", company_id),
            "name": "",
            "columns": [],
            "l10n_bg_vat_declaration": column_values,
            "class": "o_account_reports_ja_subtable",
        }

    def _get_report_sales_purchases(
        self, report, options, results, tax_report=False, tags=False
    ):
        lines = []
        if not results:
            return lines
        total_values_dict = {}
        move_info_dict = {}
        number_keys = [
            line for line in results[0].keys() if line.startswith("account_tag_")
        ]
        for (
            column_group_key,
            column_group_options,
        ) in report._split_options_per_column_group(options).items():
            total_values_dict.setdefault(
                column_group_key, dict.fromkeys(number_keys, 0.0)
            )
            # move_info_dict.setdefault(column_group_key, {})
            for result in results:
                # _logger.info(f"result {result}")
                move_id = result["move_id"]
                move_info_dict.setdefault(move_id, {})
                move_info_dict[move_id][column_group_key] = result
                for key in number_keys:
                    total_values_dict[column_group_key][key] += result.get(key) or 0.0

        # _logger.info(f"{move_info_dict}")
        for move_id, move_info in move_info_dict.items():
            # _logger.info(f"move_info {move_info}")
            if not move_info:
                continue
            line = self._create_report_line(
                report, options, move_info, move_id, number_keys, tax_report
            )
            line["caret_options"] = "account_move"
            lines.append((0, line))

        total_line = self._create_report_total_line(
            report, options, total_values_dict, tax_report
        )
        lines.append((0, total_line))
        return lines

    def _create_report_line(
        self, report, options, move_vals, move_id, number_values, tax_report
    ):
        """Create a standard (non total) line for the report
        :param options: report options
        :param move_vals: values necessary for the line
        :param move_id: id of the account.move (or account.bg.vat.purchases.line, account.bg.vat.sales.line)
        :param number_values: list of expression_label that require the 'number' class
        """

        line_name = ""
        columns = []
        for column in options["columns"]:
            expression_label = column["expression_label"]
            value = move_vals.get(column["column_group_key"], {}).get(expression_label)
            if tax_report == "purchases" and expression_label == "info_tag_6":
                line_name = value
            elif tax_report == "sales" and expression_label == "info_tag_5":
                line_name = value
            columns.append(
                {
                    "name": report.format_value(
                        value, figure_type=column["figure_type"]
                    )
                    if value is not None
                    else None,
                    "no_format": value,
                    "class": "number" if expression_label in number_values else "text-left",
                }
            )
        return {
            "id": report._get_generic_line_id("account.move", move_id),
            "caret_options": "account.move",
            "name": line_name,
            "columns": columns,
            "level": 1,
        }

    def _create_report_total_line(self, report, options, total_vals, tax_report):
        """Create a total line for the report
        :param options: report options
        :param total_vals: values necessary for the line
        """
        columns = []
        for column in options["columns"]:
            expression_label = column["expression_label"]
            value = total_vals.get(column["column_group_key"], {}).get(expression_label)
            columns.append(
                {
                    "name": report.format_value(
                        value, figure_type=column["figure_type"]
                    )
                    if value is not None
                    else None,
                    "no_format": value,
                    "class": "number",
                }
            )
        return {
            "id": report._get_generic_line_id(None, None, markup="total"),
            "name": _("TOTAL"),
            "class": "total",
            "level": 1,
            "columns": columns,
        }

    def _get_report_vies(self, report, results, lines_results, options, tags=False):
        lines = []
        report_lines = []
        for result_line in lines_results:
            lines_lines = self._get_report_line_vies(report, result_line, tags=tags)
            report_lines.append(lines_lines["l10n_bg_vat_vies"])
        for result in results:
            report_line = self._get_report_line_vies(report, result, tags=tags)
            report_line.update(
                {
                    "info_tag_ttr": report_lines,
                }
            )
            lines.append((0, report_line))
        return lines

    def _get_report_line_vies(self, report, result, tags=False):
        column_values = {}
        company_id = result["company_id"]
        for key, value in result.items():
            if key == "company_id":
                continue
            # _logger.info(f"{key}: {value}")
            if key.startswith("account_tag_"):
                column_values.update(
                    {
                        key: {
                            "name": report.format_value(value, blank_if_zero=True),
                            "no_format": value,
                            "class": "font-monospace number",
                        }
                    }
                )
            else:
                column_values.update(
                    {
                        key: {
                            "name": value,
                            "no_format": value,
                            "class": "font-monospace text-left",
                        }
                    }
                )
        # _logger.info(f"lines {lines_results}")
        return {
            "id": report._get_generic_line_id("res.company", company_id),
            "name": "",
            "columns": [],
            "l10n_bg_vat_vies": column_values,
            "class": "o_account_reports_ja_subtable",
        }


class GenericTaxReportPurchaseCustomHandler(models.AbstractModel):
    _name = "bg.account.report.vat.purchase.custom.handler"
    _inherit = "bg.account.report.vat.declaration.custom.handler"
    _description = "Generic Tax Report Custom Handler (VAT Purchase report)"

    def _dynamic_lines_generator(
        self, report, options, all_column_groups_expression_totals
    ):
        """Overrides the dynamic line generation method to implement custom processing.

        Args:
            report (object): The report object.
            options (dict): Options for generating the report.
            all_column_groups_expression_totals (dict): Expression totals for all column groups.

        Returns:
            list of tuples: A list of tuples [(sequence, line_dict), ...], where:
                - sequence is the sequence to apply when rendering the line (can be mixed with static lines),
                - line_dict is a dict containing all the line values.
        """
        return super()._get_dynamic_lines(report, options, "purchases")


class GenericTaxReportSalesCustomHandler(models.AbstractModel):
    _name = "bg.account.report.vat.sales.custom.handler"
    _inherit = "bg.account.report.vat.declaration.custom.handler"
    _description = "Generic Tax Report Custom Handler (VAT Sales report)"

    def _dynamic_lines_generator(
        self, report, options, all_column_groups_expression_totals
    ):
        """Overrides the dynamic line generation method to implement custom processing.

        Args:
            report (object): The report object.
            options (dict): Options for generating the report.
            all_column_groups_expression_totals (dict): Expression totals for all column groups.

        Returns:
            list of tuples: A list of tuples [(sequence, line_dict), ...], where:
                - sequence is the sequence to apply when rendering the line (can be mixed with static lines),
                - line_dict is a dict containing all the line values.
        """
        return super()._get_dynamic_lines(report, options, "sales")


class GenericTaxReportViesCustomHandler(models.AbstractModel):
    _name = "bg.account.report.vat.vies.custom.handler"
    _inherit = "bg.account.report.vat.declaration.custom.handler"
    _description = "Generic Tax Report Custom Handler (VIES report)"

    def _dynamic_lines_generator(
        self, report, options, all_column_groups_expression_totals
    ):
        """Overrides the dynamic line generation method to implement custom processing.

        Args:
            report (object): The report object.
            options (dict): Options for generating the report.
            all_column_groups_expression_totals (dict): Expression totals for all column groups.

        Returns:
            list of tuples: A list of tuples [(sequence, line_dict), ...], where:
                - sequence is the sequence to apply when rendering the line (can be mixed with static lines),
                - line_dict is a dict containing all the line values.
        """
        return super()._get_dynamic_lines(report, options, "vies")
