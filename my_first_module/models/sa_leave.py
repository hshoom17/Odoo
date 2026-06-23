# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import ValidationError
from datetime import date


class SaLeave(models.Model):
    _name = 'sa.leave'
    _description = 'Leave Request'
    _order = 'date_from desc'

    name = fields.Char(string='Reference', readonly=True, default='New', copy=False)
    employee_id = fields.Many2one('sa.employee', string='Employee', required=True, ondelete='restrict')
    department_id = fields.Many2one(related='employee_id.department_id', store=True, string='Department')
    nationality_type = fields.Selection(related='employee_id.nationality_type', store=True)

    leave_type = fields.Selection([
        ('annual',      'Annual Leave'),
        ('hajj',        'Hajj Leave'),
        ('sick_full',   'Sick Leave – Full Pay'),
        ('sick_half',   'Sick Leave – Half Pay'),
        ('sick_unpaid', 'Sick Leave – Unpaid'),
        ('maternity',   'Maternity Leave'),
        ('paternity',   'Paternity Leave'),
        ('emergency',   'Emergency Leave'),
    ], string='Leave Type', required=True)

    date_from = fields.Date(string='Start Date', required=True)
    date_to = fields.Date(string='End Date', required=True)
    days = fields.Integer(string='Days', compute='_compute_days', store=True)

    state = fields.Selection([
        ('draft',    'Draft'),
        ('approved', 'Approved'),
        ('refused',  'Refused'),
    ], default='draft', required=True)

    notes = fields.Text(string='Notes')

    # ── computed helpers exposed for the form ─────────────────────────────────
    annual_balance = fields.Integer(
        string='Annual Balance (days)',
        compute='_compute_annual_balance',
    )

    @api.depends('date_from', 'date_to')
    def _compute_days(self):
        for rec in self:
            if rec.date_from and rec.date_to:
                delta = (rec.date_to - rec.date_from).days + 1
                rec.days = max(delta, 0)
            else:
                rec.days = 0

    @api.depends('employee_id', 'leave_type')
    def _compute_annual_balance(self):
        for rec in self:
            if rec.employee_id and rec.leave_type == 'annual':
                rec.annual_balance = rec.employee_id.annual_leave_balance
            else:
                rec.annual_balance = 0

    # ── business logic ────────────────────────────────────────────────────────

    @api.constrains('date_from', 'date_to')
    def _check_dates(self):
        for rec in self:
            if rec.date_from and rec.date_to and rec.date_to < rec.date_from:
                raise ValidationError('End date must be on or after start date.')

    def _get_approved_days(self, employee, leave_type, year=None):
        """Return total approved days for employee + leave_type in calendar year."""
        if year is None:
            year = date.today().year
        domain = [
            ('employee_id', '=', employee.id),
            ('leave_type', '=', leave_type),
            ('state', '=', 'approved'),
            ('date_from', '>=', date(year, 1, 1)),
            ('date_to', '<=', date(year, 12, 31)),
        ]
        leaves = self.env['sa.leave'].search(domain)
        return sum(leaves.mapped('days'))

    @api.constrains('employee_id', 'leave_type', 'days', 'date_from', 'date_to', 'state')
    def _check_leave_limits(self):
        for rec in self:
            if rec.state == 'refused':
                continue
            emp = rec.employee_id
            year = rec.date_from.year if rec.date_from else date.today().year

            if rec.leave_type == 'annual':
                entitlement = emp.annual_leave_entitlement
                taken = self._get_days_excluding_self(emp, 'annual', year)
                if taken + rec.days > entitlement:
                    raise ValidationError(
                        f'Annual leave exceeds entitlement. '
                        f'Entitlement: {entitlement} days, Already taken: {taken} days, '
                        f'Requested: {rec.days} days.'
                    )

            elif rec.leave_type == 'hajj':
                # Hajj leave is once in a career
                existing = self.env['sa.leave'].search([
                    ('employee_id', '=', emp.id),
                    ('leave_type', '=', 'hajj'),
                    ('state', '=', 'approved'),
                    ('id', '!=', rec.id),
                ])
                if existing:
                    raise ValidationError(
                        'Hajj leave has already been taken by this employee. '
                        'It is granted only once per career.'
                    )
                if rec.days > 10:
                    raise ValidationError('Hajj leave cannot exceed 10 days.')

            elif rec.leave_type == 'sick_full':
                taken = self._get_days_excluding_self(emp, 'sick_full', year)
                if taken + rec.days > 30:
                    raise ValidationError(
                        f'Sick leave (full pay) cannot exceed 30 days per year. '
                        f'Already taken: {taken} days.'
                    )

            elif rec.leave_type == 'sick_half':
                taken = self._get_days_excluding_self(emp, 'sick_half', year)
                if taken + rec.days > 60:
                    raise ValidationError(
                        f'Sick leave (half pay) cannot exceed 60 days per year. '
                        f'Already taken: {taken} days.'
                    )

            elif rec.leave_type == 'sick_unpaid':
                taken = self._get_days_excluding_self(emp, 'sick_unpaid', year)
                if taken + rec.days > 30:
                    raise ValidationError(
                        f'Sick leave (unpaid) cannot exceed 30 days per year. '
                        f'Already taken: {taken} days.'
                    )

    def _get_days_excluding_self(self, employee, leave_type, year):
        domain = [
            ('employee_id', '=', employee.id),
            ('leave_type', '=', leave_type),
            ('state', '=', 'approved'),
            ('date_from', '>=', date(year, 1, 1)),
            ('date_to', '<=', date(year, 12, 31)),
            ('id', '!=', self.id if not isinstance(self.id, models.NewId) else -1),
        ]
        return sum(self.env['sa.leave'].search(domain).mapped('days'))

    # ── workflow actions ──────────────────────────────────────────────────────

    def action_approve(self):
        self.write({'state': 'approved'})

    def action_refuse(self):
        self.write({'state': 'refused'})

    def action_reset(self):
        self.write({'state': 'draft'})

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('sa.leave') or 'New'
        return super().create(vals_list)
