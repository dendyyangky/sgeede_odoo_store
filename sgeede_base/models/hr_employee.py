from odoo import _, api, fields, models

class HREmployee(models.Model):
    _inherit = 'hr.employee'

    join_date = fields.Date(string='Join Date', help='Employee join date. Defaults to the earliest contract start date if left empty.')
    children_ids = fields.One2many('sgeede.employee.children', 'employee_id', string='Children Details')
    is_pregnant = fields.Boolean(string='Is Pregnant')
    spouse_country_id = fields.Many2one('res.country', string='Spouse Country')
    is_spouse_pregnant = fields.Boolean(string="Is Spouse Pregnant")
    marriage_date = fields.Date(string="Marriage Date")
    edd_date = fields.Date(string="Estimated Delivery Date")