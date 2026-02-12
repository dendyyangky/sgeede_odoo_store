# -*- coding: utf-8 -*-

from odoo import models, fields, Command, api, tools, _
from odoo.exceptions import UserError
from datetime import timedelta

class SGEEDEPartialPaymentWizard(models.TransientModel):
    _name = 'sgeede.writeoff.payment.wizard'
    _description = 'Write-Off Payment Distribution Wizard'

    move_line_ids = fields.Many2many('account.move.line', string="Account")
    account_id = fields.Many2one('account.account', string="Account", required=True, domain="[('active', '=', False), ('account_type', '!=', 'off_balance')]")
    currency_id = fields.Many2one('res.currency', string="Currency", readonly=True)
    journal_id = fields.Many2one('account.journal', string="Journal", check_company=True, domain="[('type', '=', 'general')]", compute='_compute_journal_id', store=True, readonly=False, required=True, precompute=True)
    company_id = fields.Many2one(comodel_name='res.company', required=True, readonly=True, compute='_compute_company_id')
    date = fields.Date(string='Date', default=fields.Date.context_today, required=True)
    amount = fields.Monetary(string='Amount', readonly=True)

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        pd_obj = self.env['sgeede.payment.distribution'].browse(self.env.context.get('active_ids', []))
        invoices = pd_obj.distribution_line_ids.mapped('invoice_id')
        move_lines = invoices.mapped('line_ids')
        
        if pd_obj.invoice_type in ['out_invoice', 'out_refund']:
            partner_account = pd_obj.partner_id.property_account_receivable_id
        else:
            partner_account = pd_obj.partner_id.property_account_payable_id
        
        invoice_aml = move_lines.filtered(lambda l: l.account_id == partner_account)
        res['move_line_ids'] = [Command.set(invoice_aml.ids)]
        res['amount'] = pd_obj.payment_amount - sum(pd_obj.distribution_line_ids.mapped('payment_amount'))
        return res

    @api.depends('move_line_ids.company_id')
    def _compute_company_id(self):
        for wizard in self:
            wizard.company_id = wizard.move_line_ids[0].company_id

    @api.depends('company_id')
    def _compute_journal_id(self):
        for wizard in self:
            wizard.journal_id = self.env['account.journal'].search([
                *self.env['account.journal']._check_company_domain(wizard.company_id),
                ('type', '=', 'general')
            ], limit=1)

    def _create_write_off_supplier_lines(self):
        pd_obj = self.env['sgeede.payment.distribution'].browse(self.env.context.get('active_ids', []))
        amount = self.amount
        line_ids_commands = [
            Command.create({
                'name': _('Write-Off'),
                'account_id': self.move_line_ids[0].account_id.id,
                'partner_id': pd_obj.partner_id.id,
                'currency_id': pd_obj.currency_id.id,
                'amount_currency': -amount,
                'balance': -amount,
            }),
            Command.create({
                'name': _('Write-Off'),
                'account_id': self.account_id.id,
                'partner_id': pd_obj.partner_id.id,
                'currency_id': pd_obj.currency_id.id,
                'amount_currency': amount,
                'balance': amount,
            }),
        ]
       
        return line_ids_commands

    def create_write_off_supplier(self):
        self.ensure_one()
        pd_obj = self.env['sgeede.payment.distribution'].browse(self.env.context.get('active_ids', []))
        write_off_vals = {
            'journal_id': self.journal_id.id,
            'company_id': self.company_id.id,
            'date': self.date,
            'ref': _('Write-Off for %s') % pd_obj.name,
            'line_ids': self._create_write_off_supplier_lines()
        }
        write_off_supplier_move = self.env['account.move'].with_context(
            skip_invoice_sync=True,
            skip_invoice_line_sync=True,
        ).create(write_off_vals)
        write_off_supplier_move.action_post()
        return write_off_supplier_move
    
    def create_write_off_customer(self):
        self.ensure_one()
        pd_obj = self.env['sgeede.payment.distribution'].browse(self.env.context.get('active_ids', []))
        amount = self.amount
        line_ids = []
        line_ids += [
            Command.create({
                'name': _('Write-Off'),
                'account_id': self.move_line_ids[0].account_id.id,
                'partner_id': pd_obj.partner_id.id,
                'currency_id': pd_obj.currency_id.id,
                'amount_currency': amount,
                'balance': amount,
            }),
            Command.create({
                'name': _('Write-Off'),
                'account_id': self.account_id.id,
                'partner_id': pd_obj.partner_id.id,
                'currency_id': pd_obj.currency_id.id,
                'amount_currency': -amount,
                'balance': -amount,
            }),
        ]
        transfer_vals = {
            'ref': _('Write-Off for %s') % pd_obj.name,
            'journal_id': self.journal_id.id,
            'company_id': self.company_id.id,
            'date': self.date,
            'line_ids': line_ids,
        }
        write_off_customer_move = self.env['account.move'].create(transfer_vals)
        write_off_customer_move.action_post()
        return write_off_customer_move
    
    def make_payment_distribution_writeoff(self):
        self.ensure_one()
        payment_vals = {}
        pd_obj = self.env['sgeede.payment.distribution'].browse(self.env.context.get('active_ids', []))
        partner_id = pd_obj.partner_id.id
        vals = {
            'out_invoice': {'payment_type': 'inbound', 'partner_type': 'customer'},
            'in_invoice': {'payment_type': 'outbound', 'partner_type': 'supplier'},
            'in_refund': {'payment_type': 'inbound', 'partner_type': 'supplier'},
            'out_refund': {'payment_type': 'outbound', 'partner_type': 'customer'}
        }
        
        payment_vals.update(vals[pd_obj.invoice_type])
        payment_vals.update({
            'partner_id': partner_id or False,
            'journal_id': pd_obj.journal_id and pd_obj.journal_id.id or False,
            'date': pd_obj.payment_date or self.Date.context_today(self),
            'amount': pd_obj.payment_amount,
            'currency_id': pd_obj.currency_id.id,
            'payment_method_id': self.env.ref('account.account_payment_method_manual_in').id
            if pd_obj.invoice_type in ['out_invoice', 'in_refund'] else self.env.ref('account.account_payment_method_manual_out').id
        })
        payment = self.env['account.payment'].create(payment_vals)
        if payment:
            payment.action_post()
            pd_obj.write({'payment_id': payment.id})

            if pd_obj.invoice_type in ['out_invoice', 'out_refund']:
                partner_account = pd_obj.partner_id.property_account_receivable_id
            else:
                partner_account = pd_obj.partner_id.property_account_payable_id
            
            move_lines_to_reconcile = self.move_line_ids._origin
            payment_aml = payment.move_id.line_ids.filtered(lambda l: l.account_id == partner_account)
            if pd_obj.invoice_type in ['in_invoice', 'out_refund']:
                write_off_move = self.create_write_off_supplier()
            else:
                write_off_move = self.create_write_off_customer()
            write_off_line_to_reconcile = write_off_move.line_ids[0]
            aml_obj = [[move_lines_to_reconcile, payment_aml, write_off_line_to_reconcile]]
            self.env['account.move.line']._reconcile_plan(aml_obj)
            pd_obj.state = 'done'

    def _action_open_wizard(self):
        self.ensure_one()
        return {
            'name': _('Write-Off Entry'),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'sgeede.writeoff.payment.wizard',
            'target': 'new',
        }