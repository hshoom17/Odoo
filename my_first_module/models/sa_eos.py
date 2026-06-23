# -*- coding: utf-8 -*-

from odoo import models, fields, api
from datetime import date


class SaEos(models.Model):
    """
    End of Service gratuity record (Saudi Labor Law, Articles 84-88).
    Created when an employee leaves; keeps a permanent audit trail.
    """
    _name = 'sa.eos'
    _description = 'End of Service Gratuity'
    _order = 'last_working_day desc'

    name = fields.Char(string='Reference', readonly=True, default='New', copy=False)
    employee_id = fields.Many2one('sa.employee', string='Employee', required=True, ondelete='restrict')
    department_id = fields.Many2one(related='employee_id.department_id', store=True)

    last_working_day = fields.Date(string='Last Working Day', required=True)
    termination_reason = fields.Selection([
        ('resignation',   'Resignation'),
        ('termination',   'Termination by Employer'),
        ('mutual',        'Mutual Agreement'),
        ('death',         'Death'),
        ('retirement',    'Retirement'),
    ], string='Reason', required=True)

    # Computed from employee at time of calculation
    hire_date = fields.Date(string='Hire Date')
    basic_salary = fields.Float(string='Last Basic Salary (SAR)')

    # Output
    years_of_service = fields.Float(string='Years of Service', digits=(16, 2))
    full_gratuity = fields.Float(string='Full Gratuity (SAR)', digits=(16, 2))
    gratuity_factor = fields.Float(string='Entitlement Factor', digits=(16, 2),
                                   help='1.0 = full, 0.67 = two-thirds, 0.33 = one-third, 0 = none')
    gratuity_amount = fields.Float(string='Gratuity Due (SAR)', digits=(16, 2))
    calculation_notes = fields.Text(string='Calculation Notes', readonly=True)

    state = fields.Selection([
        ('draft', 'Draft'),
        ('paid',  'Paid'),
    ], default='draft')

    def action_mark_paid(self):
        self.write({'state': 'paid'})

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('sa.eos') or 'New'
        return super().create(vals_list)

    # ── Saudi EOS formula ─────────────────────────────────────────────────────

    @staticmethod
    def compute_gratuity(basic_salary, hire_date, last_working_day, termination_reason):
        """
        Returns (years, full_gratuity, factor, amount, notes).

        Saudi Labor Law:
          Base unit = daily wage = basic_salary / 30
          First 5 years: 15 days per year (half-month)
          Each year after 5: 30 days per year (full month)

        Resignation entitlement factor:
          < 2 years   → 0
          2–<5 years  → 1/3
          5–<10 years → 2/3
          ≥10 years   → 1 (full)

        Termination by employer → always full from day 1.
        Mutual / Death / Retirement → always full.
        """
        if not hire_date or not last_working_day or not basic_salary:
            return 0, 0, 0, 0, 'Insufficient data.'

        days_worked = (last_working_day - hire_date).days
        years = days_worked / 365.0
        daily_wage = basic_salary / 30.0

        # Full gratuity (regardless of reason)
        if years <= 5:
            full_gratuity = daily_wage * 15 * years
        else:
            full_gratuity = (daily_wage * 15 * 5) + (daily_wage * 30 * (years - 5))

        # Entitlement factor
        if termination_reason == 'resignation':
            if years < 2:
                factor = 0.0
                note = 'Resignation with < 2 years service: no gratuity.'
            elif years < 5:
                factor = 1 / 3
                note = f'Resignation with {years:.1f} years: 1/3 of full gratuity.'
            elif years < 10:
                factor = 2 / 3
                note = f'Resignation with {years:.1f} years: 2/3 of full gratuity.'
            else:
                factor = 1.0
                note = f'Resignation with {years:.1f} years: full gratuity.'
        else:
            factor = 1.0
            labels = {
                'termination': 'Termination by employer',
                'mutual': 'Mutual agreement',
                'death': 'Death',
                'retirement': 'Retirement',
            }
            note = f'{labels.get(termination_reason, termination_reason)} — full gratuity applies.'

        amount = full_gratuity * factor
        notes = (
            f'Hire date: {hire_date} | Last day: {last_working_day}\n'
            f'Days worked: {days_worked} ({years:.2f} years)\n'
            f'Daily wage: SAR {daily_wage:.2f}\n'
            f'Full gratuity: SAR {full_gratuity:.2f}\n'
            f'Factor: {factor:.2f}\n'
            f'{note}\n'
            f'Gratuity due: SAR {amount:.2f}'
        )
        return round(years, 2), round(full_gratuity, 2), round(factor, 2), round(amount, 2), notes
