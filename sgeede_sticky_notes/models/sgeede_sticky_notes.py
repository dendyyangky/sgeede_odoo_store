from odoo import models, fields

class SGEEDEStickyNotes(models.Model):
    _name = 'sgeede.sticky.notes'

    sale_order_id = fields.Many2one('sale.order', ondelete='cascade')
    purchase_order_id = fields.Many2one('purchase.order', ondelete='cascade')
    account_move_id = fields.Many2one('account.move', ondelete='cascade')
    content = fields.Text(string='Note')
    color = fields.Selection([
        ('yellow', 'Yellow'),
        ('blue', 'Blue'),
        ('red', 'Red'),
        ('green', 'Green'),
    ], default='yellow')
    user_id = fields.Many2one('res.users', string='User', default=lambda self: self.env.user)
    date = fields.Datetime(string='Date', default=fields.Datetime.now())
    active = fields.Boolean(default=True)



