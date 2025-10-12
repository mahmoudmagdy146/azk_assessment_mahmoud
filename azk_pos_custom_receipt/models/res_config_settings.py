from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    """Used to add new fields to the settings"""
    _inherit = "res.config.settings"

    use_customized_receipt = fields.Boolean(
        related='pos_config_id.use_customized_receipt',
        string="Configure Customized Receipt",
        readonly=False
    )
    show_customer_details = fields.Boolean(
        related='pos_config_id.show_customer_details',
        string="Configure Customer Details",
        readonly=False
    )

    receipt_logo = fields.Binary(
        related='pos_config_id.receipt_logo',
        string="Receipt Logo",
                                 readonly=False)
    receipt_logo_filename = fields.Char(
        related='pos_config_id.receipt_logo_filename',
        string="Receipt Logo Filename",
                                        readonly=False)

    company_name = fields.Html(
        related='pos_config_id.company_name',
        string='Company Name',
        readonly=False)

    company_details = fields.Html(
        related='pos_config_id.company_details',
        string='Company Details',
        readonly=False)
