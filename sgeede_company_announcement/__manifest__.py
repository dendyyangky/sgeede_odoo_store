{
    'name': 'Internal Announcement Banner',
    'version': '19.0.1.0.0',
    'summary': 'Show company-wide announcements as a dismissible banner inside Odoo',
    'category': 'Tools',
    'author': 'SGEEDE',
    'website': 'https://www.sgeede.com',
    'license': 'LGPL-3',
    'depends': ['web', 'mail'],
    'images': ['static/description/banner.gif'],
    'data': [
        'security/ir.model.access.csv',
        'views/announcement_views.xml',
    ],
    'installable': True,
    'application': True,
    'assets': {
        'web.assets_backend': [
            'sgeede_company_announcement/static/src/components/announcement_banner/announcement_banner.js',
            'sgeede_company_announcement/static/src/components/announcement_banner/announcement_banner.xml',
            'sgeede_company_announcement/static/src/components/announcement_banner/announcement_banner.scss',
        ],
    },
}
