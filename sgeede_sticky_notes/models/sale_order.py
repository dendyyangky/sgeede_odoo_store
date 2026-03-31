from odoo import models, fields

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    note_ids = fields.One2many('sgeede.sticky.notes', 'sale_order_id')