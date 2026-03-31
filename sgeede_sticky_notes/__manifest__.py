{
    'name': 'Sticky Notes for Sales, Purchase, and Invoicing',
    'version': '19.0.1.0.0',
    'description': """
    Adds color-coded sticky notes directly to Sales, Purchase, and Invoicing.

    Notes appear above the form header — instantly visible
    without scrolling to the chatter. Each note has a color,
    author, and timestamp. Close a note to archive it;
    Notes do not carry over when duplicating an order.
    """,

    'summary': 'Color-coded sticky notes on Sales, Purchase and Invoicing',
    'author': 'SGEEDE',
    'website': 'https://www.sgeede.com',
    'license': 'LGPL-3',
    'category': 'Productivity',
    'depends': [
        'base',
        'sale_management',
        'purchase',
        'account',
    ],
    'data': [
        'security/ir.model.access.csv',
        
        'views/account_move_views.xml',
        'views/sale_order_views.xml',
        'views/purchase_order_views.xml',

    ],
    'assets': {
        'web.assets_backend': [
            'sgeede_sticky_notes/static/src/js/sgeede_sticky_notes_widget.js',
            'sgeede_sticky_notes/static/src/xml/sgeede_sticky_notes.xml',
            'sgeede_sticky_notes/static/src/scss/sgeede_sticky_notes.scss',
        ],
    },
    'images': ['static/description/banner.gif'],
    'installable': True,
    'auto_install': False,
    'application': False,
}