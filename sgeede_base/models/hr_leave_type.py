from odoo import _, api, fields, models
from dateutil.relativedelta import relativedelta
from datetime import date

class HrLeaveType(models.Model):
    _inherit = 'hr.leave.type'
    
    allocation_type = fields.Selection(
        [('day', 'Days'),
         ('month', 'Months'),
         ('year', 'Years')], default='day', string='Allocation Type')
    leave_type = fields.Selection([
        ('annual', 'Annual Leave'), 
        ('sick', 'Sick Leave'), 
        ('hospitalisation', "Hospitalisation Leave"), 
        ('maternity', "Maternity Leave"),
        ('paternity', "Paternity Leave"),
        ('childcare', "Childcare Leave"),
        ('extended_childcare', "Extended Childcare Leave"),
        ('adoption_childcare', "Adoption Leave"),
        ('no_pay', "No Pay Leave"),
        ('marriage', "Marriage Leave"),
        ('compassionate', "Compassionate Leave"),
        ('national_service', "National Service Leave"),
        ('infant_care', "Infant Care Leave"),], default='', string='Leave Type')    
    min_type = fields.Selection(
        [('day', 'Days'),
         ('month', 'Months'),
         ('year', 'Years')], default='day', string='Min Type')
    max_type = fields.Selection(
        [('day', 'Days'),
         ('month', 'Months'),
         ('year', 'Years')], default='day', string='Max Type')
    allocation_min = fields.Integer(string='Minimum Allocation')
    min_count = fields.Integer(string='Min Age', default=0)
    max_count = fields.Integer(string='Max Age', default=0)
    leave_config_ids = fields.One2many('sgeede.leave.config', 'leave_type_id', string='Leave Configurations')
    eligible_from_date = fields.Date(string="Eligible From Date", default="2017-01-01")