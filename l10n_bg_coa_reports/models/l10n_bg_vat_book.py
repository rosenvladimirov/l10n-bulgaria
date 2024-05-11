import datetime
import io
import logging
import zipfile

from odoo import _, api, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class BulgarianReportCustomer(models.AbstractModel):
    _name = "l10n_bg_tax_report_handler"
    _inherit = "account.generic.tax.report.handler"
    _description = "Bulgarian Report Custom Handler"

    CONST_LEN_4 = 4
    CONST_LEN_15 = 15
    CONST_LEN_20 = 20
    CONST_LEN_30 = 30
    CONST_LEN_50 = 50
    CONST_VALUE = 0.00

    def _dynamic_lines_generator(
        self, report, options, all_column_groups_expression_totals
    ):
        # dict of the form {move_id: {column_group_key: {expression_label: value}}}
        move_info_dict = {}

        # dict of the form {column_group_key: total_value}
        total_values_dict = {}

        # Every key/expression_label that is a number (and should be rendered like one)
        number_keys = ["vat_20", "vat_9", "vat_0", "total"]

        # Build full query
        query_list = []
        full_query_params = []
        for (
            column_group_key,
            column_group_options,
        ) in report._split_options_per_column_group(options).items():
            query, params = self._build_query(
                report, column_group_options, column_group_key
            )
            query_list.append(f"({query})")
            full_query_params += params

            # Set defaults here since the results of the query for this column_group_key might be empty
            total_values_dict.setdefault(
                column_group_key, dict.fromkeys(number_keys, 0.0)
            )

        full_query = " UNION ALL ".join(query_list)
        self._cr.execute(full_query, full_query_params)
        results = self._cr.dictfetchall()
        for result in results:
            # Iterate over these results in order to fill the move_info_dict dictionary
            move_id = result["id"]
            column_group_key = result["column_group_key"]

            # Convert date to string to be displayed in the xlsx report
            result["date"] = result["date"].strftime("%d-%m-%Y")

            # For number rendering, take the opposite for sales taxes
            sign = -1.0 if result["tax_type"] == "sale" else 1.0

            current_move_info = move_info_dict.setdefault(move_id, {})

            current_move_info["line_name"] = result["move_name"]
            current_move_info[column_group_key] = result

            # Apply sign and add values to totals
            totals = total_values_dict[column_group_key]
            for key in number_keys:
                result[key] = sign * result[key]
                totals[key] += result[key]

        lines = []
        for move_id, move_info in move_info_dict.items():
            # 1 line for each move_id
            line = self._create_report_line(
                report, options, move_info, move_id, number_keys
            )
            lines.append((0, line))
        # Single total line if only one type of journal is selected
        selected_tax_types = self._vat_book_get_selected_tax_types(options)
        if len(selected_tax_types) < 2:
            total_line = self._create_report_total_line(
                report, options, total_values_dict
            )
            lines.append((0, total_line))

        return lines

    def _custom_options_initializer(self, report, options, previous_options=None):
        super()._custom_options_initializer(
            report, options, previous_options=previous_options
        )
        if previous_options is None:
            previous_options = {}

        # Add export button
        zip_export_button = {
            "name": _("VAT Book (ZIP)"),
            "sequence": 30,
            "action": "export_file",
            "action_param": "vat_book_export_files_to_zip",
            "file_export_type": _("ZIP"),
        }
        options["buttons"].append(zip_export_button)

        options["bg_vat_book_tax_types_available"] = {
            "sale": _("Sales"),
            "purchase": _("Purchases"),
            "all": _("All"),
        }

        if options.get("_running_export_test"):
            # Exporting the file is not allowed for 'all'. When executing the export tests, we hence always select 'sales', to avoid raising.
            options["bg_vat_book_tax_type_selected"] = "sale"
        else:
            options["bg_vat_book_tax_type_selected"] = previous_options.get(
                "bg_vat_book_tax_type_selected", "all"
            )

        tax_types = self._vat_book_get_selected_tax_types(options)

        columns_to_remove = []
        if not self.env["account.tax"].search(
            [
                ("type_tax_use", "in", tax_types),
                ("tax_group_id.l10n_bg_vat_code", "=", "1"),
            ]
        ):
            columns_to_remove.append("vat_9")
        if not self.env["account.tax"].search(
            [
                ("type_tax_use", "in", tax_types),
                ("tax_group_id.l10n_bg_vat_code", "=", "2"),
            ]
        ):
            columns_to_remove.append("vat_20")
        if not self.env["account.tax"].search(
            [
                ("type_tax_use", "in", tax_types),
                ("tax_group_id.l10n_bg_vat_code", "=", "0"),
            ]
        ):
            columns_to_remove.append("vat_0")
        options["columns"] = [
            col
            for col in options["columns"]
            if col["expression_label"] not in columns_to_remove
        ]

    def _build_query(self, report, options, column_group_key):
        """
        Build a query to retrieve data for a VAT report.

        Parameters:
        - report: The VAT report object.
        - options: Options for the query.
        - column_group_key: The key for grouping columns.

        Returns:
        A query for retrieving data.
        """
        tables, where_clause, where_params = report._query_get(options, "strict_range")

        where_clause = f"AND {where_clause}"
        tax_types = tuple(self._vat_book_get_selected_tax_types(options))

        return self.env["account.bg.vat.line"]._bg_vat_line_build_query(
            tables, where_clause, where_params, column_group_key, tax_types
        )

    def _create_report_line(self, report, options, move_vals, move_id, number_values):
        """Create a standard (non total) line for the report
        :param options: report options
        :param move_vals: values necessary for the line
        :param move_id: id of the account.move (or account.bg.vat.line)
        :param number_values: list of expression_label that require the 'number' class
        """
        columns = []
        for column in options["columns"]:
            expression_label = column["expression_label"]
            value = move_vals.get(column["column_group_key"], {}).get(expression_label)

            columns.append(
                {
                    "name": report.format_value(
                        value, figure_type=column["figure_type"]
                    )
                    if value is not None
                    else None,
                    "no_format": value,
                    "class": "number" if expression_label in number_values else "",
                }
            )

        return {
            "id": report._get_generic_line_id("account.move", move_id),
            "caret_options": "account.move",
            "name": move_vals["line_name"],
            "columns": columns,
            "level": 2,
        }

    def _create_report_total_line(self, report, options, total_vals):
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
            "name": _("Total"),
            "class": "total",
            "level": 1,
            "columns": columns,
        }

    def vat_book_export_files_to_zip(self, options):
        """Export method that lets us export the VAT book to a zip archive.
        It contains the files that we upload for Purchase VAT Book"""
        tax_type = self._vat_book_get_selected_tax_types(options)
        tax_type = tax_type[0]

        # Build file name
        export_file_name = {
            "sale": "VAT_Book_Sales",
            "purchase": "VAT_Book_Purchase",
            "declar": "VAT_Book_Declar",
        }.get(tax_type, "VAT_Book")
        export_file_name = f"{export_file_name}_{options['date']['date_to']}"

        # Build zip content
        filenames = self._get_filenames()

        stream = io.BytesIO()
        with zipfile.ZipFile(stream, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            (
                vouchers_data,
                aliquots_data,
                declaration,
                purchase,
            ) = self._vat_book_get_txt_files(options, tax_type)

            zf.writestr(filenames.get("sale") + ".txt", vouchers_data)
            zf.writestr(filenames.get("purchases") + ".txt", purchase)
            zf.writestr(filenames.get("declar") + ".txt", declaration)

        file_content = stream.getvalue()
        return {
            "file_name": export_file_name,
            "file_content": file_content,
            "file_type": "zip",
        }

    def _vat_book_get_txt_files(self, options, tax_type):
        """Compute the date to be printed in the txt files"""
        lines = []
        invoices = self._vat_book_get_txt_invoices(options)

        aliquots_data = "\r\n".join(lines).encode("cp1251")
        vouchers_data = "\r\n".join(
            self._vat_book_get_REGINFO_SALES(options, tax_type, invoices)
        ).encode("cp1251", "ignore")
        declaration = "\r\n".join(
            self._vat_book_get_REGINFO_DECLARATION(options, tax_type, invoices)
        ).encode("cp1251", "ignore")
        purchase = "\r\n".join(
            self._vat_book_get_REGINFO_PURCHASE(options, tax_type, invoices)
        ).encode("cp1251", "ignore")

        return vouchers_data, aliquots_data, declaration, purchase

    def _vat_book_get_selected_tax_types(self, options):
        # Retrieve the selected tax type from the options.
        selected = options["bg_vat_book_tax_type_selected"]

        # Return a list of tax types based on the selected value.
        # If 'all' is selected, include both 'sale' and 'purchase' tax types.
        # Otherwise, include the selected tax type.
        return ["sale", "purchase", "declar"] if selected == "all" else [selected]

    @api.model
    def _vat_book_get_lines_domain(self, options):
        # Retrieve the company IDs associated with the current environment.
        company_ids = self.env.company.ids

        # Get selected journal types based on the provided options.
        selected_journal_types = self._vat_book_get_selected_tax_types(options)
        domain = [
            ("journal_id.type", "in", selected_journal_types),
            ("company_id", "in", company_ids),
        ]

        # Determine the state of entries to include in the domain (all or posted).
        state = options.get("all_entries") and "all" or "posted"

        # Add a condition to the domain if it's not 'all,' filtering by entry state.
        if state and state.lower() != "all":
            domain += [("state", "=", state)]

        # Add conditions to the domain based on date filters if provided.
        if options.get("date").get("date_to"):
            domain += [("date", "<=", options["date"]["date_to"])]
        if options.get("date").get("date_from"):
            domain += [("date", ">=", options["date"]["date_from"])]

        # Return the final domain, which will be used to filter account moves (entries).
        return domain

    def _vat_book_get_txt_invoices(self, options):
        # Determine the state of entries to include in the TXT file (posted or all).
        state = options.get("all_entries") and "all" or "posted"

        # Check if the state is 'posted'; only posted entries are allowed for TXT file generation.
        if state != "posted":
            raise UserError(
                _(
                    "Can only generate TXT files using posted entries."
                    " Please remove Include unposted entries filter and try again"
                )
            )

        # Define a domain to filter the account moves based on options and generate TXT invoices.
        domain = [("move_type", "!=", False)] + self._vat_book_get_lines_domain(options)

        # Retrieve and return the account moves (invoices) that match the specified domain.
        return self.env["account.move"].search(
            domain, order="invoice_date asc, name asc, id asc"
        )

    def _vat_book_get_REGINFO_SALES(self, options, tax_type, invoices):
        """
        Generate a report containing VAT-related information Sale.

        This method generates a report with VAT information for a specific set of invoices, focusing on sales transactions.

        Args:
            options (dict): A dictionary of report options.
            aliquots (list): A list of VAT aliquots.
            tax_type (str): The type of tax (e.g., 'sales' or 'purchase').
            invoices (list): A list of invoice objects.

        Returns:
            list: A list of strings representing the generated report.

        Parameters:
            - options (dict): A dictionary containing various report options.
            - aliquots (list): A list of VAT aliquots for processing.
            - tax_type (str): The type of tax, which can be 'sales'.
            - invoices (list): A list of invoice objects to generate the report.

        Returns:
            list: A list of strings representing the generated VAT report. Each string
            represents a row of information in the report.

        This method calculates various VAT-related information for each sales invoice, including VAT amounts, document type, and invoice numbers. It then generates a formatted row for each sales invoice and appends it to the result list. The result list represents a VAT-related report, focusing on sales transactions, which is returned as a list of strings.

        Note:
        - The returned list may contain multiple strings, one for each sales invoice's information.
        - The formatting of the generated report is specific to VAT-related information for sales.
        - The 'tax_type' parameter determines whether it's a sales or purchase report.

        """
        serial_number = 0
        res = []
        for inv in invoices:
            amounts = self._calculate_sales_invoice_totals(options, inv)
            sales_vat_total = amounts["sales_vat_total"]

            # Different TAGS for SALES
            amount_sales = self._calculate_amount_for_different_sales_taxes(
                inv, options
            )
            amount_tag_11 = amount_sales["amount_tag_11"]
            amount_tag_12 = amount_sales["amount_tag_12_1"]
            amount_tag_26 = amount_sales["amount_tag_12_2"]
            amount_tag_21 = amount_sales["amount_tag_21"]
            amount_tag_15 = amount_sales["amount_tag_15"]
            amount_tag_16 = amount_sales["amount_tag_16"]
            amount_tag_17 = amount_sales["amount_tag_17"]
            amount_tag_18 = amount_sales["amount_tag_18"]
            amount_tag_19 = amount_sales["amount_tag_19"]
            amount_tag_23 = amount_sales["amount_tag_23"]
            amount_tag_13 = amount_sales["amount_tag_13"]
            amount_tag_22 = amount_sales["amount_tag_22"]
            amount_tag_24 = amount_sales["amount_tag_24"]
            amount_tag_14 = amount_sales["amount_tag_14"]

            amount_total = self._calculate_amount_total(inv)
            doc_type = self._get_document_type(inv)
            invoice_number = self._get_document_number(inv)

            if inv.move_type in ["out_refund", "out_invoice"]:
                serial_number += 1
                row = f'{self._base_lenght_formatting(inv.company_id.vat, self.CONST_LEN_15)}{inv.invoice_date.strftime("%Y%m")}{f"{0:d}".rjust(4)}{f"{serial_number:d}".rjust(self.CONST_LEN_15)}{doc_type}{self._base_lenght_formatting(invoice_number, self.CONST_LEN_20)}{inv.invoice_date.strftime("%d/%m/%Y")}{self._base_lenght_formatting(inv.partner_id.vat, self.CONST_LEN_15)}{self._base_lenght_formatting(inv.commercial_partner_id.name, self.CONST_LEN_50)}{self._base_lenght_formatting("Продажба на стоки и услуги", self.CONST_LEN_30)}{self._base_number_formatting(amount_total, self.CONST_LEN_15)}{self._base_number_formatting(sales_vat_total, self.CONST_LEN_15)}{self._base_number_formatting(amount_tag_11, self.CONST_LEN_15)}{self._base_number_formatting(amount_tag_21, self.CONST_LEN_15)}{self._base_number_formatting(amount_tag_12, self.CONST_LEN_15)}{self._base_number_formatting(amount_tag_26, self.CONST_LEN_15)}{self._base_number_formatting(amount_tag_22, self.CONST_LEN_15)}{self._base_number_formatting(amount_tag_23, self.CONST_LEN_15)}{self._base_number_formatting(amount_tag_13, self.CONST_LEN_15)}{self._base_number_formatting(amount_tag_24, self.CONST_LEN_15)}{self._base_number_formatting(amount_tag_14, self.CONST_LEN_15)}{self._base_number_formatting(amount_tag_15, self.CONST_LEN_15)}{self._base_number_formatting(amount_tag_16, self.CONST_LEN_15)}{self._base_number_formatting(amount_tag_17, self.CONST_LEN_15)}{self._base_number_formatting(amount_tag_18, self.CONST_LEN_15)}{self._base_number_formatting(amount_tag_19, self.CONST_LEN_15)}{self._base_number_formatting(self.CONST_VALUE, self.CONST_LEN_15)}{"  "}'
                res.append(
                    "".join(str(row))
                    .replace(",", "")
                    .replace("'", "")
                    .replace("[", "")
                    .replace("]", "")
                    .replace('"', "")
                )

        if res:
            res[-1] += "\n"

        return res

    def _vat_book_get_REGINFO_PURCHASE(self, options, tax_type, invoices):
        """
        Generate a report containing VAT-related information for purchases.
        This method generates a report with VAT information for a specific set of invoices, focusing on purchase transactions.
        Args:
            options (dict): A dictionary of report options.
            aliquots (list): A list of VAT aliquots.
            tax_type (str): The type of tax (e.g., 'sales' or 'purchase').
            invoices (list): A list of invoice objects.
        Returns:
            list: A list of strings representing the generated report.
        Parameters:
            - options (dict): A dictionary containing various report options.
            - aliquots (list): A list of VAT aliquots for processing.
            - tax_type (str): The type of tax, which can be 'purchase'.
            - invoices (list): A list of invoice objects to generate the report.
        Returns:
            list: A list of strings representing the generated VAT report. Each string
            represents a row of information in the report.
        This method calculates various VAT-related information for each purchase invoice, including VAT amounts, document type, and invoice numbers. It then generates a formatted row for each purchase invoice and appends it to the result list. The result list represents a VAT-related report, focusing on purchase transactions, which is returned as a list of strings.
        Note:
        - The returned list may contain multiple strings, one for each purchase invoice's information.
        - The formatting of the generated report is specific to VAT-related information for purchases.
        - The 'tax_type' parameter determines whether it's a sales or purchase report.
        """
        serial_number = 0
        res = []
        for inv in invoices:
            # Different TAGS for PURCHASES
            amount_purchase = self._calculate_amount_for_different_purchases_taxes(
                inv, options
            )
            amount_tag_41 = amount_purchase["amount_tag_41"]
            amount_tag_31 = amount_purchase["amount_tag_31"]
            amount_tag_32 = amount_purchase["amount_tag_32"]
            amount_tag_42 = amount_purchase["amount_tag_42"]
            amount_tag_30 = amount_purchase["amount_tag_30"]

            doc_type = self._get_document_type(inv)
            invoice_number = self._get_document_number(inv)

            if inv.move_type in ["in_refund", "in_invoice"]:
                serial_number += 1
                row = f'{self._base_lenght_formatting(inv.company_id.vat, self.CONST_LEN_15)}{inv.invoice_date.strftime("%Y%m")}{f"{0:d}".rjust(self.CONST_LEN_4)}{f"{serial_number:d}".rjust(self.CONST_LEN_15)}{doc_type}{self._base_lenght_formatting(invoice_number, self.CONST_LEN_20)}{inv.invoice_date.strftime("%d/%m/%Y")}{self._base_lenght_formatting(inv.partner_id.vat, self.CONST_LEN_15)}{self._base_lenght_formatting(inv.commercial_partner_id.name, self.CONST_LEN_50)}{self._base_lenght_formatting("Покупка на стоки и услуги", self.CONST_LEN_30)}{self._base_number_formatting(amount_tag_30, self.CONST_LEN_15)}{self._base_number_formatting(amount_tag_31, self.CONST_LEN_15)}{self._base_number_formatting(amount_tag_41, self.CONST_LEN_15)}{self._base_number_formatting(amount_tag_32, self.CONST_LEN_15)}{self._base_number_formatting(amount_tag_42, self.CONST_LEN_15)}{self._base_number_formatting(self.CONST_VALUE, self.CONST_LEN_15)}{self._base_number_formatting(self.CONST_VALUE, self.CONST_LEN_15)}{"  "}'
                res.append(
                    "".join(str(row))
                    .replace(",", "")
                    .replace("'", "")
                    .replace("[", "")
                    .replace("]", "")
                    .replace('"', "")
                )

        if res:
            res[-1] += "\n"

        return res

    def _vat_book_get_REGINFO_DECLARATION(self, options, tax_type, invoices):
        """
        Generate and return VAT registration information for a specific period (Vat Declaration).

        This method generates VAT registration information for a specified period based on a set of invoices and VAT data. It aggregates various sales and purchase totals and creates a formatted row containing the VAT registration information.

        Args:
            options (dict): Options and settings for generating the registration information.
            aliquots (list): A list of VAT aliquots.
            tax_type (str): The type of tax (e.g., 'sales', 'purchases').
            invoices (list): A list of invoice objects.

        Returns:
            list: A list containing the formatted VAT registration information row.

        Parameters:
            - options (dict): A dictionary containing various options and settings for generating the registration information.
            - aliquots (list): A list of VAT aliquots for processing.
            - tax_type (str): The type of tax, which can be 'sales' or 'purchases'.
            - invoices (list): A list of invoice objects for generating the report.

        Returns:
            list: A list containing a single formatted row of VAT registration information.

        This method calculates VAT registration information for a specific period, based on a set of invoices and VAT data. It calculates various sales and purchase totals and creates a formatted row with this information.

        Note:
        - The generated list contains a single string with the formatted registration information.
        - The formatting is specific to VAT registration information.
        - The 'tax_type' parameter determines whether it's a sales or purchase report.

        """
        # Amount TAGS from PURCHASES
        amounts_purchase = self._calculate_amount_for_different_purchases_taxes(
            invoices, options
        )
        amount_tag_41 = amounts_purchase["amount_tag_41"]
        amount_tag_31 = amounts_purchase["amount_tag_31"]
        amount_tag_32 = amounts_purchase["amount_tag_32"]
        amount_tag_42 = amounts_purchase["amount_tag_42"]
        amount_tag_30 = amounts_purchase["amount_tag_30"]
        vat_tax_40 = amounts_purchase["vat_tax_40"]
        count_purchase = amounts_purchase["len"]

        # Amount TAGS from SALES
        amounts = self._calculate_amount_for_different_sales_taxes(invoices, options)
        amount_tag_11 = amounts["amount_tag_11"]
        amount_tag_21 = amounts["amount_tag_21"]
        amount_tag_15 = amounts["amount_tag_15"]
        amount_tag_16 = amounts["amount_tag_16"]
        amount_tag_17 = amounts["amount_tag_17"]
        amount_tag_19 = amounts["amount_tag_19"]
        amount_tag_13 = amounts["amount_tag_13"]
        amount_tag_24 = amounts["amount_tag_24"]
        amount_tag_14 = amounts["amount_tag_14"]
        amount_tag_23 = amounts["amount_tag_23"]
        amount_tag_22 = amounts["amount_tag_22"]
        amount_tag_12 = amounts["amount_tag_12_1"] + amounts["amount_tag_12_2"]
        count_sales = amounts["len"]

        res = []

        amount_sales_vat = self._calculate_sales_invoice_totals(options, invoices)

        sales_total = amount_sales_vat["sales_total"]
        sales_vat_total = amount_sales_vat["sales_vat_total"]

        amount_tag_50 = (
            sales_vat_total - sales_vat_total if sales_vat_total >= vat_tax_40 else 0
        )
        amount_tag_60 = (
            vat_tax_40 - sales_vat_total if sales_vat_total < vat_tax_40 else 0
        )

        row = f'{self._base_lenght_formatting(invoices[0].company_id.vat, self.CONST_LEN_15)}{self._base_lenght_formatting(invoices[0].company_id.name, self.CONST_LEN_50)}{invoices[0].invoice_date.strftime("%Y%m")}{self._base_lenght_formatting("3445837/Тома Томов", self.CONST_LEN_50)}{f"{count_sales:d}".rjust(self.CONST_LEN_15)}{f"{count_purchase:d}".rjust(self.CONST_LEN_15)}{self._base_number_formatting(sales_total, self.CONST_LEN_15)}{self._base_number_formatting(sales_vat_total, self.CONST_LEN_15)}{self._base_number_formatting(amount_tag_11, self.CONST_LEN_15)}{self._base_number_formatting(amount_tag_21, self.CONST_LEN_15)}{self._base_number_formatting(amount_tag_12, self.CONST_LEN_15)}{self._base_number_formatting(amount_tag_22, self.CONST_LEN_15)}{self._base_number_formatting(amount_tag_23, self.CONST_LEN_15)}{self._base_number_formatting(amount_tag_13, self.CONST_LEN_15)}{self._base_number_formatting(amount_tag_24, self.CONST_LEN_15)}{self._base_number_formatting(self.CONST_VALUE, self.CONST_LEN_15)}{self._base_number_formatting(amount_tag_14, self.CONST_LEN_15)}{self._base_number_formatting(amount_tag_15, self.CONST_LEN_15)}{self._base_number_formatting(amount_tag_16, self.CONST_LEN_15)}{self._base_number_formatting(amount_tag_17, self.CONST_LEN_15)}{self._base_number_formatting(self.CONST_VALUE, self.CONST_LEN_15)}{self._base_number_formatting(amount_tag_19, self.CONST_LEN_15)}{self._base_number_formatting(amount_tag_30, self.CONST_LEN_15)}{self._base_number_formatting(amount_tag_31, self.CONST_LEN_15)}{self._base_number_formatting(amount_tag_41, self.CONST_LEN_15)}{self._base_number_formatting(amount_tag_32, self.CONST_LEN_15)}{self._base_number_formatting(amount_tag_42, self.CONST_LEN_15)}{self._base_number_formatting(self.CONST_VALUE, self.CONST_LEN_4)}{self._base_number_formatting(self.CONST_VALUE, self.CONST_LEN_15)}{self._base_number_formatting(vat_tax_40, self.CONST_LEN_15)}{self._base_number_formatting(amount_tag_50, self.CONST_LEN_15)}{self._base_number_formatting(amount_tag_60, self.CONST_LEN_15)}{self._base_number_formatting(self.CONST_VALUE, self.CONST_LEN_15)}{self._base_number_formatting(self.CONST_VALUE, self.CONST_LEN_15)}{self._base_number_formatting(self.CONST_VALUE, self.CONST_LEN_15)}{self._base_number_formatting(self.CONST_VALUE, self.CONST_LEN_15)}'
        res.append(
            "".join(str(row))
            .replace(",", "")
            .replace("'", "")
            .replace("[", "")
            .replace("]", "")
            .replace('"', "")
        )

        if res:
            res[-1] += "\n"
        return res

    ############################# HELPER METHODS

    def _calculate_sales_invoice_totals(self, options, invoices):
        # Returns filtered by date and  calculated SALES TOTAL, SALES VAT and SALES COUNT
        invoices = self._filter_invoices_by_date_range(
            options, invoices, "invoice_date"
        )
        invoices = self._filter_invoices_type(
            options, invoices, ["out_invoice", "out_refund"]
        )

        # SALES TOTAL AMOUNT and SALES VAT TOTAL AMOUNT
        return {
            "sales_total": sum(
                abs(inv.price_subtotal) for inv in invoices.invoice_line_ids
            ),
            "sales_vat_total": sum(abs(inv.amount_tax) for inv in invoices),
        }

    def _calculate_amount_total(self, invoices):
        # Returns amount for different type documents
        if invoices.move_type in ["out_refund", "in_refund"]:
            amount_total = -invoices.amount_total
        else:
            amount_total = sum(inv.price_subtotal for inv in invoices.invoice_line_ids)

        return amount_total

    def _calculate_amount_for_different_purchases_taxes(self, invoices, options):
        # Calculate and return filtered invoices total amounts of VAT with different tax taxs a given invoice.
        invoices = self._filter_invoices_type(
            options, invoices, ["in_invoice", "in_refund"]
        )
        invoices = self._filter_invoices_by_date_range(options, invoices, "date")

        # Define tax tag IDs for different categories
        tax_tag_ids = {
            "amount_tag_41": 39,
            "amount_tag_31": 35,
            "amount_tag_32": 37,
            "amount_tag_42": 41,
            "amount_tag_30": 33,
        }

        tax_tag_ids_neg = {
            "amount_tag_41_neg": 38,
            "amount_tag_31_neg": 34,
            "amount_tag_32_neg": 36,
            "amount_tag_42_neg": 40,
            "amount_tag_30_neg": 32,
        }

        # Calculate total amounts for each tax tag
        total_amounts = {}
        for tag, id in tax_tag_ids.items():
            total_amounts[tag] = sum(
                [
                    abs(line.balance)
                    for line in invoices.line_ids
                    if line.tax_tag_ids.id == id
                ]
            )

        for tag, id in tax_tag_ids_neg.items():
            total_amounts[tag] = sum(
                [
                    abs(line.balance)
                    for line in invoices.line_ids
                    if line.tax_tag_ids.id == id
                ]
            )

        total_amounts["amount_tag_31"] = (
            total_amounts["amount_tag_31"] - total_amounts["amount_tag_31_neg"]
        )
        total_amounts["amount_tag_32"] = (
            total_amounts["amount_tag_32"] - total_amounts["amount_tag_32_neg"]
        )
        total_amounts["amount_tag_41"] = (
            total_amounts["amount_tag_41"] - total_amounts["amount_tag_41_neg"]
        )
        total_amounts["amount_tag_42"] = (
            total_amounts["amount_tag_42"] - total_amounts["amount_tag_42_neg"]
        )
        total_amounts["amount_tag_30"] = (
            total_amounts["amount_tag_30"] - total_amounts["amount_tag_30_neg"]
        )

        total_amounts["vat_tax_40"] = sum(
            [
                inv.amount_tax
                for inv in invoices
                if inv.move_type in ["in_invoice", "in_refund"]
            ]
        )
        # Calculated purchases invoice length
        total_amounts["len"] = len(invoices)

        return total_amounts

    def _calculate_amount_for_different_sales_taxes(self, invoices, options):
        # Calculate and return filtered invoices total amounts of VAT with different tax tags a given invoice.
        invoices = self._filter_invoices_type(
            options, invoices, ["out_invoice", "out_refund"]
        )
        invoices = self._filter_invoices_by_date_range(
            options, invoices, "invoice_date"
        )

        # Define tax tag IDs for different categories
        tag_tax_ids = {
            "amount_tag_11": 5,
            "amount_tag_12_1": 6,
            "amount_tag_12_2": 9,
            "amount_tag_21": 25,
            "amount_tag_22": 27,
            "amount_tag_13": 11,
            "amount_tag_24": 31,
            "amount_tag_14": 13,
            "amount_tag_15": 15,
            "amount_tag_16": 17,
            "amount_tag_17": 19,
            "amount_tag_18": 21,
            "amount_tag_19": 23,
            "amount_tag_23": 29,
        }

        tag_tax_ids_neg = {
            "amount_tag_11_neg": 4,
            "amount_tag_12_1_neg": 7,
            "amount_tag_12_2_neg": 8,
            "amount_tag_21_neg": 24,
            "amount_tag_22_neg": 26,
            "amount_tag_13_neg": 10,
            "amount_tag_24_neg": 30,
            "amount_tag_14_neg": 12,
            "amount_tag_15_neg": 14,
            "amount_tag_16_neg": 16,
            "amount_tag_17_neg": 18,
            "amount_tag_18_neg": 20,
            "amount_tag_19_neg": 22,
            "amount_tag_23_neg": 28,
        }

        # Calculate total amounts for each tax tag
        total_amounts = {}
        for tag, ids in tag_tax_ids.items():
            total_amounts[tag] = sum(
                [
                    abs(line.balance)
                    for line in invoices.line_ids
                    if line.tax_tag_ids.id in ids
                ]
            )

        # Calculated sales invoice length
        total_amounts["len"] = len(invoices)

        return total_amounts

    def _convert_date_string_to_date(self, date_str):
        # Returns convert string to datetime.datetime
        try:
            date_datetime = datetime.datetime.strptime(date_str, "%Y-%m-%d")
            return date_datetime.date()
        except ValueError:
            # Handle invalid date string or format as needed
            raise ValueError("Invalid cast from string to datetime")

    def _get_document_number(self, invoice):
        # Returns Invoice numbers
        return (
            invoice.ref
            if invoice.move_type in ["in_invoice", "in_refund"]
            else invoice.name
        )

    def _get_document_type(self, inv):
        # Returns invoice type
        return {
            "in_invoice": "01",
            "out_invoice": "01",
            "out_refund": "03",
            "in_refund": "03",
        }.get(inv.move_type, None)

    def _get_filenames(self):
        # Returns filenames for zip
        return {
            "declar": "Declar",
            "purchases": "Pokupki",
            "purchases_aliquots": "VAT_Purchases",
            "sale": "Prodagbi",
            "sale_aliquots": "VAT_Sales",
        }

    ########################### FILTER METHODS

    def _filter_invoices_type(self, options, invoices, move_types):
        # Returns filtered invoices
        filtered_invoices = invoices.filtered(lambda inv: inv.move_type in move_types)

        return filtered_invoices

    def _filter_invoices_by_date_range(self, options, invoices, custom_date_attribute):
        # Returns filtered invoices
        date_from_str = options["date"]["date_from"]
        date_to_str = options["date"]["date_to"]

        date_from_date = self._convert_date_string_to_date(date_from_str)
        date_to_date = self._convert_date_string_to_date(date_to_str)

        filtered_invoices = invoices.filtered(
            lambda inv: date_from_date
            <= getattr(inv, custom_date_attribute)
            <= date_to_date
        )

        return filtered_invoices

    #################################### BASE FORMATING PART

    def _base_lenght_formatting(self, value, max_length):
        # Formatting string values
        if len(value) < max_length:
            return value[:max_length].ljust(max_length)
        return value

    def _base_number_formatting(self, value, max_length):
        # Formatting numbers values
        formatted_value = f"{value:.2f}".rjust(max_length)
        return formatted_value
