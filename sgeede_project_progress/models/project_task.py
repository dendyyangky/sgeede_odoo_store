from odoo import models, fields

class ProjectTask(models.Model):
    _inherit = 'project.task'

    completion_percentage = fields.Float(string='Completion Percentage (%)')