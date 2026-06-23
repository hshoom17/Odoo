# -*- coding: utf-8 -*-

from odoo import models, fields, api


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
