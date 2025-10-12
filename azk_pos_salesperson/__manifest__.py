{
    'name': 'Azk POS Salesperson Assignment',
    'version': '18.0.0.0',
    'author': 'Mahmoud Magdy',
        'depends': ['point_of_sale','hr'],
    'data': [
        'security/ir.model.access.csv',
        'views/pos_config_views.xml',
        'views/pos_order_view.xml',
        'views/pos_sale_person_view.xml',

        
    ],     
    'assets': {
        'point_of_sale._assets_pos': [        
            'azk_pos_salesperson/static/src/js/order_line_pos.js',
            'azk_pos_salesperson/static/src/xml/select_salesperson_button.xml',
            'azk_pos_salesperson/static/src/xml/orderline_salesperson.xml',
            'azk_pos_salesperson/static/src/js/select_salesperson_button.js',
            'azk_pos_salesperson/static/src/css/salesperson_template.css',

        ],
    },
    'installable': True,
    'application': True,
}
