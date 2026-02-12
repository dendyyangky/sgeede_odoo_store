from odoo import models, fields, api

class ProjectProject(models.Model):
    _inherit = 'project.project'

    completion_percentage = fields.Float(string='Completion Percentage (%)', compute='_compute_completion_percentage')

    @api.depends('task_ids.completion_percentage', 'task_ids')
    def _compute_completion_percentage(self):
        Task = self.env['project.task']

        for rec in self:
            tasks = Task.search([('project_id', '=', rec.id)])

            total_percent = sum(tasks.mapped('completion_percentage'))
            total_tasks = len(tasks)

            rec.completion_percentage = (
                total_percent / total_tasks if total_tasks else 0.0
            )

    def action_dummy(self):
        return True