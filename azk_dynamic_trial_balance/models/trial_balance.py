from odoo import api, fields, models

class TrialBalanceLine(models.Model):
    _name = 'trial.balance.line'
    _description = 'Trial Balance Line (generated)'

    account_id = fields.Many2one('account.account', string='Account', required=True, ondelete='cascade')
    account_code = fields.Char(related='account_id.code', string='Account Code', readonly=True)
    account_name = fields.Char(related='account_id.name', string='Account Name', readonly=True)
    company_id = fields.Many2one('res.company', string='Company')
    debit = fields.Monetary(string='Debit', currency_field='company_currency_id')
    credit = fields.Monetary(string='Credit', currency_field='company_currency_id')
    balance = fields.Monetary(string='Balance', currency_field='company_currency_id')
    currency_id = fields.Many2one('res.currency', string='Currency')
    company_currency_id = fields.Many2one('res.currency', related='company_id.currency_id', string='Company Currency', readonly=True)
    date_from = fields.Date(string='From')
    date_to = fields.Date(string='To')

    @api.model
    def clear_old(self, domain=None):
        domain = domain or []
        lines = self.search(domain)
        if lines:
            lines.unlink()
        return True
