# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class TrialBalanceWizard(models.TransientModel):
    _name = 'trial.balance.wizard'
    _description = 'Dynamic Trial Balance Wizard'

    # Date Range
    date_from = fields.Date(
        string='Date From',
        required=True,
        default=lambda self: fields.Date.context_today(self)
    )
    date_to = fields.Date(
        string='Date To',
        required=True,
        default=lambda self: fields.Date.context_today(self)
    )

    # Company
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company
    )

    # Options Section
    posted_entries_only = fields.Boolean(
        string='Posted Entries Only',
        default=True,
        help='When checked, only posted entries are included. Uncheck to include draft entries.'
    )

    hierarchy_and_subtotals = fields.Boolean(
        string='Hierarchy and Subtotals',
        default=False,
        help='Export report with Account Groups (same as Odoo behavior)'
    )

    hierarchy_only_parents = fields.Boolean(
        string='Hierarchy Only Parents',
        default=False,
        help='Show only parent levels up to selected level'
    )

    account_level_up_to = fields.Selection(
        [
            ('1', 'Level 1'),
            ('2', 'Level 2'),
            ('3', 'Level 3'),
            ('4', 'Level 4'),
            ('5', 'Level 5'),
        ],
        string='Account Level Up To',
        help='Select hierarchy level from 1 to 5'
    )

    # Filters Section
    accounts_filter = fields.Char(
        string='Accounts',
        help='Specify the account prefix to view only matching accounts. '
             'If no prefix is entered, all accounts will be displayed. '
             'Examples: "100" or "100, 200, 400"'
    )

    journal_ids = fields.Many2many(
        'account.journal',
        string='Journals',
        help='Select specific journals to include in the report, '
             'or leave empty to include all journals.'
    )

    analytic_account_ids = fields.Many2many(
        'account.analytic.account',
        string='Analytic Accounts',
        help='Select specific analytic accounts to include in the report, '
             'or leave empty to include all.'
    )

    skip_zero_balance = fields.Boolean(
        string='Skip Zero Balance',
        default=True,
        help='Select this option to hide accounts that have neither an initial '
             'balance nor any transactions in this report.'
    )

    show_amount_currency = fields.Boolean(
        string='Show Amount Currency',
        default=False,
        help='Enable this option to group the report by Account, followed by '
             'Amount Currency. This will show the sum of the Amount Currency '
             'for each account in its respective currency. Essentially, this '
             'option provides a breakdown of account balances by the transaction '
             'currency used.'
    )

    @api.onchange('hierarchy_and_subtotals')
    def _onchange_hierarchy_and_subtotals(self):
        """Reset child options when hierarchy is disabled"""
        if not self.hierarchy_and_subtotals:
            self.hierarchy_only_parents = False
            self.account_level_up_to = False

    @api.onchange('hierarchy_only_parents')
    def _onchange_hierarchy_only_parents(self):
        """Reset level when hierarchy only parents is disabled"""
        if not self.hierarchy_only_parents:
            self.account_level_up_to = False

    @api.onchange('company_id')
    def _onchange_company_id(self):
        """Filter journals and analytic accounts by company"""
        if self.company_id:
            if self.journal_ids:
                self.journal_ids = self.journal_ids.filtered(
                    lambda j: j.company_id == self.company_id
                )
            if self.analytic_account_ids:
                self.analytic_account_ids = self.analytic_account_ids.filtered(
                    lambda a: not a.company_id or a.company_id == self.company_id
                )

        return {
            'domain': {
                'journal_ids': [('company_id', '=', self.company_id.id)],
                'analytic_account_ids': [
                    '|',
                    ('company_id', '=', False),
                    ('company_id', '=', self.company_id.id)
                ],
            }
        }

    def _prepare_report_options(self):
        """
        Convert wizard values to account.report options format.
        This matches Odoo's enterprise report structure.
        """
        self.ensure_one()

        # Base options structure
        options = {
            'date': {
                'mode': 'range',
                'date_from': fields.Date.to_string(self.date_from),
                'date_to': fields.Date.to_string(self.date_to),
                'filter': 'custom',
            },
            'all_entries': not self.posted_entries_only,
            'company_id': self.company_id.id,
            'companies': [{'id': self.company_id.id, 'name': self.company_id.name, 'selected': True}],
            'multi_company': [{'id': self.company_id.id, 'name': self.company_id.name, 'selected': True}],
        }

        # Custom options for our report
        options.update({
            'include_unposted': not self.posted_entries_only,
            'hierarchy_enabled': self.hierarchy_and_subtotals,
            'hierarchy_only_parents': self.hierarchy_only_parents,
            'hierarchy_level': int(self.account_level_up_to) if self.account_level_up_to else 0,
            'skip_zero_balance': self.skip_zero_balance,
            'show_currency': self.show_amount_currency,
            'account_codes': self.accounts_filter or '',
        })

        # Journal filter
        if self.journal_ids:
            options['journals'] = [
                {
                    'id': journal.id,
                    'name': journal.name,
                    'code': journal.code,
                    'type': journal.type,
                    'selected': True,
                }
                for journal in self.journal_ids
            ]

        # Analytic filter
        if self.analytic_account_ids:
            options['analytic_accounts'] = [
                {
                    'id': analytic.id,
                    'name': analytic.name,
                    'selected': True,
                }
                for analytic in self.analytic_account_ids
            ]

        return options

    def action_preview(self):
        """
        Open the enterprise-style report with configured options.
        This mimics the native Odoo Trial Balance behavior.
        """
        self.ensure_one()

        # Get the report
        report = self.env.ref('azk_dynamic_trial_balance.dynamic_trial_balance_report')

        if not report:
            raise UserError(_('Dynamic Trial Balance report not found. Please check module installation.'))

        # Prepare options
        options = self._prepare_report_options()

        # Store options in context for the report action
        action = report.open_report(options)

        # Update action to include our custom options
        action['context'] = dict(action.get('context', {}), **{
            'dynamic_trial_balance_options': options,
        })

        return action

    def action_export_pdf(self):
        """Export report to PDF"""
        self.ensure_one()

        # Get report and prepare options
        report = self.env.ref('azk_dynamic_trial_balance.dynamic_trial_balance_report')
        options = self._prepare_report_options()

        # Generate lines using the handler
        handler = report.custom_handler_model_id.model

        lines = self.env[handler]._dynamic_lines(report, options, {})

        # Prepare PDF data
        data = {
            'company': self.company_id,
            'date_from': self.date_from,
            'date_to': self.date_to,
            'lines': lines,
            'options': options,
        }

        # Render PDF
        return self.env.ref('azk_dynamic_trial_balance.action_report_dynamic_trial_balance_pdf').report_action(
            self, data=data
        )

    def action_export_xlsx(self):
        """Export report to XLSX with wizard options"""
        self.ensure_one()
        options = self._prepare_report_options()
        report = self.env.ref('azk_dynamic_trial_balance.dynamic_trial_balance_report')
        return report.export_to_xlsx(options)