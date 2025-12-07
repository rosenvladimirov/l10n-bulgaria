# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
from collections import defaultdict

from odoo import _, fields, models
from odoo.tools import format_date

_logger = logging.getLogger(__name__)

MAX_NAME_LENGTH = 50


class BGAssetReportCustomHandler(models.AbstractModel):
    _name = "bg.account.asset.report.handler"
    _inherit = "account.report.custom.handler"
    _description = "Bulgaria Tax Asset Report Custom Handler"

    def _dynamic_lines_generator(
        self, report, options, all_column_groups_expression_totals, warnings=None
    ):
        report = self._with_context_company2code2model(report)

        lines, totals_by_column_group = self._generate_report_lines_without_grouping(
            report, options
        )
        # add the groups by account
        if options["assets_groupby_tax_profile"]:
            lines = self._group_by_tax_profile(report, lines, options)
        else:
            lines = report._regroup_lines_by_name_prefix(
                options,
                lines,
                "_report_expand_unfoldable_line_assets_report_prefix_group",
                0,
            )

        # add the total line
        total_columns = []
        for column_data in options["columns"]:
            col_value = totals_by_column_group[column_data["column_group_key"]].get(
                column_data["expression_label"]
            )
            if column_data.get("figure_type") == "monetary":
                total_columns.append(
                    {
                        "name": report.format_value(
                            options,
                            col_value,
                            figure_type="monetary",
                            format_params={"currency_id": self.env.company.currency_id.id},
                        ),
                        "no_format": col_value,
                    }
                )
            else:
                total_columns.append({})

        lines.append(
            {
                "id": report._get_generic_line_id(None, None, markup="total"),
                "level": 1,
                "class": "total",
                "name": _("Total"),
                "columns": total_columns,
                "unfoldable": False,
                "unfolded": False,
            }
        )
        return [(0, line) for line in lines]

    def _generate_report_lines_without_grouping(
        self,
        report,
        options,
        prefix_to_match=None,
        parent_id=None,
        forced_model_id=None,
    ):
        # construct a dictionary:
        #   {(model_id, asset_id): {col_group_key: {expression_label_1: value, expression_label_2: value, ...}}}
        all_asset_ids = set()
        all_lines_data = {}
        for (
            column_group_key,
            column_group_options,
        ) in report._split_options_per_column_group(options).items():
            # the lines returned are already sorted by l10n_bg_model_id !
            lines_query_results = self._query_lines(
                column_group_options,
                prefix_to_match=prefix_to_match,
                forced_model_id=forced_model_id,
            )
            for model_id, asset_id, cols_by_expr_label in lines_query_results:
                line_id = (model_id, asset_id)
                all_asset_ids.add(asset_id)
                if line_id not in all_lines_data:
                    all_lines_data[line_id] = {column_group_key: []}
                all_lines_data[line_id][column_group_key] = cols_by_expr_label

        column_names = [
            "assets_date_from",
            "assets_plus",
            "assets_minus",
            "assets_date_to",
            "depre_date_from",
            "depre_plus",
            "depre_minus",
            "depre_date_to",
            "balance",
        ]
        totals_by_column_group = defaultdict(lambda: dict.fromkeys(column_names, 0.0))

        # Browse all the necessary assets in one go, to minimize the number of queries
        assets_cache = {
            asset.id: asset for asset in self.env["account.asset"].browse(all_asset_ids)
        }

        # construct the lines, 1 at a time
        lines = []
        company_currency = self.env.company.currency_id
        for (model_id, asset_id), col_group_totals in all_lines_data.items():
            all_columns = []
            for column_data in options["columns"]:
                col_group_key = column_data["column_group_key"]
                expr_label = column_data["expression_label"]
                if (
                    col_group_key not in col_group_totals
                    or expr_label not in col_group_totals[col_group_key]
                ):
                    all_columns.append({})
                    continue

                col_value = col_group_totals[col_group_key][expr_label]
                if col_value is None:
                    all_columns.append({})
                elif column_data["figure_type"] == "monetary":
                    all_columns.append(
                        {
                            "name": report.format_value(
                                options,
                                col_value,
                                figure_type="monetary",
                                format_params={"currency_id": company_currency.id},
                            ),
                            "no_format": col_value,
                        }
                    )
                else:
                    all_columns.append({"name": col_value, "no_format": col_value})

                # add to the total line
                if column_data["figure_type"] == "monetary":
                    totals_by_column_group[column_data["column_group_key"]][
                        column_data["expression_label"]
                    ] += col_value

            name = assets_cache[asset_id].name
            line = {
                "id": report._get_generic_line_id(
                    "account.asset", asset_id, parent_line_id=parent_id
                ),
                "level": 2,
                "name": name,
                "columns": all_columns,
                "unfoldable": False,
                "unfolded": False,
                "caret_options": "account_asset_line",
                "model_id": model_id,
                "class": "o_account_asset_contrast_inner",
            }
            if parent_id:
                line["parent_id"] = parent_id
            if len(name) >= MAX_NAME_LENGTH:
                line["title_hover"] = name
            lines.append(line)

        return lines, totals_by_column_group

    def _caret_options_initializer(self):
        # Use 'caret_option_open_record_form' defined in account_reports rather than a custom function
        return {
            "account_asset_line": [
                {"name": _("Open Asset"), "action": "caret_option_open_record_form"},
            ]
        }

    def _custom_options_initializer(self, report, options, previous_options=None):
        super()._custom_options_initializer(
            report, options, previous_options=previous_options
        )
        column_group_options_map = report._split_options_per_column_group(options)

        for col in options["columns"]:
            column_group_options = column_group_options_map[col["column_group_key"]]
            # Dynamic naming of columns containing dates
            if col["expression_label"] == "balance":
                col["name"] = ""  # The column label will be displayed in the subheader
            if col["expression_label"] in ["assets_date_from", "depre_date_from"]:
                col["name"] = format_date(
                    self.env, column_group_options["date"]["date_from"]
                )
            elif col["expression_label"] in ["assets_date_to", "depre_date_to"]:
                col["name"] = format_date(
                    self.env, column_group_options["date"]["date_to"]
                )

        options["custom_columns_subheaders"] = [
            {"name": _("Characteristics"), "colspan": 4},
            {"name": _("Assets"), "colspan": 4},
            {"name": _("Depreciation"), "colspan": 4},
            {"name": _("Book Value"), "colspan": 1},
        ]

        # Group by model by default
        groupby_activated = (previous_options or {}).get(
            "assets_groupby_tax_profile", True
        )
        options["assets_groupby_tax_profile"] = groupby_activated
        prefix_group_parameter_name = (
            "account_reports.assets_report.groupby_prefix_groups_threshold"
        )
        prefix_groups_threshold = int(
            self.env["ir.config_parameter"]
            .sudo()
            .get_param(prefix_group_parameter_name, 0)
        )
        if prefix_groups_threshold:
            options["groupby_prefix_groups_threshold"] = prefix_groups_threshold

        # Automatically unfold the report when printing it or not using prefix groups, unless some specific lines have been unfolded
        options["unfold_all"] = (
            self._context.get("print_mode") and not options.get("unfolded_lines")
        ) or (
            report.filter_unfold_all
            and (previous_options or {}).get("unfold_all", not prefix_groups_threshold)
        )

    def _with_context_company2code2model(self, report):
        if self.env.context.get("company2code2model") is not None:
            return report

        company2code2account = defaultdict(dict)
        for account in self.env["account.account"].search([]):
            # Use the first company from company_ids since account.account uses Many2many
            if account.company_ids:
                company_id = account.company_ids[0].id
                company2code2account[company_id][account.code] = account

        return report.with_context(company2code2account=company2code2account)

    def _query_lines(self, options, prefix_to_match=None, forced_model_id=None):
        """
        Returns a list of tuples: [(asset_id, model_id, [{expression_label: value}])]
        """
        lines = []
        asset_lines = self._query_values(
            options, prefix_to_match=prefix_to_match, forced_model_id=forced_model_id
        )

        # Assign the gross increases sub assets to their main asset (parent)
        parent_lines = []
        children_lines = defaultdict(list)
        for al in asset_lines:
            if al["parent_id"]:
                children_lines[al["parent_id"]] += [al]
            else:
                parent_lines += [al]

        for al in parent_lines:
            # Compute the depreciation rate string
            if (
                al["asset_method"] == "linear" and al["asset_method_number"]
            ):  # some assets might have 0 depreciations because they dont lose value
                total_months = int(al["asset_method_number"]) * int(
                    al["asset_method_period"]
                )
                months = total_months % 12
                years = total_months // 12
                asset_depreciation_rate = " ".join(
                    part
                    for part in [
                        years and _("%s y", years),
                        months and _("%s m", months),
                    ]
                    if part
                )
            elif al["asset_method"] == "linear":
                asset_depreciation_rate = "0.00 %"
            else:
                asset_depreciation_rate = ("{:.2f} %").format(
                    float(al["asset_method_progress_factor"]) * 100
                )

            # Copute the tax percentage string
            asset_method_percentage = al["asset_method_percentage"]
            _logger.info(f"asset_method_percentage: {asset_method_percentage}")
            if asset_method_percentage:
                asset_method_percentage = (
                    f"{float(asset_method_percentage) * 100:.2f} %"
                )
            else:
                asset_method_percentage = _("Not set")

            # Manage the opening of the asset
            opening = (
                al["asset_acquisition_date"] or al["asset_date"]
            ) < fields.Date.to_date(options["date"]["date_from"])

            # Get the main values of the board for the asset
            depreciation_opening = al["depreciated_before"]
            depreciation_add = al["depreciated_during"]
            depreciation_minus = 0.0

            asset_disposal_value = (
                al["asset_disposal_value"]
                if al["asset_disposal_date"]
                and al["asset_disposal_date"]
                <= fields.Date.to_date(options["date"]["date_to"])
                else 0.0
            )

            asset_opening = al["asset_original_value"] if opening else 0.0
            asset_add = 0.0 if opening else al["asset_original_value"]
            asset_minus = 0.0
            asset_salvage_value = al.get("asset_salvage_value", 0.0)

            # Add the main values of the board for all the sub assets (gross increases)
            for child in children_lines[al["asset_id"]]:
                depreciation_opening += child["depreciated_before"]
                depreciation_add += child["depreciated_during"]

                opening = (
                    child["asset_acquisition_date"] or child["asset_date"]
                ) < fields.Date.to_date(options["date"]["date_from"])
                asset_opening += child["asset_original_value"] if opening else 0.0
                asset_add += 0.0 if opening else child["asset_original_value"]

            # Compute the closing values
            asset_closing = asset_opening + asset_add - asset_minus
            depreciation_closing = (
                depreciation_opening + depreciation_add - depreciation_minus
            )
            al_currency = self.env["res.currency"].browse(al["asset_currency_id"])

            # Manage the closing of the asset
            if (
                al["asset_state"] == "close"
                and al["asset_disposal_date"]
                and al["asset_disposal_date"]
                <= fields.Date.to_date(options["date"]["date_to"])
                and al_currency.compare_amounts(
                    depreciation_closing, asset_closing - asset_salvage_value
                )
                == 0
            ):
                depreciation_add -= asset_disposal_value
                depreciation_minus += depreciation_closing - asset_disposal_value
                depreciation_closing = 0.0
                asset_minus += asset_closing
                asset_closing = 0.0

            # Manage negative assets (credit notes)
            if al["asset_original_value"] < 0:
                asset_add, asset_minus = -asset_minus, -asset_add
                depreciation_add, depreciation_minus = (
                    -depreciation_minus,
                    -depreciation_add,
                )

            # Format the data
            columns_by_expr_label = {
                "acquisition_date": al["asset_acquisition_date"]
                and format_date(self.env, al["asset_acquisition_date"])
                or "",
                # Characteristics
                "first_depreciation": al["asset_date"]
                and format_date(self.env, al["asset_date"])
                or "",
                "asset_method_percentage": asset_method_percentage,
                "duration_rate": asset_depreciation_rate,
                "assets_date_from": asset_opening,
                "assets_plus": asset_add,
                "assets_minus": asset_minus,
                "assets_date_to": asset_closing,
                "depre_date_from": depreciation_opening,
                "depre_plus": depreciation_add,
                "depre_minus": depreciation_minus,
                "depre_date_to": depreciation_closing,
                "balance": asset_closing - depreciation_closing,
            }

            lines.append((al["model_id"], al["asset_id"], columns_by_expr_label))
        return lines

    def _group_by_tax_profile(self, report, lines, options):
        """
        This function adds the grouping lines on top of each group of account.asset
        It iterates over the lines, change the line_id of each line to include the account.account.id and the
        account.asset.id.
        """
        if not lines:
            return lines

        line_vals_per_model_id = {}
        for line in lines:
            parent_model_id = line.get("model_id")

            model, res_id = report._get_model_info_from_id(line["id"])
            assert model == "account.asset"

            # replace the line['id'] to add the account.account.id
            line["id"] = report._build_line_id(
                [
                    (None, "account.asset", parent_model_id),
                    (None, "account.asset", res_id),
                ]
            )

            line_vals_per_model_id.setdefault(
                parent_model_id,
                {
                    # We don't assign a name to the line yet, so that we can batch the browsing of account.account objects
                    "id": report._build_line_id(
                        [(None, "account.asset", parent_model_id)]
                    ),
                    "columns": [],  # Filled later
                    "unfoldable": True,
                    "unfolded": options.get("unfold_all", False),
                    "level": 1,
                    "class": "o_account_asset_contrast",
                    # This value is stored here for convenience; it will be removed from the result
                    "group_lines": [],
                },
            )["group_lines"].append(line)
            _logger.info(f"{line}\n{line_vals_per_model_id}")

        # Generate the result
        idx_monetary_columns = [
            idx_col
            for idx_col, col in enumerate(options["columns"])
            if col["figure_type"] == "monetary"
        ]
        models = self.env["account.asset"].browse(line_vals_per_model_id.keys())
        rslt_lines = []
        for model in models:
            model_line_vals = line_vals_per_model_id[model.id]
            model_line_vals[
                "name"
            ] = f"{model.name}: {model.l10n_bg_method_percentage*100:.2f}%"

            rslt_lines.append(model_line_vals)

            group_totals = {column_index: 0 for column_index in idx_monetary_columns}
            group_lines = report._regroup_lines_by_name_prefix(
                options,
                model_line_vals.pop("group_lines"),
                "_report_expand_unfoldable_line_assets_report_prefix_group",
                model_line_vals["level"],
                parent_line_dict_id=model_line_vals["id"],
            )

            for model_sub_line in group_lines:
                # Add this line to the group totals
                for column_index in idx_monetary_columns:
                    group_totals[column_index] += model_sub_line["columns"][
                        column_index
                    ].get("no_format", 0)

                # Setup the parent and add the line to the result
                model_sub_line["parent_id"] = model_line_vals["id"]
                rslt_lines.append(model_sub_line)

            # Add totals (columns) to the account line
            for column_index in range(len(options["columns"])):
                tot_val = group_totals.get(column_index)
                if tot_val is None:
                    model_line_vals["columns"].append({})
                else:
                    model_line_vals["columns"].append(
                        {
                            "name": report.format_value(
                                options,
                                tot_val,
                                figure_type="monetary",
                                format_params={"currency_id": self.env.company.currency_id.id},
                            ),
                            "no_format": tot_val,
                        }
                    )

        return rslt_lines

    def _query_values(self, options, prefix_to_match=None, forced_model_id=None):
        "Get the data from the database"

        self.env["account.asset"].check_access_rights("read")

        if options.get("multi_company", False):
            company_ids = tuple(self.env.companies.ids)
        else:
            company_ids = tuple(self.env.company.ids)

        query_params = {
            "date_to": options["date"]["date_to"],
            "date_from": options["date"]["date_from"],
            "company_ids": company_ids,
        }

        prefix_query = ""
        if prefix_to_match:
            prefix_query = "AND asset.name ILIKE %(prefix_to_match)s"
            query_params["prefix_to_match"] = f"{prefix_to_match}%"

        models_query = ""
        if forced_model_id:
            models_query = "AND asset.l10n_bg_tax_model_id = %(forced_model_id)s"
            query_params["forced_model_id"] = forced_model_id

        sql = f"""
                SELECT asset.id AS asset_id,
                       asset.parent_id AS parent_id,
                       asset.name AS asset_name,
                       asset.original_value AS asset_original_value,
                       asset.currency_id AS asset_currency_id,
                       COALESCE(asset.salvage_value, 0) as asset_salvage_value,
                       MIN(tax_board.line_date) AS asset_date,
                       asset.disposal_date AS asset_disposal_date,
                       asset.acquisition_date AS asset_acquisition_date,
                       asset.method AS asset_method,
                       asset.method_number AS asset_method_number,
                       asset.method_period AS asset_method_period,
                       asset.l10n_bg_method_percentage AS asset_method_percentage,
                       asset.method_progress_factor AS asset_method_progress_factor,
                       asset.state AS asset_state,
                       asset.l10n_bg_tax_model_id AS model_id,
                       COALESCE(SUM(tax_board.value) FILTER (WHERE tax_board.line_date < %(date_from)s), 0) + COALESCE(asset.already_depreciated_amount_import, 0) AS depreciated_before,
                       COALESCE(SUM(tax_board.value) FILTER (WHERE tax_board.line_date BETWEEN %(date_from)s AND %(date_to)s), 0) AS depreciated_during,
                       COALESCE(SUM(tax_board.value) FILTER (WHERE tax_board.line_date BETWEEN %(date_from)s AND %(date_to)s), 0) AS asset_disposal_value
                  FROM account_asset AS asset
             LEFT JOIN account_asset AS tax_model ON tax_model.id = asset.l10n_bg_tax_model_id
             LEFT JOIN bg_account_asset_depreciation_board AS tax_board ON tax_board.asset_id = asset.id
                 WHERE asset.company_id in %(company_ids)s
                   AND asset.l10n_bg_method_percentage <> 0.0
                   AND (asset.acquisition_date <= %(date_to)s OR tax_board.line_date <= %(date_to)s)
                   AND (asset.disposal_date >= %(date_from)s OR asset.disposal_date IS NULL)
                   AND asset.state not in ('model', 'draft', 'cancelled')
                   AND asset.active = 't'
                   {prefix_query}
                   {models_query}
              GROUP BY asset.l10n_bg_tax_model_id, tax_model.name, asset.id
              ORDER BY tax_model.name, asset.acquisition_date;
            """
        # _logger.info(f"SQL: {sql}\n {query_params}")
        self._cr.execute(sql, query_params)
        results = self._cr.dictfetchall()
        return results

    def _report_expand_unfoldable_line_assets_report_prefix_group(
        self,
        line_dict_id,
        groupby,
        options,
        progress,
        offset,
        unfold_all_batch_data=None,
    ):
        matched_prefix = self.env[
            "account.report"
        ]._get_prefix_groups_matched_prefix_from_line_id(line_dict_id)
        report = self.env["account.report"].browse(options["report_id"])

        lines, _totals_by_column_group = self._generate_report_lines_without_grouping(
            report,
            options,
            prefix_to_match=matched_prefix,
            parent_id=line_dict_id,
            forced_model_id=self.env["account.report"]._get_res_id_from_line_id(
                line_dict_id, "account.asset"
            ),
        )

        lines = report._regroup_lines_by_name_prefix(
            options,
            lines,
            "_report_expand_unfoldable_line_assets_report_prefix_group",
            len(matched_prefix),
            matched_prefix=matched_prefix,
            parent_line_dict_id=line_dict_id,
        )

        return {
            "lines": lines,
            "offset_increment": len(lines),
            "has_more": False,
        }

    def _custom_line_postprocessor(self, report, options, lines):
        for line in lines:
            for column in line["columns"]:
                if "no_format" in column and column["no_format"] == 0:
                    column_class = column.get("class") or ""
                    column["class"] = column_class + " o_asset_blank_if_zero_value"
        return lines


class AssetsReport(models.Model):
    _inherit = "account.report"

    def _get_caret_option_view_map(self):
        view_map = super()._get_caret_option_view_map()
        view_map["account.asset.line"] = "account_asset.view_account_asset_expense_form"
        return view_map
