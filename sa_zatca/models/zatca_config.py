# -*- coding: utf-8 -*-

import base64
import requests
import logging
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.x509.oid import NameOID

from odoo import models, fields, api
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

ZATCA_SANDBOX_URL = 'https://gw-fatoora.zatca.gov.sa/e-invoicing/developer-portal'
ZATCA_PROD_URL    = 'https://gw-fatoora.zatca.gov.sa/e-invoicing/core'


class ZatcaConfig(models.Model):
    _name = 'zatca.config'
    _description = 'ZATCA Configuration'

    name         = fields.Char(default='ZATCA Settings', required=True)
    environment  = fields.Selection([
        ('sandbox',    'Sandbox (Testing)'),
        ('production', 'Production'),
    ], default='sandbox', required=True)

    # Company info
    company_name = fields.Char(string='Company Name', required=True)
    seller_vat   = fields.Char(string='VAT Number', required=True)
    seller_cr    = fields.Char(string='CR Number')
    city         = fields.Char(string='City', default='Riyadh')

    # Onboarding
    otp          = fields.Char(string='OTP from ZATCA Portal',
                               help='Get from fatoora.zatca.gov.sa → New Device. Enter before clicking Onboard.')

    # Generated / received credentials
    private_key  = fields.Text(string='Private Key (PEM)', readonly=True)
    csr          = fields.Text(string='CSR (Base64)', readonly=True)
    certificate  = fields.Text(string='Certificate', readonly=True)
    csid         = fields.Char(string='CSID', readonly=True)
    csid_secret  = fields.Char(string='CSID Secret', readonly=True)

    onboard_status = fields.Selection([
        ('pending',   'Pending'),
        ('csr_ready', 'CSR Generated'),
        ('compliant', 'Compliant'),
    ], default='pending', readonly=True)

    @property
    def _base_url(self):
        return ZATCA_PROD_URL if self.environment == 'production' else ZATCA_SANDBOX_URL

    def action_generate_csr(self):
        self.ensure_one()
        if not self.company_name or not self.seller_vat:
            raise UserError('Company name and VAT number are required.')

        private_key = ec.generate_private_key(ec.SECP256K1())

        private_key_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        ).decode()

        csr = (
            x509.CertificateSigningRequestBuilder()
            .subject_name(x509.Name([
                x509.NameAttribute(NameOID.COMMON_NAME,             self.company_name),
                x509.NameAttribute(NameOID.ORGANIZATION_NAME,       self.company_name),
                x509.NameAttribute(NameOID.ORGANIZATIONAL_UNIT_NAME, 'VAT-' + self.seller_vat),
                x509.NameAttribute(NameOID.COUNTRY_NAME,            'SA'),
                x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME,  self.city or 'Riyadh'),
                x509.NameAttribute(NameOID.LOCALITY_NAME,           self.city or 'Riyadh'),
                x509.NameAttribute(NameOID.SERIAL_NUMBER,           '1-' + (self.seller_cr or self.seller_vat)),
            ]))
            .sign(private_key, hashes.SHA256())
        )

        self.write({
            'private_key':    private_key_pem,
            'csr':            base64.b64encode(csr.public_bytes(serialization.Encoding.DER)).decode(),
            'onboard_status': 'csr_ready',
        })

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title':   'CSR Generated',
                'message': 'Key pair and CSR are ready. Enter the OTP from ZATCA portal then click Onboard.',
                'type':    'success',
            }
        }

    def action_onboard(self):
        self.ensure_one()
        if not self.csr:
            raise UserError('Generate the CSR first.')
        if not self.otp:
            raise UserError('Enter the OTP from the ZATCA Fatoora portal first.')

        try:
            response = requests.post(
                f'{self._base_url}/compliance',
                json={'csr': self.csr},
                headers={
                    'OTP':            self.otp,
                    'Accept-Version': 'V2',
                    'Content-Type':   'application/json',
                },
                timeout=30,
            )
        except requests.exceptions.RequestException as e:
            raise UserError(f'Could not reach ZATCA: {e}')

        if response.status_code not in (200, 202):
            raise UserError(f'ZATCA returned error {response.status_code}:\n{response.text}')

        data = response.json()
        self.write({
            'csid':           data.get('binarySecurityToken', ''),
            'csid_secret':    data.get('secret', ''),
            'certificate':    data.get('binarySecurityToken', ''),
            'onboard_status': 'compliant',
            'otp':            False,
        })

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title':   'Onboarding Successful',
                'message': 'CSID received from ZATCA. You can now submit invoices.',
                'type':    'success',
            }
        }

    @api.model
    def get_config(self):
        config = self.search([], limit=1)
        if not config:
            raise UserError('ZATCA is not configured. Go to ZATCA → Settings.')
        return config
