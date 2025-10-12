from odoo import http
from odoo.http import request

class PosSalespersonController(http.Controller):

    @http.route('/pos/get_salespersons', type='json', auth='public')
    def get_salespersons(self, pos_config_id=None):
        if not pos_config_id:
            return []

        config = request.env['pos.config'].sudo().browse(int(pos_config_id))
        if not config or not config.active_salesperson_feature:
            return []

        employees = config.allowed_sale_person_ids.sudo()
        return [
            {
                'id': emp.id,
                'name': emp.name,
                'image_128' : emp.image_128,
            }
            for emp in employees
        ]