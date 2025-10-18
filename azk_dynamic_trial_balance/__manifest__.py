{
    "name": "Azk Dynamic Trial Balance",
    "version": "1.0",
    "summary": "Dynamic Trial Balance report with filters, PDF and XLSX export",
    "description": "Provides a wizard to generate a dynamic trial balance with export to PDF/XLSX. Suitable for Odoo 17.",
    "category": "Accounting",
    "author": "Mahmoud Magdy",
    "depends": ["account"],
    "data": [
        "security/ir.model.access.csv",
        "views/trial_balance_wizard_view.xml",
        "views/trial_balance_menu.xml",

        "report/trial_balance_report_templates.xml"
    ],
    "installable": True,
    "application": False
}
