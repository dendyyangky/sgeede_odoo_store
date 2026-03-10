{
    'name': 'SGEEDE Note Template',
    'version': '17.0.1.0.0',
    'description': """
    
    Adds reusable note templates to Sales Orders and Purchase Orders.

    Create and manage a library of predefined note templates for Terms & Conditions.
    Select a template directly from the Sales Order or Purchase Order form.
    Notes are automatically populated and can still be edited freely after selection.
    Templates can be scoped to Sales only, Purchase only, or both.

    """,

    'summary': 'Reusable note templates for Sales Orders and Purchase Orders',
    'author': 'SGEEDE',
    'website': 'https://www.sgeede.com',
    'license': 'LGPL-3',
    'category': 'Sales',
    'depends': [
        'base', 'sale', 'purchase', 'sale_management'
    ],
    'data': [
        'security/ir.model.access.csv',

        'data/sgeede_note_template_data.xml',
        
        'views/sale_order_view.xml',
        'views/purchase_order_view.xml',
        'views/sgeede_note_template_views.xml'

    ],
    'images' : ['static/description/banner.gif'],
}