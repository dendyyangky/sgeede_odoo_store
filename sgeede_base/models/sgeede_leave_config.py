# -*- coding: utf-8 -*-
from odoo import fields, api, models, _

class SGEEDELeaveConfig(models.Model):
    _name = 'sgeede.leave.config'
    _description = 'Leave Config'    

    added_value = fields.Float(string='Day of Leave', default=0.0)
    months_count = fields.Integer(string='Months of Service', default=0)
    years_count = fields.Integer(string='Years of Service', default=0)
    service_type = fields.Selection(
        [('day', 'Days'),
         ('month', 'Months'),
         ('year', 'Years')], default='day', string='Service Type')
    sg_citizen_type = fields.Selection(
        [('yes', 'Yes'),
         ('no', 'No'),], default='yes', string='Child is a Singapore citizen')
    leave_type_id = fields.Many2one('hr.leave.type', string='Leave Type', required=True)