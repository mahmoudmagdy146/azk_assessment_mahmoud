import { PosOrder } from "@point_of_sale/app/models/pos_order";
import { patch } from "@web/core/utils/patch";
// Simple HTML → text cleaner (frontend-safe)
function htmlToText(html) {
    const div = document.createElement('div');
    div.innerHTML = html || '';
    return div.textContent.trim();
}
//Patching PosOrder
patch(PosOrder.prototype, {
//    supering export_for_printing method to add custom data
    export_for_printing(baseUrl, headerData) {
        const result = super.export_for_printing(...arguments);
        if (this.partner_id){
            result.headerData.customer_name = this.partner_id.name;
            result.headerData.customer_address = this.partner_id.contact_address;
        }
        result.headerData.company_name_clean = htmlToText(this.config.company_name);
        result.headerData.company_details_clean = htmlToText(this.config.company_details);
        // collect unique salesperson names from all lines
        const salespersons = [];
        for (const line of this.get_orderlines()) {
            if (line.extra_data.salesperson_name && !salespersons.includes(line.extra_data.salesperson_name)) {
                salespersons.push(line.extra_data.salesperson_name);
            }
        }
        result.headerData.salespersons = salespersons;
        return result;
    },
});