# -*- coding: utf-8 -*-
{
    'name': 'SA ZATCA Invoice',
    'version': '17.0.1.0.0',
    'summary': 'ZATCA Phase 1 & 2 compliant e-invoicing for Saudi Arabia',
    'description': """
        E-invoicing module compliant with ZATCA Phase 1 & 2 requirements.
        Features:
        - Standard and Simplified invoice types (B2B / B2C)
        - 15% VAT calculation
        - ZATCA Phase 1 QR code (TLV encoded)
        - ZATCA Phase 2: UBL 2.1 XML generation
        - ZATCA Phase 2: ECDSA digital signature
        - ZATCA Phase 2: Fatoora API integration (clearance & reporting)
        - Professional PDF invoice layout
        - Invoice workflow: Draft → Confirmed → ZATCA Submitted
    """,
    'author': 'Hashem Al-Ahdal',
    'website': 'https://github.com/hashemalahdal',
    'category': 'Accounting',
    'license': 'LGPL-3',
    'depends': ['base'],
    'data': [
        'security/ir.model.access.csv',
        'views/invoice_views.xml',
        'views/report_invoice.xml',
        'views/zatca_config_views.xml',
        'views/menus.xml',
    ],
    'installable': True,
    'application': True,
}
