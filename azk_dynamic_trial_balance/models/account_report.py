# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.tools.misc import format_date
from collections import defaultdict


class DynamicTrialBalanceCustomHandler(models.AbstractModel):
    _name = 'account.dynamic.trial.balance.report.handler'
    _inherit = 'account.report.custom.handler'
    _description = 'Dynamic Trial Balance Report Custom Handler'

    def _custom_options_initializer(self, report, options, previous_options=None):
        super()._custom_options_initializer(report, options, previous_options)
        wizard_options = self.env.context.get('dynamic_trial_balance_options', {})

        options['include_unposted'] = wizard_options.get('include_unposted') or (previous_options and previous_options.get('include_unposted', False)) or False
        options['hierarchy_enabled'] = wizard_options.get('hierarchy_enabled') or (previous_options and previous_options.get('hierarchy_enabled', False)) or False
        options['hierarchy_only_parents'] = wizard_options.get('hierarchy_only_parents') or (previous_options and previous_options.get('hierarchy_only_parents', False)) or False
        options['hierarchy_level'] = wizard_options.get('hierarchy_level') or (previous_options and previous_options.get('hierarchy_level', 0)) or 0
        options['show_currency'] = wizard_options.get('show_currency') or (previous_options and previous_options.get('show_currency', False)) or False
        options['skip_zero_balance'] = wizard_options.get('skip_zero_balance', True) if 'skip_zero_balance' in wizard_options else (previous_options and previous_options.get('skip_zero_balance', True)) if previous_options else True
        options['account_codes'] = wizard_options.get('account_codes') or (previous_options and previous_options.get('account_codes', '')) or ''

        if not options.get('buttons'):
            options['buttons'] = []

        options['buttons'].extend([
            {'name': _('Include Unposted'), 'sequence': 30, 'action': 'action_toggle_unposted', 'always_show': True},
            {'name': _('Skip Zero'), 'sequence': 31, 'action': 'action_toggle_skip_zero', 'always_show': True},
            {'name': _('Hierarchy'), 'sequence': 32, 'action': 'action_toggle_hierarchy', 'always_show': True},
            {'name': _('Show Currency'), 'sequence': 33, 'action': 'action_toggle_currency', 'always_show': True},
        ])

    def action_toggle_unposted(self, options):
        options['include_unposted'] = not options.get('include_unposted', False)
        options['all_entries'] = options['include_unposted']
        return {'type': 'ir_actions_account_report_reload'}

    def action_toggle_skip_zero(self, options):
        options['skip_zero_balance'] = not options.get('skip_zero_balance', True)
        return {'type': 'ir_actions_account_report_reload'}

    def action_toggle_hierarchy(self, options):
        options['hierarchy_enabled'] = not options.get('hierarchy_enabled', False)
        return {'type': 'ir_actions_account_report_reload'}

    def action_toggle_currency(self, options):
        options['show_currency'] = not options.get('show_currency', False)
        return {'type': 'ir_actions_account_report_reload'}

    def _dynamic_lines(self, report, options, all_column_groups_expression_totals, warnings=None):
        return self._get_trial_balance_lines(report, options)

    def _get_trial_balance_lines(self, report, options):
        query_data = self._build_sql_query(options)
        self.env.cr.execute(query_data['sql'], query_data['params'])
        results = self.env.cr.dictfetchall()
        return self._process_results_to_lines(results, options, report)

    def _build_sql_query(self, options):
        date_from = fields.Date.from_string(options['date']['date_from'])
        date_to = fields.Date.from_string(options['date']['date_to'])
        company_id = options.get('company_id') or self.env.company.id
        company = self.env['res.company'].browse(company_id)
        fy_start_date = company.compute_fiscalyear_dates(date_from)['date_from']

        where_conditions = ["aml.company_id = %s"]
        params = [company_id]

        if options.get('include_unposted'):
            where_conditions.append("am.state IN ('posted', 'draft')")
        else:
            where_conditions.append("am.state = 'posted'")

        if options.get('journals'):
            journal_ids = [j['id'] for j in options['journals'] if j.get('selected')]
            if journal_ids:
                where_conditions.append("aml.journal_id IN %s")
                params.append(tuple(journal_ids))

        if options.get('account_codes'):
            code_list = [code.strip() for code in options['account_codes'].split(',') if code.strip()]
            if code_list:
                code_conditions = []
                for code in code_list:
                    code_conditions.append("aa.code LIKE %s")
                    params.append(f"{code}%")
                where_conditions.append(f"({" OR ".join(code_conditions)})")

        if options.get('analytic_accounts'):
            analytic_ids = [a['id'] for a in options['analytic_accounts'] if a.get('selected')]
            if analytic_ids:
                where_conditions.append(
                    "EXISTS (SELECT 1 FROM jsonb_each(aml.analytic_distribution) WHERE key::int IN %s)"
                )
                params.append(tuple(analytic_ids))

        where_clause = " AND ".join(where_conditions)

        currency_select = ", aml.currency_id, rc.name as currency_name" if options.get('show_currency') else ""
        currency_group = ", aml.currency_id, rc.name" if options.get('show_currency') else ""
        currency_join = "LEFT JOIN res_currency rc ON aml.currency_id = rc.id" if options.get('show_currency') else ""
        currency_sum_initial = ", SUM(CASE WHEN aml.date < %s THEN aml.amount_currency ELSE 0 END) as initial_amount_currency" if options.get('show_currency') else ""
        currency_sum_period = ", SUM(CASE WHEN aml.date >= %s AND aml.date <= %s THEN aml.amount_currency ELSE 0 END) as period_amount_currency" if options.get('show_currency') else ""

        sql = f"""
            WITH all_moves_filtered AS (
                SELECT
                    aml.account_id,
                    aml.debit,
                    aml.credit,
                    aml.balance,
                    aml.amount_currency,
                    aml.date,
                    aml.currency_id
                FROM account_move_line aml
                JOIN account_move am ON aml.move_id = am.id
                JOIN account_account aa ON aml.account_id = aa.id
                WHERE {where_clause}
                  AND aml.display_type NOT IN ('line_section', 'line_note')
            ),
            initial_balance AS (
                SELECT
                    account_id
                    {currency_select}
                    , SUM(CASE WHEN date < %s THEN debit ELSE 0 END) as initial_debit
                    , SUM(CASE WHEN date < %s THEN credit ELSE 0 END) as initial_credit
                    , SUM(CASE WHEN date < %s THEN balance ELSE 0 END) as initial_balance
                    {currency_sum_initial}
                FROM all_moves_filtered
                {currency_join}
                GROUP BY account_id {currency_group}
            ),
            period_balance AS (
                SELECT
                    account_id
                    {currency_select}
                    , SUM(CASE WHEN date >= %s AND date <= %s THEN debit ELSE 0 END) as period_debit
                    , SUM(CASE WHEN date >= %s AND date <= %s THEN credit ELSE 0 END) as period_credit
                    , SUM(CASE WHEN date >= %s AND date <= %s THEN balance ELSE 0 END) as period_balance
                    {currency_sum_period}
                FROM all_moves_filtered
                {currency_join}
                GROUP BY account_id {currency_group}
            )
            SELECT
                aa.id as account_id,
                aa.code as account_code,
                aa.name as account_name,
                aa.account_type,
                ag.id as group_id,
                ag.name as group_name,
                ag.code_prefix_start as group_code,
                COALESCE(ib.currency_id, pb.currency_id) as currency_id,
                COALESCE(ib.currency_name, pb.currency_name) as currency_name,
                COALESCE(ib.initial_debit, 0) as initial_debit,
                COALESCE(ib.initial_credit, 0) as initial_credit,
                COALESCE(ib.initial_balance, 0) as initial_balance,
                COALESCE(pb.period_debit, 0) as period_debit,
                COALESCE(pb.period_credit, 0) as period_credit,
                COALESCE(pb.period_balance, 0) as period_balance,
                COALESCE(ib.initial_debit, 0) + COALESCE(pb.period_debit, 0) as ending_debit,
                COALESCE(ib.initial_credit, 0) + COALESCE(pb.period_credit, 0) as ending_credit,
                COALESCE(ib.initial_balance, 0) + COALESCE(pb.period_balance, 0) as ending_balance
                {", COALESCE(ib.initial_amount_currency, 0) as initial_amount_currency" if options.get('show_currency') else ''}
                {", COALESCE(pb.period_amount_currency, 0) as period_amount_currency" if options.get('show_currency') else ''}
                {", COALESCE(ib.initial_amount_currency, 0) + COALESCE(pb.period_amount_currency, 0) as ending_amount_currency" if options.get('show_currency') else ''}
            FROM account_account aa
            LEFT JOIN account_group ag ON aa.group_id = ag.id
            FULL OUTER JOIN initial_balance ib ON ib.account_id = aa.id {"AND ib.currency_id = aa.currency_id" if options.get('show_currency') else ''}
            FULL OUTER JOIN period_balance pb ON pb.account_id = aa.id {"AND pb.currency_id = aa.currency_id" if options.get('show_currency') else ''}
            WHERE aa.company_id = %s AND (ib.initial_balance IS NOT NULL OR pb.period_balance IS NOT NULL OR pb.period_debit != 0 OR pb.period_credit != 0)
            ORDER BY aa.code {'ASC, currency_name ASC' if options.get('show_currency') else 'ASC'}
        """

        all_params = [
            *params,  # for all_moves_filtered CTE
            fy_start_date, fy_start_date, fy_start_date, # for initial_balance CTE
            fy_start_date, # for initial_amount_currency
            date_from, date_to, date_from, date_to, date_from, date_to, # for period_balance CTE
            date_from, date_to, # for period_amount_currency
            company_id,  # for main query
        ]

        return {'sql': sql, 'params': all_params}

    def _process_results_to_lines(self, results, options, report):
        lines = []
        show_currency = options.get('show_currency', False)

        if show_currency:
            for result in results:
                if not self._should_skip_line(result, options):
                    lines.append(self._build_account_line(result, options, report))
        else:
            account_data = defaultdict(lambda: {
                'account_id': None, 'account_code': '', 'account_name': '',
                'initial_debit': 0, 'initial_credit': 0, 'initial_balance': 0,
                'period_debit': 0, 'period_credit': 0, 'period_balance': 0,
                'ending_debit': 0, 'ending_credit': 0, 'ending_balance': 0,
            })
            for result in results:
                acc_id = result['account_id']
                if not account_data[acc_id]['account_id']:
                    account_data[acc_id].update({
                        'account_id': result['account_id'], 'account_code': result['account_code'], 'account_name': result['account_name'],
                        'group_id': result.get('group_id'), 'group_name': result.get('group_name'), 'group_code': result.get('group_code'),
                    })
                for key in ['initial_debit', 'initial_credit', 'initial_balance', 'period_debit', 'period_credit', 'period_balance', 'ending_debit', 'ending_credit', 'ending_balance']:
                    account_data[acc_id][key] += result[key]

            if options.get('hierarchy_enabled'):
                lines = self._build_hierarchy_lines(list(account_data.values()), options, report)
            else:
                for acc_data in sorted(account_data.values(), key=lambda x: x['account_code']):
                    if not self._should_skip_line(acc_data, options):
                        lines.append(self._build_account_line(acc_data, options, report))
        return lines

    def _should_skip_line(self, result, options):
        if not options.get('skip_zero_balance', True):
            return False

        # Check if all balance and movement values are zero
        return (
            result['initial_balance'] == 0 and
            result['period_debit'] == 0 and
            result['period_credit'] == 0 and
            result['ending_balance'] == 0
        )

    def _build_account_line(self, result, options, report):
        line_id = f"account_{result['account_id']}"
        if options.get('show_currency') and result.get('currency_id'):
            line_id += f"_cur_{result['currency_id']}"

        columns = [
            {'name': self._format_value(result['initial_debit'], report), 'no_format': result['initial_debit']},
            {'name': self._format_value(result['initial_credit'], report), 'no_format': result['initial_credit']},
            {'name': self._format_value(result['initial_balance'], report), 'no_format': result['initial_balance']},
            {'name': self._format_value(result['period_debit'], report), 'no_format': result['period_debit']},
            {'name': self._format_value(result['period_credit'], report), 'no_format': result['period_credit']},
            {'name': self._format_value(result['period_balance'], report), 'no_format': result['period_balance']},
            {'name': self._format_value(result['ending_debit'], report), 'no_format': result['ending_debit']},
            {'name': self._format_value(result['ending_credit'], report), 'no_format': result['ending_credit']},
            {'name': self._format_value(result['ending_balance'], report), 'no_format': result['ending_balance']},
        ]
        if options.get('show_currency'):
            columns.append({'name': self._format_value(result['ending_amount_currency'], report, currency_id=result.get('currency_id')), 'no_format': result['ending_amount_currency']})

        line_name = f"{result['account_code']} {result['account_name']}"
        if options.get('show_currency') and result.get('currency_name'):
            line_name += f" [{result['currency_name']}]"

        return {
            'id': line_id, 'name': line_name, 'level': 2, 'columns': columns, 'unfoldable': False, 'unfolded': False, 'caret_options': 'account.account',
        }

    def _build_hierarchy_lines(self, results, options, report):
        lines = []
        max_level = int(options.get('hierarchy_level', 0))
        only_parents = options.get('hierarchy_only_parents', False)

        AccountGroup = self.env['account.group']
        grouped_accounts = defaultdict(list)
        group_totals = defaultdict(lambda: defaultdict(float))

        # Group accounts by their direct parent group
        for acc_data in sorted(results, key=lambda x: x['account_code']):
            group_id = acc_data.get('group_id')
            if group_id:
                grouped_accounts[group_id].append(acc_data)
                # Accumulate totals for the group
                for key in ['initial_debit', 'initial_credit', 'initial_balance', 'period_debit', 'period_credit', 'period_balance', 'ending_debit', 'ending_credit', 'ending_balance']:
                    group_totals[group_id][key] += acc_data[key]
                if options.get('show_currency'):
                    group_totals[group_id]['initial_amount_currency'] += acc_data.get('initial_amount_currency', 0)
                    group_totals[group_id]['period_amount_currency'] += acc_data.get('period_amount_currency', 0)
                    group_totals[group_id]['ending_amount_currency'] += acc_data.get('ending_amount_currency', 0)
            else:
                # Accounts without a group are added directly
                if not self._should_skip_line(acc_data, options):
                    lines.append(self._build_account_line(acc_data, options, report))

        # Build hierarchy
        account_groups = AccountGroup.search([('id', 'in', list(grouped_accounts.keys()))], order='code_prefix_start')
        for group in account_groups:
            group_level = group.level + 1 # Odoo group levels are 0-indexed, report levels are 1-indexed

            if only_parents and max_level > 0 and group_level > max_level:
                continue # Skip groups and their children if level exceeds max_level

            # Add group header
            group_line = self._build_group_line(group, group_totals[group.id], options, report)
            lines.append(group_line)

            # Add accounts under this group
            for acc_data in grouped_accounts[group.id]:
                if not self._should_skip_line(acc_data, options):
                    account_line = self._build_account_line(acc_data, options, report)
                    account_line['level'] = group_level + 1 # Account is one level deeper than its group
                    lines.append(account_line)

        return lines

    def _build_group_line(self, group, totals, options, report):
        columns = [
            {'name': self._format_value(totals['initial_debit'], report), 'no_format': totals['initial_debit']},
            {'name': self._format_value(totals['initial_credit'], report), 'no_format': totals['initial_credit']},
            {'name': self._format_value(totals['initial_balance'], report), 'no_format': totals['initial_balance']},
            {'name': self._format_value(totals['period_debit'], report), 'no_format': totals['period_debit']},
            {'name': self._format_value(totals['period_credit'], report), 'no_format': totals['period_credit']},
            {'name': self._format_value(totals['period_balance'], report), 'no_format': totals['period_balance']},
            {'name': self._format_value(totals['ending_debit'], report), 'no_format': totals['ending_debit']},
            {'name': self._format_value(totals['ending_credit'], report), 'no_format': totals['ending_credit']},
            {'name': self._format_value(totals['ending_balance'], report), 'no_format': totals['ending_balance']},
        ]
        if options.get('show_currency'):
            columns.append({'name': self._format_value(totals['ending_amount_currency'], report), 'no_format': totals['ending_amount_currency']})

        return {
            'id': f"group_{group.id}",
            'name': f"{group.code_prefix_start or ''} {group.name}",
            'level': group.level + 1,
            'columns': columns,
            'unfoldable': True,
            'unfolded': options.get('unfolded_lines') and f"group_{group.id}" in options['unfolded_lines'],
            'caret_options': 'account.group',
            'class': 'o_account_report_group_line',
        }

    def _format_value(self, value, report, currency_id=None):
        if not value:
            return ''
        currency = self.env['res.currency'].browse(currency_id) if currency_id else report.env.company.currency_id
        return report.format_value(value, currency=currency)

