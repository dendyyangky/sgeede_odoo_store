from odoo import models, fields

class ProjectProject(models.Model):
    _inherit = 'project.project'

    completion_percentage = fields.Float(string='Completion Percentage (%)', compute='_compute_completion_percentage')

    def _compute_completion_percentage(self):
        for rec in self:
            total_percent = sum(rec.task_ids.mapped('completion_percentage'))
            total_task = len(rec.task_ids)

            rec.completion_percentage = (total_percent / total_task if total_task else 0.0)