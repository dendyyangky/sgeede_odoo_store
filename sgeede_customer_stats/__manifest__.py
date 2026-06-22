{
    'name': 'Sale Customer Statistics',
    'version': '17.0.1.0.0',
    'category': 'Sales/Sales',
    'summary': 'Customer sales statistics on contact records',
    'description': """
Display quotation and sales order statistics on customer contact records.
    """,
    'author': 'SGEEDE',
    'website': 'https://www.sgeede.com',
    'license': 'LGPL-3',
    'depends': [
        'contacts',
        'sale',
        'sale_management',
    ],
    'data': [
        'views/res_partner_views.xml',
    ],
    'images': ['static/description/banner.gif'],
    'installable': True,
    'application': False,
    'auto_install': False,
}
