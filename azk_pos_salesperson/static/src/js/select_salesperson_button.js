// /** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { PosStore } from "@point_of_sale/app/store/pos_store";
import { SelectionPopup } from "@point_of_sale/app/utils/input_popups/selection_popup";
import { rpc } from "@web/core/network/rpc";

patch(PosStore.prototype, {
    async showSalespersonPopup() {
        const configId = this.config.id;

        const result = await rpc("/pos/get_salespersons", { pos_config_id: configId });

        if (!result || !result.length) {
            this.notification.add("No salespersons configured for this POS.");
            return;
        }

        await this.dialog.add(SelectionPopup, {
            title: "Select Salesperson",
            list: result.map((employee) => ({
                id: employee.id,
                label: employee.name,
                item: employee,
                imageUrl: employee.image_128 ? `data:image/png;base64,${employee.image_128}` : null,
            })),
        
            getPayload: (choice) => {
                const currentOrder = this.get_order();
                const selectedLine = currentOrder.get_selected_orderline();
                const orderlines = currentOrder.get_orderlines();
                if (selectedLine && choice?.id) {
                    selectedLine.setSalesperson(choice.id, choice.name,choice.image_128);
                }
                if (!selectedLine && choice?.id) {
                    for (const line of orderlines) {
                        line.setSalesperson(choice.id, choice.name, choice.image_128);

                    }
                }

                return choice;
            },
        });
    },
});

