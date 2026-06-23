# -*- coding: utf-8 -*-

from odoo import models, fields, api, Command
from odoo.exceptions import ValidationError


class IqamaRenewalWizard(models.TransientModel):
    _name = 'iqama.renewal.wizard'
    _description = 'Iqama Renewal Wizard'

    employee_ids = fields.Many2many('sa.employee', string='Employees')
    new_expiry_date = fields.Date(string='New Expiry Date', required=True)

    @api.model
    def default_get(self, field_names):
        res = super().default_get(field_names)
        active_ids = self.env.context.get('active_ids', [])
        if active_ids:
            expats = self.env['sa.employee'].browse(active_ids).filtered(
                lambda e: e.nationality_type == 'expat'
            )
            if not expats:
                raise ValidationError('Please select at least one expat employee.')
            res['employee_ids'] = [Command.set(expats.ids)]
        return res

    def action_renew(self):
        self.employee_ids.write({'iqama_expiry': self.new_expiry_date})
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Iqama Renewed',
                'message': f'{len(self.employee_ids)} employee(s) updated to {self.new_expiry_date}.',
                'type': 'success',
                'sticky': False,
            }
        }
