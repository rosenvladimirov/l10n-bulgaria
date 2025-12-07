# Part of Odoo. See LICENSE file for full copyright and licensing details.
import datetime
import io
import json
import logging

from odoo import _, api, models

from odoo.addons.l10n_bg_reports_audit.models import l10n_bg_file_helper

from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class BulgarianTaxReportCustomHandler(models.AbstractModel):
    _name = "bg.account.report.vat.custom.handler"
    _inherit = ["account.generic.tax.report.handler", "l10n.bg.export.file"]
    _description = "Bulgarian Tax Report Custom Handler (VAT Declaration report)"

    def _custom_options_initializer(self, report, options, previous_options=None):
        super()._custom_options_initializer(
            report, options, previous_options=previous_options
        )
        options["buttons"].append(
            {
                "name": _("VAT Book (ZIP)"),
                "sequence": 30,
                "action": "export_file",
                "action_param": "l10n_bg_export_csvs_zip",
                "file_export_type": _("ZIP"),
            }
        )
        # ПРЕМАХВАНЕ НА EXCEL ЕКСПОРТ
        # Филтрираме buttons за да махнем Excel бутона
        if 'buttons' in options:
            options['buttons'] = [
                btn for btn in options['buttons']
                if btn.get('action') != 'export_file' or btn.get('action_param') != 'export_to_xlsx'
            ]

    def _caret_options_initializer(self):
        return {
            "account_move": [
                {
                    "name": _("Open Journal Entry"),
                    "action": "caret_option_open_record_form",
                },
            ],
        }

    def _get_results(self, report, options, tax_report):
        return self._get_l10n_bg_results(tax_report, options=options)

    def _get_dynamic_lines(self, report, options, grouping, warnings=None):
        pass

    def _get_dynamic_lines_data(self, report, options, tax_report, warnings=None):
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

        # Build queries for each column group and initialize the total values dictionary
        full_query = self._build_query(options, tax_report)
        # Execute the queries and fetch results
        self.env.cr.execute(full_query, [])
        return self.env.cr.dictfetchall(), tags

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
        return self._build_l10n_bg_query(tax_report, options=options)

    @staticmethod
    def get_value(raw_value):
        if not raw_value or isinstance(raw_value, (int, float, datetime.date)):
            return raw_value

        if isinstance(raw_value, dict):
            return list(raw_value.values())[-1]

        try:
            if raw_value.count('{') > 1:
                wrapped_json = '{"value": [' + raw_value + ']}'
                parsed_data = json.loads(wrapped_json)
                # Обединяваме всички стойности със запетая
                if parsed_data.get('value'):
                    values = []
                    for obj in parsed_data['value']:
                        if isinstance(obj, dict):
                            values.append(list(obj.values())[0])
                        else:
                            values.append(str(obj))
                    return ', '.join(values)
            else:
                parsed_data = json.loads(raw_value)
            if isinstance(parsed_data, dict):
                return list(parsed_data.values())[-1]
            return parsed_data
        except json.JSONDecodeError:
            return raw_value

    def _create_report_line(
            self, report, options, move_vals, move_id, number_values, tax_report
    ):
        """
        Constructs a single report line utilizing provided move values, configuration
        options, and parameters. Formats column data according to the specific tax
        report type and mapping expressions while ensuring appropriate line rendering.

        Arguments:
            report: The report instance that provides helper methods for formatting
                and id generation.
            options: A dictionary containing report configuration parameters,
                including details of the columns to process.
            move_vals: A dictionary or None, containing the values keyed by
                expression labels used to populate the report line.
            move_id: The identifier of the accounting move associated with this line.
            number_values: A list of expression labels that should be formatted as
                numeric values in the columns.
            tax_report: A string specifying the tax report type to determine the
                behavior, e.g., 'purchase' or 'sales'.

        Returns:
            dict: A dictionary representing the constructed report line, including
            id details, configured columns, and corresponding metadata.
        """

        line_name = ""
        columns = []
        for column in options["columns"]:
            expression_label = column["expression_label"]
            value = (move_vals or {}).get(expression_label)
            value = self.get_value(value)
            if tax_report == "purchase" and expression_label == "info_tag_6":
                line_name = value
            elif tax_report == "sales" and expression_label == "info_tag_5":
                line_name = value
            columns.append(
                {
                    "name": report.format_value(
                        options, value, column["figure_type"]
                    )
                    if value is not None
                    else None,
                    "no_format": value,
                    "expression_label": expression_label,
                    "column_group_key": column["column_group_key"],
                    "class": "number" if expression_label in number_values else "",
                }
            )
        return {
            "id": report._get_generic_line_id("account.move", move_id),
            "caret_options": "account.move",
            "name": line_name,
            "columns": columns,
            "level": 1,
        }

    @staticmethod
    def _create_report_total_line(report, options, total_vals, tax_report):
        """Create a total line for the report
        :param options:  options
        :param total_vals: values necessary for the line
        """
        columns = []
        for column in options["columns"]:
            expression_label = column["expression_label"]
            value = total_vals.get(column["column_group_key"], {}).get(expression_label)
            columns.append(
                {
                    "name": report.format_value(
                        options, value, column["figure_type"]
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
                    total_values_dict[column_group_key][key] += result[key]

        # _logger.info(f"{move_info_dict}")
        for move_id, move_info in move_info_dict.items():
            # _logger.info(f"move_info {move_info}")
            if not move_info:
                continue
            if isinstance(move_info, dict):
                move_info = list(move_info.values())[0]
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

    def _get_report_line_vies(self, report, results, options, tax_report=False, tags=False):
        lines = []
        if not results:
            return lines
        total_values_dict = {}
        partner_info_dict = {}
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
                partner_id = result["partner_id"]
                partner_info_dict.setdefault(partner_id, {})
                partner_info_dict[partner_id][column_group_key] = result
                for key in number_keys:
                    total_values_dict[column_group_key][key] += result[key]

        for partner_id, partner_info in partner_info_dict.items():
            if not partner_info:
                continue
            if isinstance(partner_info, dict):
                partner_info = list(partner_info.values())[0]
            line = self._create_report_line(
                report, options, partner_info, partner_id, number_keys, tax_report
            )
            line["caret_options"] = "res_partner"
            lines.append((0, line))

        total_line = self._create_report_total_line(
            report, options, total_values_dict, tax_report
        )
        lines.append((0, total_line))
        return lines

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
        company = self.env["res.company"].browse(company_id)
        format_params = {
            'currency': company.currency_id,
        }
        for key, value in result.items():
            if key == "company_id":
                continue
            value = self.get_value(value)
            if key.startswith("account_tag_"):
                column_values.update(
                    {
                        key: {
                            "name": report.format_value(options, value, 'monetary', format_params=format_params),
                            "no_format": value,
                            "class": "font-monospace line_cell number",
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
        line = self._create_report_line(
                report, options, result, company_id, [], tax_report="declaration"
            )
        return {
            "id": report._get_generic_line_id("res.company", company_id),
            "l10n_bg_vat_lines": [{"l10n_bg_vat_declaration": column_values}],
            **line,
        }

    def _export_to_pdf_base(self, report_ref, options, results, template_name):
        base_url = report_ref.get_base_url()
        print_options = {
            **report_ref.get_options(previous_options={**options, 'export_mode': 'print'}),
        }
        landscape = template_name in ['l10n_bg_vat_reports.vat_report_report_purchases_qweb',
                                      'l10n_bg_vat_reports.l10n_bg_vat_report_report_sales_qweb']
        shrinking = template_name in ['l10n_bg_vat_reports.l10n_bg_vat_report_declaration_qweb',
                                      'l10n_bg_vat_reports.l10n_bg_vat_report_report_vies_qweb']

        report = self.env['ir.actions.report']
        report_sudo = report.sudo()
        data = {
            'docs': report_ref,
            'options': print_options,
            'base_url': base_url,
            'company': self.env.company,
            **results,
        }
        html = report._render_template(template_name, data)
        bodies, html_ids, header, footer, specific_paperformat_args = report_sudo.with_context(**print_options)._prepare_html(html)
        specific_paperformat_args.update({
            'data-report-margin-top': 10,
            'data-report-header-spacing': 10,
            'data-report-margin-bottom': 10,
            'data-report-margin-left': 5,
            'data-report-margin-right': 5,
            'data-report-disable-shrinking': shrinking,
        })
        pdf_content = report_sudo._run_wkhtmltopdf(
            bodies,
            header=header,
            footer=footer,
            landscape=landscape,
            specific_paperformat_args=specific_paperformat_args,
        )
        pdf_content_stream = io.BytesIO(pdf_content)

        return {
            "file_name": report_ref.get_default_report_filename(print_options, 'pdf'),
            "file_content": pdf_content_stream,
            "file_type": "pdf",
        }


class GenericTaxReportDeclarationCustomHandler(models.AbstractModel):
    _name = "bg.account.report.vat.declaration.custom.handler"
    _inherit = ["bg.account.report.vat.custom.handler"]
    _description = "Generic Tax Report Custom Handler (VAT Declaration report)"

    def _custom_options_initializer(self, report, options, previous_options=None):
        super()._custom_options_initializer(
            report, options, previous_options=previous_options
        )
        options["column_headers"] = []
        options['custom_display_config'] = {
            'css_custom_class': 'generic_tax_report',
            'templates': {
                'AccountReportLineName': 'l10n_bg_vat_reports.VatReportLineTemplateDeclaration',
            },
        }

    def _get_dynamic_lines(self, report, options, grouping, warnings=None):
        results, tags = self._get_dynamic_lines_data(report, options, "declaration")
        return self._get_report_declaration(report, options, results, tags=tags)

    def export_to_pdf(self, options):
        """Export Declaration report to PDF using QWeb template"""
        report = self.env["account.report"].browse(options["report_id"])
        results, tags = self._get_dynamic_lines_data(report, options, "declaration")

        # Подготовка на данните за QWeb template
        base_url = report.get_base_url()
        print_options = report.get_options(previous_options={**options, 'export_mode': 'print'})

        # Парсване на резултатите за template-а
        parsed_results = []
        for result in results:
            parsed_result = {}
            for key, value in result.items():
                parsed_result[key] = self.get_value(value)
            parsed_results.append(parsed_result)

        # Подготовка на context за template
        data = {
            'docs': report,
            'options': print_options,
            'base_url': base_url,
            'company': self.env.company,
            'vat_report_declaration': parsed_results,
        }

        # Render на QWeb template
        template_name = 'l10n_bg_vat_reports.l10n_bg_vat_report_declaration_qweb'
        html = self.env['ir.actions.report']._render_template(template_name, data)

        # Генериране на PDF
        report_sudo = self.env['ir.actions.report'].sudo()
        bodies, html_ids, header, footer, specific_paperformat_args = report_sudo.with_context(
            **print_options
        )._prepare_html(html)

        # ВАЖНО: Използваме СТАНДАРТНИ margins (не custom!)
        pdf_content = report_sudo._run_wkhtmltopdf(
            bodies,
            header=header,
            footer=footer,
            landscape=False,
            specific_paperformat_args={
                'data-report-margin-top': 10,
                'data-report-header-spacing': 10,
                'data-report-margin-bottom': 15,  # Стандартен Odoo margin
                'data-report-disable-shrinking': True,
            }
        )

        return {
            "file_name": report.get_default_report_filename(print_options, 'pdf'),
            "file_content": pdf_content,
            "file_type": "pdf",
        }


class GenericTaxReportPurchaseCustomHandler(models.AbstractModel):
    _name = "bg.account.report.vat.purchase.custom.handler"
    _inherit = ["bg.account.report.vat.custom.handler"]
    _description = "Generic Tax Report Custom Handler (VAT Purchase report)"

    def _get_dynamic_lines(self, report, options, grouping, warnings=None):
        results, tags = self._get_dynamic_lines_data(report, options, "purchase")
        return self._get_report_sales_purchases(report, options, results, "purchase", tags=tags)

    def export_to_pdf(self, options):
        """Export Purchase report to PDF using QWeb template"""
        report = self.env["account.report"].browse(options["report_id"])
        results, tags = self._get_dynamic_lines_data(report, options, "purchase")

        base_url = report.get_base_url()
        print_options = report.get_options(previous_options={**options, 'export_mode': 'print'})

        # Парсване на резултатите
        parsed_results = []
        for result in results:
            parsed_result = {}
            for key, value in result.items():
                parsed_result[key] = self.get_value(value)
            parsed_results.append(parsed_result)

        data = {
            'docs': report,
            'options': print_options,
            'base_url': base_url,
            'company': self.env.company,
            'vat_report_purchase': parsed_results,
        }

        template_name = 'l10n_bg_vat_reports.l10n_bg_vat_report_report_purchases_qweb'
        html = self.env['ir.actions.report']._render_template(template_name, data)

        report_sudo = self.env['ir.actions.report'].sudo()
        bodies, html_ids, header, footer, specific_paperformat_args = report_sudo.with_context(
            **print_options
        )._prepare_html(html)

        pdf_content = report_sudo._run_wkhtmltopdf(
            bodies,
            header=header,
            footer=footer,
            landscape=True,  # Landscape за Purchase
            specific_paperformat_args={
                'data-report-margin-top': 10,
                'data-report-header-spacing': 10,
                'data-report-margin-bottom': 15,
            }
        )

        return {
            "file_name": report.get_default_report_filename(print_options, 'pdf'),
            "file_content": pdf_content,
            "file_type": "pdf",
        }


class GenericTaxReportSalesCustomHandler(models.AbstractModel):
    _name = "bg.account.report.vat.sales.custom.handler"
    _inherit = "bg.account.report.vat.custom.handler"
    _description = "Generic Tax Report Custom Handler (VAT Sales report)"

    def _get_dynamic_lines(self, report, options, grouping, warnings=None):
        results, tags = self._get_dynamic_lines_data(report, options, "sales")
        return self._get_report_sales_purchases(report, options, results, "sales", tags=tags)

    def export_to_pdf(self, options):
        """Export Sales report to PDF using QWeb template"""
        report = self.env["account.report"].browse(options["report_id"])
        results, tags = self._get_dynamic_lines_data(report, options, "sales")

        base_url = report.get_base_url()
        print_options = report.get_options(previous_options={**options, 'export_mode': 'print'})

        # Парсване на резултатите
        parsed_results = []
        for result in results:
            parsed_result = {}
            for key, value in result.items():
                parsed_result[key] = self.get_value(value)
            parsed_results.append(parsed_result)

        data = {
            'docs': report,
            'options': print_options,
            'base_url': base_url,
            'company': self.env.company,
            'vat_report_sales': parsed_results,
        }

        template_name = 'l10n_bg_vat_reports.l10n_bg_vat_report_report_sales_qweb'
        html = self.env['ir.actions.report']._render_template(template_name, data)

        report_sudo = self.env['ir.actions.report'].sudo()
        bodies, html_ids, header, footer, specific_paperformat_args = report_sudo.with_context(
            **print_options
        )._prepare_html(html)

        pdf_content = report_sudo._run_wkhtmltopdf(
            bodies,
            header=header,
            footer=footer,
            landscape=True,  # Landscape за Sales
            specific_paperformat_args={
                'data-report-margin-top': 10,
                'data-report-header-spacing': 10,
                'data-report-margin-bottom': 15,
            }
        )

        return {
            "file_name": report.get_default_report_filename(print_options, 'pdf'),
            "file_content": pdf_content,
            "file_type": "pdf",
        }


class GenericTaxReportViesCustomHandler(models.AbstractModel):
    _name = "bg.account.report.vat.vies.custom.handler"
    _inherit = ["bg.account.report.vat.custom.handler"]
    _description = "Generic Tax Report Custom Handler (VIES report)"

    def _custom_options_initializer(self, report, options, previous_options=None):
        super()._custom_options_initializer(
            report, options, previous_options=previous_options
        )
        vies_results, vies_tags = self._get_dynamic_lines_data(report, options, "vies")
        parce_vies_results = {}
        for results in vies_results:
            for key, value in results.items():
                parce_vies_results[key] = self.get_value(value)
        options["column_headers"][0][0].update(parce_vies_results)
        options['custom_display_config'] = {
            'css_custom_class': 'generic_tax_report',
            'templates': {
                'AccountReportLineName': 'l10n_bg_vat_reports.VatReportLineTemplateVies',
            },
        }

    def _get_dynamic_lines(self, report, options, grouping, warnings=None):
        results, tags = self._get_dynamic_lines_data(report, options, "vies_lines")
        return self._get_report_line_vies(
            report, results, options, "vies_lines", tags=tags
        )

    def export_to_pdf(self, options):
        """Export VIES report to PDF using QWeb template"""
        report = self.env["account.report"].browse(options["report_id"])

        # Взимаме header данни
        vies_header_results, vies_tags = self._get_dynamic_lines_data(report, options, "vies")
        parsed_header = {}
        for result in vies_header_results:
            for key, value in result.items():
                parsed_header[key] = self.get_value(value)

        # Взимаме line данни
        vies_lines_results, _ = self._get_dynamic_lines_data(report, options, "vies_lines")
        parsed_lines = []
        for result in vies_lines_results:
            parsed_result = {}
            for key, value in result.items():
                parsed_result[key] = self.get_value(value)
            parsed_lines.append(parsed_result)

        base_url = report.get_base_url()
        print_options = report.get_options(previous_options={**options, 'export_mode': 'print'})

        data = {
            'docs': report,
            'options': print_options,
            'base_url': base_url,
            'company': self.env.company,
            'vat_report_vies': [parsed_header],  # Header като list
            'vat_report_vies_lines': parsed_lines,  # Lines
        }

        template_name = 'l10n_bg_vat_reports.l10n_bg_vat_report_report_vies_qweb'
        html = self.env['ir.actions.report']._render_template(template_name, data)

        report_sudo = self.env['ir.actions.report'].sudo()
        bodies, html_ids, header, footer, specific_paperformat_args = report_sudo.with_context(
            **print_options
        )._prepare_html(html)

        pdf_content = report_sudo._run_wkhtmltopdf(
            bodies,
            header=header,
            footer=footer,
            landscape=False,
            specific_paperformat_args={
                'data-report-margin-top': 10,
                'data-report-header-spacing': 10,
                'data-report-margin-bottom': 15,
                'data-report-disable-shrinking': True,
            }
        )

        return {
            "file_name": report.get_default_report_filename(print_options, 'pdf'),
            "file_content": pdf_content,
            "file_type": "pdf",
        }
