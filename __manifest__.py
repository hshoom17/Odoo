# -*- coding: utf-8 -*-
{
    'name': 'SA HR Module',
    'version': '17.0.1.0.0',
    'summary': 'Saudi Arabia HR management with Saudization (Nitaqat) tracking',
    'description': """
        Employee management module tailored for the Saudi labor market.
        Features:
        - Employee records with Saudi / Expat classification
        - Iqama number and expiry tracking with automatic status (Valid / Expiring / Expired)
        - Visual alerts for expired and expiring Iqamas
        - Department Saudization (Nitaqat) percentage computed automatically
        - Activate / Suspend employees from the form
        - Bulk deactivation of employees with expired Iqamas
    """,
    'author': 'Hashem Al-Ahdal',
    'website': 'https://github.com/hashemalahdal',
    'category': 'Human Resources',
    'license': 'LGPL-3',
    'depends': ['base'],
    'data': [
        'security/ir.model.access.csv',
        'data/data.xml',
        'views/department_views.xml',
        'views/employee_views.xml',
        'views/menus.xml',
    ],
    'installable': True,
    'application': True,
}
