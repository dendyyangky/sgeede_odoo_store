from odoo import models, fields, api

class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    note_template = fields.Many2one('sgeede.note.template', string='Select Template')

    @api.onchange('note_template')
    def apply_template_to_note(self):
        self.ensure_one()
        self.notes = False

        self.notes = self.note_template.note