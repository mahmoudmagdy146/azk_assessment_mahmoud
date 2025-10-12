# GenAI Usage Log

**Tool Used:** ChatGPT (GPT-5)  
**Purpose:** Assist in scaffolding, structuring, and documenting modules for the Azkatech Odoo Developer Technical Assessment.

---

## 🧠 Overview
I used ChatGPT to accelerate the setup of the module structure, improve documentation clarity, and verify Odoo-specific coding standards.  
All final implementations, testing, and debugging were done manually.

---

## 🧩 Example 1 — Generating Module Skeleton

**Date:** 2025-10-12  
**Prompt:**
```
Generate a minimal Odoo 17 module skeleton named azk_pos_salesperson that extends pos.order.line with a salesperson Many2one, adds pos.sale.person model and pos.config fields. Include __manifest__.py, models, and sample views XML.
```

**ChatGPT Output (excerpt):**
```python
class POSSalePerson(models.Model):
    _name = 'pos.sale.person'
    _description = 'POS Sale Person'

    name = fields.Char('Salesperson Name', required=True)
    phone_number = fields.Char('Phone Number')
    related_employee_id = fields.Many2one('hr.employee', 'Related Employee')
```

**My Adaptations:**
- Added `allowed_sale_person_ids` Many2many field in `pos.config`.
- Adjusted naming conventions to follow Odoo standards.
- Linked the model to POS orderlines and implemented popup logic manually.

---

## 🧩 Example 2 — JS Popup for Salesperson Selection

**Date:** 2025-10-13  
**Prompt:**
```
Write an OWL-based POS popup component for Odoo 17 that displays a list of salespersons and returns the selected salesperson to the order line.
```

**ChatGPT Output (excerpt):**
```javascript
const { Component } = owl;
export class SalespersonPopup extends Component {
    setup() {
        this.salespersons = useService('pos').db.get_salespersons();
    }
}
```

**My Adaptations:**
- Adjusted to use `Registries.Component` and extended Odoo’s `AbstractAwaitablePopup`.
- Added proper event handling (`confirm`, `cancel`).
- Integrated popup with the `Orderline` model.
- Verified compatibility with offline cache.

---

## 🧩 Example 3 — Custom Receipt QWeb Template

**Date:** 2025-10-13  
**Prompt:**
```
Create a QWeb template for a customized POS receipt that adds company logo, custom header text, and salesperson name under each line if configured.
```

**ChatGPT Output (excerpt):**
```xml
<t t-if="pos.config.use_customized_receipt">
    <img t-att-src="pos.config.logo"/>
    <t t-foreach="orderlines" t-as="line">
        <t t-if="line.salesperson_id">
            <div><strong>Salesperson:</strong> <t t-esc="line.salesperson_id[1]"/></div>
        </t>
    </t>
</t>
```

**My Adaptations:**
- Integrated logic conditionally (`t-if="pos.config.use_customized_receipt"`).
- Improved styling to match default Odoo receipt.
- Added fallback to original Odoo template when disabled.

---

## ⚙️ Summary of GenAI Contributions

| Area | Assistance | Manual Adjustments |
|------|-------------|--------------------|
| Module scaffolding | ✅ Generated initial file structure | Customized manifests & naming |
| ORM Models | ✅ Suggested base fields | Added relations, constraints |
| POS JS logic | ✅ Drafted popup logic | Implemented events & UI in Odoo context |
| QWeb receipts | ✅ Drafted sample | Integrated with configuration |
| Documentation | ✅ Structured README & Testing steps | Localized and clarified wording |

---

## ✅ Review Notes
- All generated snippets were manually reviewed, debugged, and adapted for Odoo 17.
- No direct copy-paste code was used without modification.
- The final code was tested thoroughly in local Odoo environment.

---

**Author:** Mahmoud Magdy  
**Date:** 2025-10-12  
**Project:** Azkatech Odoo Developer Technical Assessment
