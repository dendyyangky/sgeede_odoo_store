from odoo import api, fields, models, _

class ResPartner(models.Model):
    _inherit = 'res.partner'

    quotation_count = fields.Integer(
        string='Quotation Count',
        compute='_compute_sale_customer_statistics',
        store=True,
    )
    sale_order_count = fields.Integer(
        string='Sale Order Count',
        compute='_compute_sale_customer_statistics',
        store=True,
    )
    total_sales_amount = fields.Monetary(
        string='Total Sales Amount',
        compute='_compute_sale_customer_statistics',
        store=True,
        currency_field='currency_id',
    )
    average_order_value = fields.Monetary(
        string='Average Order Value',
        compute='_compute_sale_customer_statistics',
        store=True,
        currency_field='currency_id',
    )
    last_order_date = fields.Datetime(
        string='Last Order Date',
        compute='_compute_sale_customer_statistics',
        store=True,
    )

    @api.depends(
        'sale_order_ids.state',
        'sale_order_ids.amount_total',
        'sale_order_ids.date_order',
    )
    def _compute_sale_customer_statistics(self):
        SaleOrder = self.env['sale.order']
        quotation_states = ('draft', 'sent')
        confirmed_states = ('sale', 'done')

        stats_by_partner = {
            partner.id: {
                'quotation_count': 0,
                'sale_order_count': 0,
                'total_sales_amount': 0.0,
                'average_order_value': 0.0,
                'last_order_date': False,
            }
            for partner in self
        }

        if not self.ids:
            return

        quotation_groups = SaleOrder._read_group(
            domain=[
                ('partner_id', 'in', self.ids),
                ('state', 'in', quotation_states),
            ],
            groupby=['partner_id'],
            aggregates=['__count'],
        )
        for partner, count in quotation_groups:
            stats_by_partner[partner.id]['quotation_count'] = count

        confirmed_groups = SaleOrder._read_group(
            domain=[
                ('partner_id', 'in', self.ids),
                ('state', 'in', confirmed_states),
            ],
            groupby=['partner_id'],
            aggregates=['__count', 'amount_total:sum', 'amount_total:avg', 'date_order:max'],
        )
        for partner, count, total, average, last_date in confirmed_groups:
            stats = stats_by_partner[partner.id]
            stats.update({
                'sale_order_count': count,
                'total_sales_amount': total or 0.0,
                'average_order_value': average or 0.0,
                'last_order_date': last_date,
            })

        for partner in self:
            stats = stats_by_partner[partner.id]
            partner.quotation_count = stats['quotation_count']
            partner.sale_order_count = stats['sale_order_count']
            partner.total_sales_amount = stats['total_sales_amount']
            partner.average_order_value = stats['average_order_value']
            partner.last_order_date = stats['last_order_date']

    def action_view_confirmed_sale_orders(self):
        self.ensure_one()
        confirmed_states = ('sale', 'done')
        sale_orders = self.env['sale.order'].search([
            ('partner_id', '=', self.id),
            ('state', 'in', confirmed_states),
        ])

        action = self.env['ir.actions.act_window']._for_xml_id('sale.action_orders')
        action['name'] = _('Sales Orders')
        action['domain'] = [
            ('id', 'in', sale_orders.ids),
            ('state', 'in', confirmed_states),
        ]
        action['context'] = {
            'default_partner_id': self.id,
        }

        if len(sale_orders) == 1:
            action['views'] = [(self.env.ref('sale.view_order_form').id, 'form')]
            action['res_id'] = sale_orders.id

        return action
