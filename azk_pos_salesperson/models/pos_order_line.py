from odoo import fields, models,api

class PosOrderLine(models.Model):

    _inherit = 'pos.order.line'

    pos_salesperson_id = fields.Many2one('pos.sale.person', string='Salesperson', store=True, readonly=True)



class PosOrder(models.Model):
    _inherit = 'pos.order'
    pos_salesperson_id = fields.Many2one('pos.sale.person', string='Salesperson', store=True, readonly=True)

    def _process_order(self, order, existing_order):
        pos_order_id = super()._process_order(order, existing_order)
        pos_order = self.browse(pos_order_id)
        ui_lines = order.get("lines", [])
        backend_lines = pos_order.lines.sorted(key=lambda l: l.id)

        for index, line_data in enumerate(ui_lines):
            if isinstance(line_data, list) and len(line_data) > 2:
                line_vals = line_data[2]
                extra = line_vals.get("extra_data", {})
                pos_salesperson_id = extra.get("pos_salesperson_id")

                if index < len(backend_lines) and pos_salesperson_id:
                    backend_lines[index].pos_salesperson_id = pos_salesperson_id

        return pos_order_id
