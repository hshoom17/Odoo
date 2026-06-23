# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import UserError
from datetime import date


class EosCalculatorWizard(models.TransientModel):
    _name = 'eos.calculator.wizard'
    _description = 'End of Service Calculator'

    employee_id = fields.Many2one('sa.employee', string='Employee', required=True)
    last_working_day = fields.Date(string='Last Working Day', required=True,
                                   default=fields.Date.today)
    termination_reason = fields.Selection([
        ('resignation',   'Resignation'),
        ('termination',   'Termination by Employer'),
        ('mutual',        'Mutual Agreement'),
        ('death',         'Death'),
        ('retirement',    'Retirement'),
    ], string='Reason', required=True, default='resignation')

    # Read-only result fields
    years_of_service = fields.Float(string='Years of Service', readonly=True, digits=(16, 2))
    full_gratuity = fields.Float(string='Full Gratuity (SAR)', readonly=True, digits=(16, 2))
    gratuity_factor = fields.Float(string='Entitlement Factor', readonly=True, digits=(16, 2))
    gratuity_amount = fields.Float(string='Gratuity Due (SAR)', readonly=True, digits=(16, 2))
    calculation_notes = fields.Text(string='Breakdown', readonly=True)

    result_computed = fields.Boolean(default=False)

    @api.onchange('employee_id', 'last_working_day', 'termination_reason')
    def _onchange_compute(self):
        self.result_computed = False
        self.years_of_service = 0
        self.full_gratuity = 0
        self.gratuity_factor = 0
        self.gratuity_amount = 0
        self.calculation_notes = False

    def action_calculate(self):
        self.ensure_one()
        emp = self.employee_id
        if not emp.hire_date:
            raise UserError('Employee has no hire date set.')
        if not emp.salary:
            raise UserError('Employee has no basic salary set.')
        if self.last_working_day < emp.hire_date:
            raise UserError('Last working day cannot be before hire date.')

        years, full, factor, amount, notes = self.env['sa.eos'].compute_gratuity(
            emp.salary,
            emp.hire_date,
            self.last_working_day,
            self.termination_reason,
        )
        self.write({
            'years_of_service': years,
            'full_gratuity': full,
            'gratuity_factor': factor,
            'gratuity_amount': amount,
            'calculation_notes': notes,
            'result_computed': True,
        })
        # Return the same wizard so the user sees results without closing
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }

    def action_save_eos(self):
        """Persist the calculated EOS as a permanent sa.eos record."""
        self.ensure_one()
        if not self.result_computed:
            raise UserError('Please calculate first.')
        emp = self.employee_id
        record = self.env['sa.eos'].create({
            'employee_id': emp.id,
            'last_working_day': self.last_working_day,
            'termination_reason': self.termination_reason,
            'hire_date': emp.hire_date,
            'basic_salary': emp.salary,
            'years_of_service': self.years_of_service,
            'full_gratuity': self.full_gratuity,
            'gratuity_factor': self.gratuity_factor,
            'gratuity_amount': self.gratuity_amount,
            'calculation_notes': self.calculation_notes,
        })
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'sa.eos',
            'res_id': record.id,
            'view_mode': 'form',
            'target': 'current',
        }
