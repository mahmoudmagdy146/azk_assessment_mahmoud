from odoo import api, fields, models, _
from odoo.exceptions import UserError
import io
import base64

class TrialBalanceWizard(models.TransientModel):
    _name = 'trial.balance.wizard'
    _description = 'Dynamic Trial Balance Wizard'

    date_from = fields.Date(string='Date From', required=True)
    date_to = fields.Date(string='Date To', required=True)
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)
    account_ids = fields.Many2many('account.account', string='Accounts (optional)')
    include_unposted = fields.Boolean(string='Include Unposted Entries', default=False)
    skip_zero_balance = fields.Boolean(string='Skip Zero Balance', default=False)
    generated_count = fields.Integer(string='Generated Lines', readonly=True)
    xlsx_file = fields.Binary('XLSX Report', readonly=True)
    xlsx_filename = fields.Char('XLSX Filename', readonly=True)

    def _get_domain(self):
        domain = [
            ('date', '>=', self.date_from),
            ('date', '<=', self.date_to),
            ('company_id', '=', self.company_id.id)
        ]
        if not self.include_unposted:
            domain.append(('move_id.state', '=', 'posted'))
        if self.account_ids:
            domain.append(('account_id', 'in', self.account_ids.ids))
        return domain

    def action_generate(self):
        self.ensure_one()
        TBLine = self.env['trial.balance.line']
        # Clear previous lines for this wizard date/company
        TBLine.clear_old([('date_from', '=', self.date_from), ('date_to', '=', self.date_to), ('company_id', '=', self.company_id.id)])
        # Aggregate using read_group
        domain = self._get_domain()
        groupby = ['account_id', 'currency_id', 'company_id']
        grouped = self.env['account.move.line'].read_group(domain, ['debit','credit','account_id','currency_id','company_id'], groupby)
        results = []
        for g in grouped:
            acc_id = g.get('account_id')[0] if g.get('account_id') else False
            cur_id = g.get('currency_id')[0] if g.get('currency_id') else False
            comp_id = g.get('company_id')[0] if g.get('company_id') else self.company_id.id
            debit = g.get('debit') or 0.0
            credit = g.get('credit') or 0.0
            balance = (debit - credit)
            if self.skip_zero_balance and abs(balance) < 0.0001:
                continue
            vals = {
                'account_id': acc_id,
                'company_id': comp_id,
                'debit': debit,
                'credit': credit,
                'balance': balance,
                'currency_id': cur_id,
                'date_from': self.date_from,
                'date_to': self.date_to,
            }
            results.append(vals)
        # create lines
        created = []
        for vals in results:
            created.append(TBLine.create(vals))
        self.generated_count = len(created)
        # return action to view lines
        action = self.env.ref('azk_dynamic_trial_balance.action_view_trial_balance_lines').read()[0]
        return action

    def action_xlsx(self):
        self.ensure_one()
        TBLine = self.env['trial.balance.line']
        lines = TBLine.search([('date_from', '=', self.date_from), ('date_to', '=', self.date_to), ('company_id', '=', self.company_id.id)], order='account_code asc')
        # build simple xlsx in memory
        try:
            import xlsxwriter
        except Exception:
            raise UserError(_('xlsxwriter is not installed on the server.'))
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        sheet = workbook.add_worksheet('Trial Balance')
        headers = ['Account Code', 'Account Name', 'Debit', 'Credit', 'Balance', 'Currency']
        for col, h in enumerate(headers):
            sheet.write(0, col, h)
        row = 1
        for ln in lines:
            sheet.write(row, 0, ln.account_code or '')
            sheet.write(row, 1, ln.account_name or '')
            sheet.write(row, 2, float(ln.debit or 0.0))
            sheet.write(row, 3, float(ln.credit or 0.0))
            sheet.write(row, 4, float(ln.balance or 0.0))
            sheet.write(row, 5, ln.currency_id.name or '')
            row += 1
        workbook.close()
        output.seek(0)
        data = output.read()
        self.xlsx_file = base64.b64encode(data)
        self.xlsx_filename = 'trial_balance_{}_{}.xlsx'.format(self.date_from, self.date_to)
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new'
        }
