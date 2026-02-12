{
    'name': 'SGEEDE Base',
    'version': '19.0.1.0.0',
    'category': 'Customizations',
    'summary': 'SGEEDE Modifications V19',
    'description': """
SGEEDE Base
===========================

This module contains custom features that are modified by SGEEDE.
""",
    'author': 'SGEEDE',
    'website': 'https://www.sgeede.com', 
    'depends': [
        'base', 'hr', 'hr_holidays', 'hr_work_entry', 'documents_hr', 'account', 'accountant',
    ],
    'data': [

        # Security
        'security/ir.model.access.csv',
        'security/security.xml',
        'security/ir_rule.xml',

        # Data
        'data/sgeede_hr_leave_type_data.xml',
        'data/sgeede_config_leave_data.xml',
        'data/sgeede_sequence.xml',

        # views
        'views/res_config_settings_views.xml',
        'views/hr_employee_views.xml',
        'views/hr_leave_allocation_views.xml',
        'views/hr_leave_type_views.xml',
        'views/sgeede_payment_distribution_views.xml',

        #wizards
        'wizards/sgeede_writeoff_payment_distribution_wizard_views.xml',

    ],
    'assets': {
        
    },
    'license': 'LGPL-3',
}
