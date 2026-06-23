# -*- coding: utf-8 -*-

from odoo import models, fields, api


class SaPayslip(models.Model):
    _name = 'sa.payslip'
    _description = 'Payslip'
    _order = 'date_from desc'

    name = fields.Char(string='Reference', readonly=True, default='New', copy=False)
    employee_id = fields.Many2one('sa.employee', string='Employee', required=True)
    nationality_type = fields.Selection(related='employee_id.nationality_type', store=True)
    department_id = fields.Many2one(related='employee_id.department_id', store=True, string='Department')

    date_from = fields.Date(string='From', required=True)
    date_to = fields.Date(string='To', required=True)

    # Earnings
    basic_salary = fields.Float(string='Basic Salary (SAR)')
    housing_allowance = fields.Float(string='Housing Allowance', compute='_compute_housing', store=True)
    transport_allowance = fields.Float(string='Transport Allowance', default=500.0)
    other_allowances = fields.Float(string='Other Allowances')
    gross_salary = fields.Float(string='Gross Salary', compute='_compute_gross', store=True)

    # Deductions
    gosi_employee = fields.Float(string='GOSI (Employee)', compute='_compute_gosi', store=True)
    gosi_employer = fields.Float(string='GOSI (Employer)', compute='_compute_gosi', store=True)
    other_deductions = fields.Float(string='Other Deductions')

    # Net
    net_salary = fields.Float(string='Net Salary', compute='_compute_net', store=True)

    state = fields.Selection([
        ('draft',     'Draft'),
        ('confirmed', 'Confirmed'),
        ('paid',      'Paid'),
    ], default='draft', required=True)

    @api.onchange('employee_id')
    def _onchange_employee(self):
        if self.employee_id:
            self.basic_salary = self.employee_id.salary

    @api.depends('basic_salary')
    def _compute_housing(self):
        for slip in self:
            slip.housing_allowance = slip.basic_salary * 0.25

    @api.depends('basic_salary', 'housing_allowance', 'transport_allowance', 'other_allowances')
    def _compute_gross(self):
        for slip in self:
            slip.gross_salary = (
                slip.basic_salary
                + slip.housing_allowance
                + slip.transport_allowance
                + slip.other_allowances
            )

    @api.depends('basic_salary', 'nationality_type')
    def _compute_gosi(self):
        for slip in self:
            if slip.nationality_type == 'saudi':
                slip.gosi_employee = slip.basic_salary * 0.09      # 9% employee share
                slip.gosi_employer = slip.basic_salary * 0.0975    # 9.75% employer share
            else:
                slip.gosi_employee = 0.0
                slip.gosi_employer = slip.basic_salary * 0.02      # 2% hazard insurance only

    @api.depends('gross_salary', 'gosi_employee', 'other_deductions')
    def _compute_net(self):
        for slip in self:
            slip.net_salary = slip.gross_salary - slip.gosi_employee - slip.other_deductions

    def action_confirm(self):
        self.write({'state': 'confirmed'})

    def action_pay(self):
        self.write({'state': 'paid'})

    def action_reset(self):
        self.write({'state': 'draft'})

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('sa.payslip') or 'New'
        return super().create(vals_list)
