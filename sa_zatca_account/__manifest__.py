# -*- coding: utf-8 -*-
{
    'name': 'SA ZATCA — Account Integration',
    'version': '17.0.1.0.0',
    'summary': 'Extends Odoo native invoicing with ZATCA Phase 1 & 2 compliance',
    'description': """
        Extends Odoo's built-in account.move (invoicing) with ZATCA compliance.
        Features:
        - ZATCA QR code (Phase 1 TLV) on native invoices
        - UBL 2.1 XML generation (Phase 2)
        - ECDSA digital signature (Phase 2)
        - Fatoora API submission — clearance (B2B) & reporting (B2C)
        - Status badge: Cleared / Reported / Rejected
    """,
    'author': 'Hashem Al-Ahdal',
    'website': 'https://github.com/hshoom17',
    'category': 'Accounting',
    'license': 'LGPL-3',
    'depends': ['account', 'sa_zatca'],
    'data': [
        'security/ir.model.access.csv',
        'views/account_move_views.xml',
    ],
    'installable': True,
    'application': False,
}
