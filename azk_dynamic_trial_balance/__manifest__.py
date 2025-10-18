# -*- coding: utf-8 -*-
{
    "name": "Dynamic Trial Balance",
    "version": "18.0.1.0.0",
    "summary": "Enhanced Trial Balance with Enterprise Features",
    "description": """
Dynamic Trial Balance Report for Odoo 18 Enterprise
====================================================

Features:
---------
* Wizard-based configuration with all Exercise 2 options
* Enterprise-style report interface (same as native Odoo Trial Balance)
* SQL-optimized queries for performance
* Interactive web interface with real-time filtering
* Drill-down to journal entries

Options Available:
------------------
* Posted Entries Only / Include Unposted
* Hierarchy and Subtotals with Account Groups
* Hierarchy Level Selection (1-5)
* Account Code Multi-Prefix Filter
* Journal Filter
* Analytic Account Filter
* Skip Zero Balance
* Show Amount Currency with grouping

Columns:
--------
* Initial Balance: Debit, Credit, Balance
* Movement: Debit, Credit, Balance  
* Ending Balance

Export Formats:
--------------
* Preview: Interactive web view
* PDF: Professional report
* XLSX: Excel with structure

Technical:
----------
* Uses Odoo Enterprise account_reports framework
* SQL CTEs for optimal performance
* Supports multi-company
* Full multi-currency support
    """,
    "category": "Accounting",
    "author": "Mahmoud Magdy",
    "website": "https://github.com/yourusername/azk_dynamic_trial_balance",
    "license": "OPL-1",
    "depends": [
        "account_reports",  # Odoo Enterprise
        "account",
        "analytic",
    ],
    "data": [
        "security/ir.model.access.csv",
        "data/account_report_data.xml",
        "views/trial_balance_wizard_view.xml",
        "views/trial_balance_menu.xml",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
}