from odoo import models, fields

class SGEEDENoteTemplate(models.Model):
    _name = 'sgeede.note.template'

    name = fields.Char(string='Template Name')
    note = fields.Text(string='Note')
    apply_to = fields.Selection([
        ('sale', 'Sales'),
        ('purchase', 'Purchase'),
        ('both', 'Both')
    ])