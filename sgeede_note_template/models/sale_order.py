from odoo import models, fields, api

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    note_template = fields.Many2one('sgeede.note.template', string='Select Template')

    @api.onchange('note_template')
    def apply_template_to_note(self):
        self.ensure_one()
        self.note = False

        self.note = self.note_template.note