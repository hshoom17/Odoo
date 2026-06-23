# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import ValidationError
from datetime import date, timedelta


class SaEmployee(models.Model):
    _name = 'sa.employee'
    _description = 'Employee'
    _order = 'name'

    name = fields.Char(string='Full Name', required=True)
    employee_number = fields.Char(string='Employee #', readonly=True, default='New', copy=False)

    nationality_type = fields.Selection([
        ('saudi', 'Saudi'),
        ('expat', 'Expat'),
    ], string='Nationality', required=True, default='expat')

    national_id = fields.Char(string='National ID')
    iqama_number = fields.Char(string='Iqama Number')
    iqama_expiry = fields.Date(string='Iqama Expiry')
    iqama_status = fields.Selection([
        ('valid',    'Valid'),
        ('expiring', 'Expiring Soon'),
        ('expired',  'Expired'),
    ], string='Iqama Status', compute='_compute_iqama_status', store=True)

    # ── Documents ─────────────────────────────────────────────────────────────
    passport_number = fields.Char(string='Passport Number')
    passport_expiry = fields.Date(string='Passport Expiry')
    passport_status = fields.Selection([
        ('valid', 'Valid'), ('expiring', 'Expiring Soon'), ('expired', 'Expired'),
    ], compute='_compute_doc_statuses', store=True)

    work_permit_number = fields.Char(string='Work Permit Number')
    work_permit_expiry = fields.Date(string='Work Permit Expiry')
    work_permit_status = fields.Selection([
        ('valid', 'Valid'), ('expiring', 'Expiring Soon'), ('expired', 'Expired'),
    ], compute='_compute_doc_statuses', store=True)

    # ── Contract ──────────────────────────────────────────────────────────────
    contract_type = fields.Selection([
        ('open_ended', 'Open-Ended'),
        ('fixed_term', 'Fixed-Term'),
    ], string='Contract Type', default='fixed_term')
    contract_start_date = fields.Date(string='Contract Start')
    contract_end_date = fields.Date(string='Contract End')
    contract_status = fields.Selection([
        ('valid', 'Valid'), ('expiring', 'Expiring Soon'), ('expired', 'Expired'),
    ], compute='_compute_doc_statuses', store=True)

    # ── Probation ─────────────────────────────────────────────────────────────
    probation_end_date = fields.Date(
        string='Probation End',
        compute='_compute_probation_end', store=True, readonly=False,
        help='Defaults to hire date + 90 days; editable if extended (max 180 days).',
    )
    probation_status = fields.Selection([
        ('active',   'In Probation'),
        ('ended',    'Probation Ended'),
        ('expiring', 'Probation Ending Soon'),
    ], compute='_compute_probation_status', store=True)

    department_id = fields.Many2one('sa.department', string='Department')
    job_title = fields.Char(string='Job Title')
    hire_date = fields.Date(string='Hire Date', default=fields.Date.today)
    salary = fields.Float(string='Basic Salary (SAR)')

    status = fields.Selection([
        ('active',   'Active'),
        ('inactive', 'Inactive'),
    ], default='active', required=True)

    # ── Leave balance ─────────────────────────────────────────────────────────
    years_of_service = fields.Float(
        string='Years of Service', compute='_compute_years', store=True, digits=(16, 1),
    )
    annual_leave_entitlement = fields.Integer(
        string='Annual Entitlement (days)', compute='_compute_years', store=True,
        help='21 days for < 5 years, 30 days for ≥ 5 years (Saudi Labor Law Art. 109).',
    )
    annual_leave_taken = fields.Integer(
        string='Annual Leave Taken (this year)', compute='_compute_annual_taken',
    )
    annual_leave_balance = fields.Integer(
        string='Annual Leave Balance', compute='_compute_annual_taken',
    )

    _sql_constraints = [
        ('unique_iqama_number', 'UNIQUE(iqama_number)', 'Iqama number must be unique.'),
        ('unique_national_id',  'UNIQUE(national_id)',  'National ID must be unique.'),
    ]

    @api.onchange('nationality_type')
    def _onchange_nationality_type(self):
        if self.nationality_type == 'saudi':
            self.iqama_number = False
            self.iqama_expiry = False
        else:
            self.national_id = False

    @api.constrains('nationality_type', 'iqama_number', 'iqama_expiry')
    def _check_expat_iqama(self):
        for emp in self:
            if emp.nationality_type == 'expat':
                if not emp.iqama_number:
                    raise ValidationError('Expat employees must have an Iqama number.')
                if not emp.iqama_expiry:
                    raise ValidationError('Expat employees must have an Iqama expiry date.')

    @api.depends('iqama_expiry', 'nationality_type')
    def _compute_iqama_status(self):
        today = date.today()
        for emp in self:
            if emp.nationality_type == 'saudi' or not emp.iqama_expiry:
                emp.iqama_status = False
                continue
            days_left = (emp.iqama_expiry - today).days
            if days_left < 0:
                emp.iqama_status = 'expired'
            elif days_left <= 90:
                emp.iqama_status = 'expiring'
            else:
                emp.iqama_status = 'valid'

    @api.depends('passport_expiry', 'work_permit_expiry', 'contract_end_date', 'contract_type')
    def _compute_doc_statuses(self):
        today = date.today()
        for emp in self:
            emp.passport_status = self._expiry_status(emp.passport_expiry, today)
            emp.work_permit_status = self._expiry_status(emp.work_permit_expiry, today)
            if emp.contract_type == 'fixed_term':
                emp.contract_status = self._expiry_status(emp.contract_end_date, today)
            else:
                emp.contract_status = False

    @staticmethod
    def _expiry_status(expiry_date, today):
        if not expiry_date:
            return False
        days_left = (expiry_date - today).days
        if days_left < 0:
            return 'expired'
        if days_left <= 90:
            return 'expiring'
        return 'valid'

    @api.depends('hire_date')
    def _compute_probation_end(self):
        for emp in self:
            if emp.hire_date and not emp.probation_end_date:
                emp.probation_end_date = emp.hire_date + timedelta(days=90)

    @api.depends('probation_end_date')
    def _compute_probation_status(self):
        today = date.today()
        for emp in self:
            if not emp.probation_end_date:
                emp.probation_status = False
                continue
            days_left = (emp.probation_end_date - today).days
            if days_left < 0:
                emp.probation_status = 'ended'
            elif days_left <= 14:
                emp.probation_status = 'expiring'
            else:
                emp.probation_status = 'active'

    @api.depends('hire_date')
    def _compute_years(self):
        today = date.today()
        for emp in self:
            if emp.hire_date:
                years = (today - emp.hire_date).days / 365.0
                emp.years_of_service = round(years, 1)
                emp.annual_leave_entitlement = 30 if years >= 5 else 21
            else:
                emp.years_of_service = 0
                emp.annual_leave_entitlement = 21

    def _compute_annual_taken(self):
        today = date.today()
        year_start = date(today.year, 1, 1)
        year_end = date(today.year, 12, 31)
        Leave = self.env['sa.leave']
        for emp in self:
            taken = sum(
                Leave.search([
                    ('employee_id', '=', emp.id),
                    ('leave_type', '=', 'annual'),
                    ('state', '=', 'approved'),
                    ('date_from', '>=', year_start),
                    ('date_to', '<=', year_end),
                ]).mapped('days')
            )
            emp.annual_leave_taken = taken
            emp.annual_leave_balance = emp.annual_leave_entitlement - taken

    def action_suspend(self):
        self.write({'status': 'inactive'})

    def action_activate(self):
        self.write({'status': 'active'})

    def action_deactivate_expired_iqama(self):
        expired = self.filtered(lambda e: e.iqama_status == 'expired')
        expired.write({'status': 'inactive'})
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Done',
                'message': f'{len(expired)} employee(s) deactivated due to expired Iqama.',
                'type': 'warning',
            }
        }

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('employee_number', 'New') == 'New':
                vals['employee_number'] = self.env['ir.sequence'].next_by_code('sa.employee') or 'New'
        return super().create(vals_list)
