from odoo import models, fields

class AccountMove(models.Model):
    _inherit = 'account.move'

    note_ids = fields.One2many('sgeede.sticky.notes', 'account_move_id')