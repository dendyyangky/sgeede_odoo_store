from odoo import models, fields

class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    note_ids = fields.One2many('sgeede.sticky.notes', 'purchase_order_id')