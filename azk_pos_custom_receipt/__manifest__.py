{
    'name': "Azk POS Customized Receipt",
    "version": "18.0.1.0.0",
    "category": "Point of Sale",
    "summary": "Azk POS Customized Receipt",
    'author': 'Mahmoud Magdy',
    'depends': ['point_of_sale', 'sale'],
    'data': [
        'views/res_config_settings_views.xml',
        'views/pos_config_views.xml',
    ],
    'assets': {
        'point_of_sale._assets_pos': [
            'azk_pos_custom_receipt/static/src/xml/OrderReceipt.xml',
            'azk_pos_custom_receipt/static/src/js/PosOrder.js',
        ]
    },
    'license': 'LGPL-3',
    'installable': True,
    'application': False,
    'auto_install': False,
}
