from odoo import fields, models, api


class POSSalePerson(models.Model):
    _name = 'pos.sale.person'
    _description = 'POS Sale Person'

    name = fields.Char(string='Salesperson Name', required=True)
    phone_number = fields.Char("Phone Number")
    image_128 = fields.Image("Logo", max_width=128, max_height=128)
    related_employee_id = fields.Many2one('hr.employee', string='Related Employee')
