from odoo import models, fields

class PosConfig(models.Model):
    _inherit = 'pos.config'

    active_salesperson_feature = fields.Boolean(
        string="Configure Salesperson in Orderlines"
    )

    allowed_sale_person_ids = fields.Many2many(
        'pos.sale.person',
        string="Allowed POS Salesperson"
    )
