# -*- coding: utf-8 -*-

import base64
import hashlib
import io
import json
import logging
import uuid as uuid_lib
import requests
import qrcode
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from odoo import models, fields, api
from odoo.exceptions import ValidationError, UserError

_logger = logging.getLogger(__name__)


def _tlv_encode(tag, value):
    value_bytes = value.encode('utf-8')
    return bytes([tag, len(value_bytes)]) + value_bytes


class SaInvoiceLine(models.Model):
    _name = 'sa.invoice.line'
    _description = 'Invoice Line'

    invoice_id  = fields.Many2one('sa.invoice', ondelete='cascade')
    description = fields.Char(string='Description', required=True)
    quantity    = fields.Float(string='Qty', default=1.0)
    unit_price  = fields.Float(string='Unit Price')
    subtotal    = fields.Float(string='Subtotal', compute='_compute_subtotal', store=True)

    @api.depends('quantity', 'unit_price')
    def _compute_subtotal(self):
        for line in self:
            line.subtotal = line.quantity * line.unit_price


class SaInvoice(models.Model):
    _name = 'sa.invoice'
    _description = 'ZATCA Invoice'
    _order = 'invoice_date desc'

    name         = fields.Char(string='Invoice Number', readonly=True, default='New', copy=False)
    uuid         = fields.Char(string='UUID', readonly=True, default=lambda self: str(uuid_lib.uuid4()), copy=False)

    invoice_type = fields.Selection([
        ('standard',   'Standard Invoice (B2B)'),
        ('simplified', 'Simplified Invoice (B2C)'),
    ], string='Invoice Type', required=True, default='simplified')

    invoice_date = fields.Date(string='Invoice Date', required=True, default=fields.Date.today)

    # Seller
    seller_name    = fields.Char(string='Seller Name', required=True)
    seller_vat     = fields.Char(string='Seller VAT Number', required=True)
    seller_cr      = fields.Char(string='Commercial Registration (CR)')
    seller_address = fields.Char(string='Seller Address')

    # Buyer
    buyer_name    = fields.Char(string='Buyer Name', required=True)
    buyer_vat     = fields.Char(string='Buyer VAT Number')
    buyer_address = fields.Char(string='Buyer Address')

    # Lines
    line_ids = fields.One2many('sa.invoice.line', 'invoice_id', string='Invoice Lines')

    # Totals
    amount_untaxed = fields.Float(string='Subtotal',        compute='_compute_totals', store=True)
    amount_vat     = fields.Float(string='VAT (15%)',       compute='_compute_totals', store=True)
    amount_total   = fields.Float(string='Total (incl. VAT)', compute='_compute_totals', store=True)

    # ZATCA
    zatca_status   = fields.Selection([
        ('not_submitted', 'Not Submitted'),
        ('submitted',     'Submitted'),
        ('cleared',       'Cleared'),
        ('reported',      'Reported'),
        ('rejected',      'Rejected'),
    ], default='not_submitted', string='ZATCA Status', readonly=True)

    zatca_response    = fields.Text(string='ZATCA Response', readonly=True)
    zatca_clearance   = fields.Char(string='Clearance Status', readonly=True)
    ubl_xml           = fields.Text(string='UBL XML', readonly=True)
    invoice_hash      = fields.Char(string='Invoice Hash', readonly=True)

    # QR
    qr_code_image = fields.Binary(string='QR Code', compute='_compute_qr', store=True)

    state = fields.Selection([
        ('draft',     'Draft'),
        ('confirmed', 'Confirmed'),
        ('cancelled', 'Cancelled'),
    ], default='draft', required=True)

    notes = fields.Text(string='Notes')

    @api.depends('line_ids.subtotal')
    def _compute_totals(self):
        for inv in self:
            subtotal = sum(inv.line_ids.mapped('subtotal'))
            inv.amount_untaxed = subtotal
            inv.amount_vat     = round(subtotal * 0.15, 2)
            inv.amount_total   = inv.amount_untaxed + inv.amount_vat

    @api.depends('seller_name', 'seller_vat', 'invoice_date', 'amount_total', 'amount_vat')
    def _compute_qr(self):
        for inv in self:
            if not (inv.seller_name and inv.seller_vat and inv.invoice_date):
                inv.qr_code_image = False
                continue
            dt_str = str(inv.invoice_date) + 'T00:00:00Z'
            tlv = (
                _tlv_encode(1, inv.seller_name) +
                _tlv_encode(2, inv.seller_vat) +
                _tlv_encode(3, dt_str) +
                _tlv_encode(4, '%.2f' % inv.amount_total) +
                _tlv_encode(5, '%.2f' % inv.amount_vat)
            )
            qr_data = base64.b64encode(tlv).decode('utf-8')
            qr = qrcode.QRCode(version=1, box_size=6, border=2)
            qr.add_data(qr_data)
            qr.make(fit=True)
            img = qr.make_image(fill_color='black', back_color='white')
            buffer = io.BytesIO()
            img.save(buffer, format='PNG')
            inv.qr_code_image = base64.b64encode(buffer.getvalue())

    @api.constrains('seller_vat')
    def _check_seller_vat(self):
        for inv in self:
            if inv.seller_vat and (len(inv.seller_vat) != 15 or not inv.seller_vat.startswith('3')):
                raise ValidationError('VAT number must be 15 digits and start with 3.')

    # ─────────── UBL XML ───────────

    def _generate_ubl_xml(self):
        self.ensure_one()
        type_code = '0200000' if self.invoice_type == 'simplified' else '0100000'
        profile   = 'reporting:1.0' if self.invoice_type == 'simplified' else 'standard:1.0'

        lines_xml = ''
        for i, line in enumerate(self.line_ids, 1):
            line_vat = round(line.subtotal * 0.15, 2)
            lines_xml += f"""
    <cac:InvoiceLine>
        <cbc:ID>{i}</cbc:ID>
        <cbc:InvoicedQuantity unitCode="PCE">{line.quantity:.2f}</cbc:InvoicedQuantity>
        <cbc:LineExtensionAmount currencyID="SAR">{line.subtotal:.2f}</cbc:LineExtensionAmount>
        <cac:TaxTotal>
            <cbc:TaxAmount currencyID="SAR">{line_vat:.2f}</cbc:TaxAmount>
            <cac:TaxSubtotal>
                <cbc:TaxableAmount currencyID="SAR">{line.subtotal:.2f}</cbc:TaxableAmount>
                <cbc:TaxAmount currencyID="SAR">{line_vat:.2f}</cbc:TaxAmount>
                <cac:TaxCategory>
                    <cbc:ID>S</cbc:ID>
                    <cbc:Percent>15</cbc:Percent>
                    <cac:TaxScheme><cbc:ID>VAT</cbc:ID></cac:TaxScheme>
                </cac:TaxCategory>
            </cac:TaxSubtotal>
        </cac:TaxTotal>
        <cac:Item><cbc:Name>{line.description}</cbc:Name></cac:Item>
        <cac:Price>
            <cbc:PriceAmount currencyID="SAR">{line.unit_price:.2f}</cbc:PriceAmount>
        </cac:Price>
    </cac:InvoiceLine>"""

        xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Invoice xmlns="urn:oasis:names:specification:ubl:schema:xsd:Invoice-2"
         xmlns:cac="urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2"
         xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
         xmlns:ext="urn:oasis:names:specification:ubl:schema:xsd:CommonExtensionComponents-2">
    <ext:UBLExtensions>
        <ext:UBLExtension>
            <ext:ExtensionURI>urn:oasis:names:specification:ubl:dsig:enveloped:xades</ext:ExtensionURI>
            <ext:ExtensionContent/>
        </ext:UBLExtension>
    </ext:UBLExtensions>
    <cbc:ProfileID>{profile}</cbc:ProfileID>
    <cbc:ID>{self.name}</cbc:ID>
    <cbc:UUID>{self.uuid}</cbc:UUID>
    <cbc:IssueDate>{self.invoice_date}</cbc:IssueDate>
    <cbc:IssueTime>00:00:00</cbc:IssueTime>
    <cbc:InvoiceTypeCode name="{type_code}">388</cbc:InvoiceTypeCode>
    <cbc:DocumentCurrencyCode>SAR</cbc:DocumentCurrencyCode>
    <cbc:TaxCurrencyCode>SAR</cbc:TaxCurrencyCode>
    <cac:AccountingSupplierParty>
        <cac:Party>
            <cac:PartyIdentification>
                <cbc:ID schemeID="CRN">{self.seller_cr or ''}</cbc:ID>
            </cac:PartyIdentification>
            <cac:PostalAddress>
                <cbc:StreetName>{self.seller_address or ''}</cbc:StreetName>
                <cbc:CityName>Riyadh</cbc:CityName>
                <cac:Country><cbc:IdentificationCode>SA</cbc:IdentificationCode></cac:Country>
            </cac:PostalAddress>
            <cac:PartyTaxScheme>
                <cbc:CompanyID>{self.seller_vat}</cbc:CompanyID>
                <cac:TaxScheme><cbc:ID>VAT</cbc:ID></cac:TaxScheme>
            </cac:PartyTaxScheme>
            <cac:PartyLegalEntity>
                <cbc:RegistrationName>{self.seller_name}</cbc:RegistrationName>
            </cac:PartyLegalEntity>
        </cac:Party>
    </cac:AccountingSupplierParty>
    <cac:AccountingCustomerParty>
        <cac:Party>
            <cac:PostalAddress>
                <cbc:StreetName>{self.buyer_address or ''}</cbc:StreetName>
                <cbc:CityName>Riyadh</cbc:CityName>
                <cac:Country><cbc:IdentificationCode>SA</cbc:IdentificationCode></cac:Country>
            </cac:PostalAddress>
            <cac:PartyTaxScheme>
                <cbc:CompanyID>{self.buyer_vat or ''}</cbc:CompanyID>
                <cac:TaxScheme><cbc:ID>VAT</cbc:ID></cac:TaxScheme>
            </cac:PartyTaxScheme>
            <cac:PartyLegalEntity>
                <cbc:RegistrationName>{self.buyer_name}</cbc:RegistrationName>
            </cac:PartyLegalEntity>
        </cac:Party>
    </cac:AccountingCustomerParty>
    <cac:TaxTotal>
        <cbc:TaxAmount currencyID="SAR">{self.amount_vat:.2f}</cbc:TaxAmount>
        <cac:TaxSubtotal>
            <cbc:TaxableAmount currencyID="SAR">{self.amount_untaxed:.2f}</cbc:TaxableAmount>
            <cbc:TaxAmount currencyID="SAR">{self.amount_vat:.2f}</cbc:TaxAmount>
            <cac:TaxCategory>
                <cbc:ID>S</cbc:ID>
                <cbc:Percent>15</cbc:Percent>
                <cac:TaxScheme><cbc:ID>VAT</cbc:ID></cac:TaxScheme>
            </cac:TaxCategory>
        </cac:TaxSubtotal>
    </cac:TaxTotal>
    <cac:LegalMonetaryTotal>
        <cbc:LineExtensionAmount currencyID="SAR">{self.amount_untaxed:.2f}</cbc:LineExtensionAmount>
        <cbc:TaxExclusiveAmount currencyID="SAR">{self.amount_untaxed:.2f}</cbc:TaxExclusiveAmount>
        <cbc:TaxInclusiveAmount currencyID="SAR">{self.amount_total:.2f}</cbc:TaxInclusiveAmount>
        <cbc:PayableAmount currencyID="SAR">{self.amount_total:.2f}</cbc:PayableAmount>
    </cac:LegalMonetaryTotal>
    {lines_xml}
</Invoice>"""
        return xml

    # ─────────── Signing ───────────

    def _sign_invoice(self, xml_content, private_key_pem):
        xml_bytes     = xml_content.encode('utf-8')
        digest        = hashlib.sha256(xml_bytes).digest()
        digest_b64    = base64.b64encode(digest).decode()

        private_key   = serialization.load_pem_private_key(private_key_pem.encode(), password=None)
        signature     = private_key.sign(xml_bytes, ec.ECDSA(hashes.SHA256()))
        signature_b64 = base64.b64encode(signature).decode()

        return digest_b64, signature_b64

    # ─────────── ZATCA Submission ───────────

    def action_submit_to_zatca(self):
        self.ensure_one()
        if self.state != 'confirmed':
            raise UserError('Only confirmed invoices can be submitted to ZATCA.')

        config = self.env['zatca.config'].get_config()
        if config.onboard_status != 'compliant':
            raise UserError('Complete ZATCA onboarding in ZATCA → Settings first.')

        # Generate XML
        xml = self._generate_ubl_xml()

        # Sign
        digest_b64, signature_b64 = self._sign_invoice(xml, config.private_key)

        # Hash for submission
        xml_bytes     = xml.encode('utf-8')
        invoice_hash  = base64.b64encode(hashlib.sha256(xml_bytes).digest()).decode()
        invoice_b64   = base64.b64encode(xml_bytes).decode()

        payload = {
            'invoiceHash': invoice_hash,
            'uuid':        self.uuid,
            'invoice':     invoice_b64,
        }

        auth     = base64.b64encode(f'{config.csid}:{config.csid_secret}'.encode()).decode()
        endpoint = '/invoices/reporting/single' if self.invoice_type == 'simplified' else '/invoices/clearance/single'

        try:
            response = requests.post(
                f'{config._base_url}{endpoint}',
                json=payload,
                headers={
                    'Authorization': f'Basic {auth}',
                    'Accept-Version': 'V2',
                    'Content-Type':   'application/json',
                },
                timeout=30,
            )
        except requests.exceptions.RequestException as e:
            raise UserError(f'Could not reach ZATCA: {e}')

        response_data = response.json() if response.content else {}

        if response.status_code in (200, 202):
            status = 'reported' if self.invoice_type == 'simplified' else 'cleared'
            clearance_status = response_data.get('clearanceStatus') or response_data.get('reportingStatus', 'PASSED')
        else:
            status = 'rejected'
            clearance_status = 'REJECTED'
            _logger.warning('ZATCA rejected invoice %s: %s', self.name, response.text)

        self.write({
            'zatca_status':   status,
            'zatca_response': json.dumps(response_data, indent=2),
            'zatca_clearance': clearance_status,
            'ubl_xml':         xml,
            'invoice_hash':    invoice_hash,
        })

        msg_type = 'success' if status != 'rejected' else 'danger'
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title':   f'ZATCA: {clearance_status}',
                'message': f'Invoice {self.name} — {status.upper()}',
                'type':    msg_type,
                'sticky':  True,
            }
        }

    # ─────────── Workflow ───────────

    def action_confirm(self):
        for inv in self:
            if not inv.line_ids:
                raise ValidationError('Cannot confirm an invoice with no lines.')
            inv.name  = self.env['ir.sequence'].next_by_code('sa.invoice') or 'New'
            inv.state = 'confirmed'

    def action_cancel(self):
        self.write({'state': 'cancelled'})

    def action_reset(self):
        self.write({'state': 'draft'})
