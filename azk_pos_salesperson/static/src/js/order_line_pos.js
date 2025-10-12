// /** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { PosOrderline } from "@point_of_sale/app/models/pos_order_line";
import { Orderline } from "@point_of_sale/app/generic_components/orderline/orderline";
import { SelectionPopup } from "@point_of_sale/app/utils/input_popups/selection_popup";
import { rpc } from "@web/core/network/rpc";

patch(PosOrderline.prototype, {
    setup(vals) {
        super.setup(vals);
        if (!this.extra_data) {
            this.extra_data = {}; 
            debugger;
        }
    },

    setSalesperson(id, name, image) {
        this.extra_data.pos_salesperson_id = id;
        this.extra_data.salesperson_name = name;
        this.extra_data.salesperson_image = image || "";
    },

    serialize(options = {}) {
        const json = super.serialize(options);
        if (json) {
            json.pos_salesperson_id = this.extra_data.pos_salesperson_id;
        }
        return json;
    },


    getDisplayData() {
        const data = super.getDisplayData?.() || {};
        if (this.extra_data?.salesperson_name) {
            data.salesperson_name = this.extra_data.salesperson_name;
            data.salesperson_image = this.extra_data.salesperson_image;
        }
        data.id = String(this.id); 
        return data;
    },
});

patch(Orderline, {
    props: {
        ...Orderline.props,
        line: {
            ...Orderline.props.line,
            shape: {
                ...Orderline.props.line.shape,
                salesperson_name: { type: String, optional: true },
                salesperson_image: { type: String, optional: true },
                id: { type: [String, Number], optional: false }, 
            },
        },
    },
});

patch(Orderline.prototype, {
    removeSalesperson() {
        const order = this.env.services.pos.get_order();
        const orderline = order.get_orderlines().find(
            (line) => String(line.id) === String(this.props.line.id)
        );
        if (orderline?.setSalesperson) {
            orderline.setSalesperson(null, null, null);
        }
    },

    async showSalespersonPopup() {
        const configId = this.env.services.pos.config.id;

        const result = await rpc("/pos/get_salespersons", { pos_config_id: configId });

        if (!result || !result.length) {
            this.env.services.pos.notification.add("No salespersons configured for this POS.");
            return;
        }

        await this.env.services.pos.dialog.add(SelectionPopup, {
            title: "Select Salesperson",
            list: result.map((employee) => ({
                id: employee.id,
                label: employee.name,
                item: employee,
                imageUrl: employee.image_128 ? `data:image/png;base64,${employee.image_128}` : null,
            })),

            getPayload: (choice) => {
                const currentOrder = this.env.services.pos.get_order();
                const selectedLine = currentOrder.get_selected_orderline();
                if (selectedLine && choice?.id) {
                    selectedLine.setSalesperson(choice.id, choice.name,choice.image_128);
                }

                return choice;
            },
        });
    },
});
