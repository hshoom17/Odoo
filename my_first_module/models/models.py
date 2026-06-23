# -*- coding: utf-8 -*-

from odoo import models, fields, api
from datetime import date


class SaDepartment(models.Model):
    _name = 'sa.department'
    _description = 'Department'

    name = fields.Char(required=True)
    employee_ids = fields.One2many('sa.employee', 'department_id', string='Employees')
    total_employees = fields.Integer(compute='_compute_saudization', store=True)
    saudi_count = fields.Integer(compute='_compute_saudization', store=True)
    saudization_pct = fields.Float(string='Saudization %', compute='_compute_saudization', store=True)

    @api.depends('employee_ids.nationality_type', 'employee_ids.status')
    def _compute_saudization(self):
        for dept in self:
            active = dept.employee_ids.filtered(lambda e: e.status == 'active')
            total = len(active)
            saudis = len(active.filtered(lambda e: e.nationality_type == 'saudi'))
            dept.total_employees = total
            dept.saudi_count = saudis
            dept.saudization_pct = (saudis / total * 100) if total else 0.0


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

    national_id = fields.Char(string='National ID')        # Saudi employees
    iqama_number = fields.Char(string='Iqama Number')      # Expat employees
    iqama_expiry = fields.Date(string='Iqama Expiry')
    iqama_status = fields.Selection([
        ('valid',    'Valid'),
        ('expiring', 'Expiring Soon'),
        ('expired',  'Expired'),
    ], string='Iqama Status', compute='_compute_iqama_status', store=True)

    department_id = fields.Many2one('sa.department', string='Department')
    job_title = fields.Char(string='Job Title')
    hire_date = fields.Date(string='Hire Date', default=fields.Date.today)
    salary = fields.Float(string='Basic Salary (SAR)')

    status = fields.Selection([
        ('active',   'Active'),
        ('inactive', 'Inactive'),
    ], default='active', required=True)

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
