# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.tools.misc import format_date
from collections import defaultdict
import json


class DynamicTrialBalanceCustomHandler(models.AbstractModel):
    _name = 'account.dynamic.trial.balance.report.handler'
    _inherit = 'account.report.custom.handler'
    _description = 'Dynamic Trial Balance Report Custom Handler'

    def _custom_options_initializer(self, report, options, previous_options=None):
        """Initialize custom options from wizard or previous state"""
        super()._custom_options_initializer(report, options, previous_options)

        # Get wizard options if coming from wizard
        wizard_options = self.env.context.get('dynamic_trial_balance_options', {})

        # Initialize custom options with wizard values or defaults
        options['include_unposted'] = (
                wizard_options.get('include_unposted') or
                previous_options and previous_options.get('include_unposted', False) or
                False
        )
        options['hierarchy_enabled'] = (
                wizard_options.get('hierarchy_enabled') or
                previous_options and previous_options.get('hierarchy_enabled', False) or
                False
        )
        options['hierarchy_only_parents'] = (
                wizard_options.get('hierarchy_only_parents') or
                previous_options and previous_options.get('hierarchy_only_parents', False) or
                False
        )
        options['hierarchy_level'] = (
                wizard_options.get('hierarchy_level') or
                previous_options and previous_options.get('hierarchy_level', 0) or
                0
        )
        options['show_currency'] = (
                wizard_options.get('show_currency') or
                previous_options and previous_options.get('show_currency', False) or
                False
        )
        options['skip_zero_balance'] = (
            wizard_options.get('skip_zero_balance') if 'skip_zero_balance' in wizard_options
            else previous_options and previous_options.get('skip_zero_balance', True) if previous_options
            else True
        )
        options['account_codes'] = (
                wizard_options.get('account_codes') or
                previous_options and previous_options.get('account_codes', '') or
                ''
        )

        # Add custom buttons to report interface
        if not options.get('buttons'):
            options['buttons'] = []

        options['buttons'].extend([
            {
                'name': _('Include Unposted'),
                'sequence': 30,
                'action': 'action_toggle_unposted',
                'always_show': True,
            },
            {
                'name': _('Skip Zero'),
                'sequence': 31,
                'action': 'action_toggle_skip_zero',
                'always_show': True,
            },
            {
                'name': _('Hierarchy'),
                'sequence': 32,
                'action': 'action_toggle_hierarchy',
                'always_show': True,
            },
            {
                'name': _('Show Currency'),
                'sequence': 33,
                'action': 'action_toggle_currency',
                'always_show': True,
            },
        ])

    def action_toggle_unposted(self, options):
        """Toggle include unposted entries"""
        options['include_unposted'] = not options.get('include_unposted', False)
        options['all_entries'] = options['include_unposted']
        return {'type': 'ir_actions_account_report_reload'}

    def action_toggle_skip_zero(self, options):
        """Toggle skip zero balance"""
        options['skip_zero_balance'] = not options.get('skip_zero_balance', True)
        return {'type': 'ir_actions_account_report_reload'}

    def action_toggle_hierarchy(self, options):
        """Toggle hierarchy display"""
        options['hierarchy_enabled'] = not options.get('hierarchy_enabled', False)
        return {'type': 'ir_actions_account_report_reload'}

    def action_toggle_currency(self, options):
        """Toggle currency display"""
        options['show_currency'] = not options.get('show_currency', False)
        return {'type': 'ir_actions_account_report_reload'}

    def _dynamic_lines(self, report, options, all_column_groups_expression_totals, warnings=None):
        """
        Generate report lines using optimized SQL queries.
        This is the main entry point called by account.report.
        """
        lines = self._get_trial_balance_lines(report, options)
        return lines

    def _get_trial_balance_lines(self, report, options):
        """Generate trial balance lines with all filters applied"""

        # Extract date range
        date_from = fields.Date.from_string(options['date']['date_from'])
        date_to = fields.Date.from_string(options['date']['date_to'])
        company_id = options.get('company_id') or self.env.company.id
        company = self.env['res.company'].browse(company_id)

        # Get fiscal year start
        fiscal_dates = company.compute_fiscalyear_dates(date_from)
        fy_start_date = fiscal_dates['date_from']

        # Build SQL query
        query_data = self._build_sql_query(
            date_from, date_to, fy_start_date, company_id, options
        )

        # Execute query
        self.env.cr.execute(query_data['sql'], query_data['params'])
        results = self.env.cr.dictfetchall()

        # Process results into lines
        lines = self._process_results_to_lines(results, options, report)

        return lines

    def _build_sql_query(self, date_from, date_to, fy_start_date, company_id, options):
        """Build optimized SQL query with all filters"""

        show_currency = options.get('show_currency', False)
        include_unposted = options.get('include_unposted', False)
        account_codes = options.get('account_codes', '')

        # Base WHERE conditions
        where_conditions = ["aml.company_id = %s"]
        params = [company_id]

        # Posted/Unposted filter
        if include_unposted:
            where_conditions.append("am.state IN ('posted', 'draft')")
        else:
            where_conditions.append("am.state = 'posted'")

        # Journal filter
        if options.get('journals'):
            journal_ids = [j['id'] for j in options['journals'] if j.get('selected')]
            if journal_ids:
                where_conditions.append(f"aml.journal_id IN %s")
                params.append(tuple(journal_ids))

        # Account code filter
        if account_codes:
            code_list = [code.strip() for code in account_codes.split(',') if code.strip()]
            if code_list:
                code_conditions = []
                for code in code_list:
                    code_conditions.append("aa.code LIKE %s")
                    params.append(f"{code}%")
                where_conditions.append(f"({' OR '.join(code_conditions)})")

        # Analytic filter
        if options.get('analytic_accounts'):
            analytic_ids = [a['id'] for a in options['analytic_accounts'] if a.get('selected')]
            if analytic_ids:
                # Handle analytic_distribution JSON field
                where_conditions.append(
                    "EXISTS (SELECT 1 FROM jsonb_each(aml.analytic_distribution) WHERE key::int IN %s)"
                )
                params.append(tuple(analytic_ids))

        where_clause = " AND ".join(where_conditions)

        # Currency columns
        currency_select = ""
        currency_group = ""
        if show_currency:
            currency_select = """
                , aml.currency_id
                , rc.name as currency_name
            """
            currency_group = ", aml.currency_id, rc.name"

        # Main SQL with CTEs for performance
        sql = f"""
            WITH 
            initial_balance AS (
                SELECT 
                    aml.account_id
                    {currency_select}
                    , SUM(aml.debit) as initial_debit
                    , SUM(aml.credit) as initial_credit
                    , SUM(aml.balance) as initial_balance
                    {", SUM(aml.amount_currency) as initial_amount_currency" if show_currency else ""}
                FROM account_move_line aml
                JOIN account_move am ON aml.move_id = am.id
                JOIN account_account aa ON aml.account_id = aa.id
                {f"LEFT JOIN res_currency rc ON aml.currency_id = rc.id" if show_currency else ""}
                WHERE aml.date >= %s
                  AND aml.date < %s
                  AND {where_clause}
                  AND aml.display_type NOT IN ('line_section', 'line_note')
                GROUP BY aml.account_id {currency_group}
            ),
            period_balance AS (
                SELECT 
                    aml.account_id
                    {currency_select}
                    , SUM(aml.debit) as period_debit
                    , SUM(aml.credit) as period_credit
                    , SUM(aml.balance) as period_balance
                    {", SUM(aml.amount_currency) as period_amount_currency" if show_currency else ""}
                FROM account_move_line aml
                JOIN account_move am ON aml.move_id = am.id
                JOIN account_account aa ON aml.account_id = aa.id
                {f"LEFT JOIN res_currency rc ON aml.currency_id = rc.id" if show_currency else ""}
                WHERE aml.date >= %s
                  AND aml.date <= %s
                  AND {where_clause}
                  AND aml.display_type NOT IN ('line_section', 'line_note')
                GROUP BY aml.account_id {currency_group}
            )
            SELECT 
                aa.id as account_id
                , aa.code as account_code
                , aa.name as account_name
                , aa.account_type
                , ag.id as group_id
                , ag.name as group_name
                , ag.code_prefix_start as group_code
                {", COALESCE(ib.currency_id, pb.currency_id) as currency_id" if show_currency else ""}
                {", COALESCE(ib.currency_name, pb.currency_name) as currency_name" if show_currency else ""}
                , COALESCE(ib.initial_debit, 0) as initial_debit
                , COALESCE(ib.initial_credit, 0) as initial_credit
                , COALESCE(ib.initial_balance, 0) as initial_balance
                , COALESCE(pb.period_debit, 0) as period_debit
                , COALESCE(pb.period_credit, 0) as period_credit
                , COALESCE(pb.period_balance, 0) as period_balance
                , COALESCE(ib.initial_balance, 0) + COALESCE(pb.period_balance, 0) as ending_balance
                {", COALESCE(ib.initial_amount_currency, 0) as initial_amount_currency" if show_currency else ""}
                {", COALESCE(pb.period_amount_currency, 0) as period_amount_currency" if show_currency else ""}
                {", COALESCE(ib.initial_amount_currency, 0) + COALESCE(pb.period_amount_currency, 0) as ending_amount_currency" if show_currency else ""}
            FROM account_account aa
            LEFT JOIN account_group ag ON aa.group_id = ag.id
            LEFT JOIN initial_balance ib ON ib.account_id = aa.id {f"AND ib.currency_id = aa.currency_id" if show_currency else ""}
            LEFT JOIN period_balance pb ON pb.account_id = aa.id {f"AND pb.currency_id = aa.currency_id" if show_currency else ""}
            WHERE aa.company_id = %s
              AND (ib.initial_balance IS NOT NULL 
                   OR pb.period_balance IS NOT NULL)
            ORDER BY aa.code {", currency_name" if show_currency else ""}
        """

        # Parameters for CTEs
        all_params = [
            fy_start_date, date_from, *params,  # initial_balance CTE
            date_from, date_to, *params,  # period_balance CTE
            company_id,  # main query
        ]

        return {'sql': sql, 'params': all_params}

    def _process_results_to_lines(self, results, options, report):
        """Convert SQL results to report lines"""
        lines = []

        skip_zero = options.get('skip_zero_balance', True)
        hierarchy_enabled = options.get('hierarchy_enabled', False)
        hierarchy_level = options.get('hierarchy_level', 0)
        hierarchy_only_parents = options.get('hierarchy_only_parents', False)

        if hierarchy_enabled:
            lines = self._build_hierarchy_lines(results, options, report, hierarchy_level, hierarchy_only_parents)
        else:
            for result in results:
                # Skip zero balance if requested
                if skip_zero and result['ending_balance'] == 0 and result['initial_balance'] == 0:
                    continue

                line = self._build_account_line(result, options, report)
                lines.append(line)

        return lines

    def _build_account_line(self, result, options, report):
        """Build a single account line"""

        show_currency = options.get('show_currency', False)
        account_id = result['account_id']
        currency_id = result.get('currency_id') if show_currency else None

        # Build unique line ID
        line_id = f"account_{account_id}"
        if show_currency and currency_id:
            line_id += f"_cur_{currency_id}"

        # Format columns
        columns = [
            {'name': self._format_value(result['initial_debit'], report), 'no_format_name': result['initial_debit']},
            {'name': self._format_value(result['initial_credit'], report), 'no_format_name': result['initial_credit']},
            {'name': self._format_value(result['initial_balance'], report),
             'no_format_name': result['initial_balance']},
            {'name': self._format_value(result['period_debit'], report), 'no_format_name': result['period_debit']},
            {'name': self._format_value(result['period_credit'], report), 'no_format_name': result['period_credit']},
            {'name': self._format_value(result['period_balance'], report), 'no_format_name': result['period_balance']},
            {'name': self._format_value(result['ending_balance'], report), 'no_format_name': result['ending_balance']},
        ]

        # Add currency columns if enabled
        if show_currency:
            columns.extend([
                {'name': result.get('currency_name', ''), 'class': 'text'},
                {'name': self._format_value(result.get('ending_amount_currency', 0), report),
                 'no_format_name': result.get('ending_amount_currency', 0)},
            ])

        # Build line name with currency info
        line_name = f"{result['account_code']} {result['account_name']}"
        if show_currency and result.get('currency_name'):
            line_name += f" ({result['currency_name']})"

        return {
            'id': line_id,
            'name': line_name,
            'level': 2,
            'columns': columns,
            'unfoldable': False,
            'caret_options': 'account.account',
            'account_id': account_id,
        }

    def _build_hierarchy_lines(self, results, options, report, max_level, only_parents):
        """Build hierarchical lines with account groups"""
        lines = []
        groups = defaultdict(lambda: {
            'accounts': [],
            'initial_debit': 0,
            'initial_credit': 0,
            'initial_balance': 0,
            'period_debit': 0,
            'period_credit': 0,
            'period_balance': 0,
            'ending_balance': 0,
            'initial_amount_currency': 0,
            'period_amount_currency': 0,
            'ending_amount_currency': 0,
        })

        skip_zero = options.get('skip_zero_balance', True)

        # Group accounts
        for result in results:
            # Skip zero if requested
            if skip_zero and result['ending_balance'] == 0 and result['initial_balance'] == 0:
                continue

            group_id = result.get('group_id')
            if group_id:
                groups[group_id]['accounts'].append(result)
                groups[group_id]['group_name'] = result['group_name']
                groups[group_id]['group_code'] = result['group_code']

                # Aggregate
                for key in ['initial_debit', 'initial_credit', 'initial_balance',
                            'period_debit', 'period_credit', 'period_balance', 'ending_balance']:
                    groups[group_id][key] += result[key]

                if options.get('show_currency'):
                    for key in ['initial_amount_currency', 'period_amount_currency', 'ending_amount_currency']:
                        groups[group_id][key] += result.get(key, 0)
            else:
                # No group - add directly
                lines.append(self._build_account_line(result, options, report))

        # Build group lines
        for group_id, group_data in sorted(groups.items(), key=lambda x: x[1].get('group_code', '')):
            # Check hierarchy level
            if only_parents and max_level:
                # Get group level
                group = self.env['account.group'].browse(group_id)
                group_level = len(group.complete_code.split('/'))
                if group_level > max_level:
                    continue

            # Group header line
            group_line = {
                'id': f"group_{group_id}",
                'name': f"{group_data['group_code']} {group_data['group_name']}",
                'level': 1,
                'class': 'o_account_reports_level1',
                'columns': [
                    {'name': self._format_value(group_data['initial_debit'], report)},
                    {'name': self._format_value(group_data['initial_credit'], report)},
                    {'name': self._format_value(group_data['initial_balance'], report)},
                    {'name': self._format_value(group_data['period_debit'], report)},
                    {'name': self._format_value(group_data['period_credit'], report)},
                    {'name': self._format_value(group_data['period_balance'], report)},
                    {'name': self._format_value(group_data['ending_balance'], report)},
                ],
                'unfoldable': True,
                'unfolded': True,
            }

            if options.get('show_currency'):
                group_line['columns'].extend([
                    {'name': ''},
                    {'name': self._format_value(group_data['ending_amount_currency'], report)},
                ])

            lines.append(group_line)

            # Add account lines under group
            for account in sorted(group_data['accounts'], key=lambda x: x['account_code']):
                lines.append(self._build_account_line(account, options, report))

        return lines

    def _format_value(self, value, report):
        """Format monetary value for display"""
        if not value or value == 0:
            return ''
        return report.format_value(value)