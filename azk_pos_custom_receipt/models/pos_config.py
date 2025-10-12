from odoo import fields, models


class PosConfig(models.Model):
    """Used to add new fields to the settings"""
    _inherit = "pos.config"

    use_customized_receipt = fields.Boolean(
        string="Configure Customized Receipt",
    )
    show_customer_details = fields.Boolean(
        string="Configure Customer Details",
    )
    receipt_logo = fields.Binary("Receipt Logo")
    receipt_logo_filename = fields.Char("Receipt Logo Filename")

    company_name = fields.Html(
        string='Company Name',
        required=False)

    company_details = fields.Html(
        string='Company Details',
        required=False)