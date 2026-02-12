# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import RedirectWarning, UserError, ValidationError

class SGEEDEPaymentDistribution(models.Model):
    _name = 'sgeede.payment.distribution'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Payment Distribution'

    name = fields.Char('Name', default='New')
    reference = fields.Char('Memo')
    payment_amount = fields.Monetary(string='Payment Amount')
    payment_date = fields.Date("Payment Date", default=fields.Date.context_today)
    invoice_type = fields.Selection([
        ('out_invoice', 'Customer Invoices'),
        ('in_invoice', 'Vendor Bills'),
        ('in_refund', 'Vendor Credit Notes'),
        ('out_refund', 'Customer Credit Notes')
    ], required=True, string='Invoice Type', default='out_invoice')
    move_type = fields.Selection(selection=[
        ('entry', 'Journal Entry'),
        ('out_invoice', 'Customer Invoice'),
        ('out_refund', 'Customer Credit Note'),
        ('in_invoice', 'Vendor Bill'),
        ('in_refund', 'Vendor Credit Note'),
        ('out_receipt', 'Sales Receipt'),
        ('in_receipt', 'Purchase Receipt'),
    ], string='Type', default="out_invoice")
    state = fields.Selection([('draft', 'Draft'), ('done', 'Done'),('cancel','Cancelled')], default='draft')
    journal_id = fields.Many2one('account.journal', string='Journal', required=True, domain=[('type', 'in', ['cash', 'bank'])])
    partner_id = fields.Many2one('res.partner', string='Partner', required=True)
    currency_id = fields.Many2one('res.currency', string='Currency', default=lambda self: self.env.user.company_id.currency_id)
    company_id = fields.Many2one('res.company', related='journal_id.company_id', string='Company', readonly=True)
    payment_id = fields.Many2one('account.payment', string='Payment')
    distribution_line_ids = fields.One2many('sgeede.payment.distribution.line', 'distribution_id', string='Partial Account Line')
    
    #fitur payment distribution advance
    payment_feature_type = fields.Selection([
        ('default', 'Default'),
        ('advance', 'Advance')
    ], string='Payment Feature', default='default')
    payment_type = fields.Selection([
        ('outbound', 'Send'),
        ('inbound', 'Receive'),
    ], string='Payment Type', default='inbound', tracking=True)
    move_knockoff_id = fields.Many2one('account.move', string='Move Knockoff')
    move_writeoff_id = fields.Many2one('account.move', string='Move Writeoff')

    # KOLOM UNTUK CUSTOMER INVOICE
    select_move_ids = fields.Many2many('account.move', 'invoice_id', string='Invoice')
    select_move_knockoff_bill_ids = fields.Many2many('account.move', 'knockoff_bill_id', string='Knockoff Bill')
    select_credit_note_ids = fields.Many2many('account.move', 'credit_note_id', string='Credit Note')
    sum_total_invoice = fields.Monetary('Total Invoice', tracking=True)
    sum_total_knockoff_bill = fields.Monetary('Total Knockoff', tracking=True)
    sum_total_credit_note = fields.Monetary('Total Credit Note', tracking=True)

    # KOLOM UNTUK WRITEOFF
    account_writeoff_ids = fields.One2many('sgeede.payment.writeoff', 'writeoff_id', string='Write Off')
    amount_writeoff = fields.Monetary('Amount Write Off', tracking=True)

    # KOLOM UNTUK VENDOR PAYMENT
    select_move_bill_ids = fields.Many2many('account.move', 'bill_id', string='Bill')
    select_move_knockoff_invoice_ids = fields.Many2many('account.move', 'knockoff_invoice_id', string='Knockoff Invoice')
    select_refund_ids = fields.Many2many('account.move', 'refund_id', string='Refund')
    sum_total_bill = fields.Monetary('Total Bill', tracking=True)
    sum_total_knockoff_invoice = fields.Monetary('Total Knockoff', tracking=True)
    sum_total_refund = fields.Monetary('Total Refund', tracking=True)

    @api.onchange('select_move_ids')
    def _onchange_select_move_ids(self):
        total_amount = 0
        for rec in self.select_move_ids:
            total_amount += rec.amount_residual
        self.sum_total_invoice = total_amount

    @api.onchange('select_move_knockoff_bill_ids')
    def _onchange_select_move_knockoff_bill_ids(self):
        total_amount = 0
        for rec in self.select_move_knockoff_bill_ids:
            total_amount += rec.amount_residual
        self.sum_total_knockoff_bill = total_amount

    @api.onchange('select_credit_note_ids')
    def _onchange_select_credit_note_ids(self):
        total_amount = 0
        for rec in self.select_credit_note_ids:
            total_amount += rec.amount_residual
        self.sum_total_credit_note = total_amount
    
    @api.onchange('account_writeoff_ids')
    def _onchange_account_writeoff_ids(self):
        total_amount = 0
        for rec in self.account_writeoff_ids:
            total_amount += rec.amount
        self.amount_writeoff = total_amount
    
    @api.onchange('select_move_bill_ids')
    def _onchange_select_move_bill_ids(self):
        total_amount = 0
        for rec in self.select_move_bill_ids:
            total_amount += rec.amount_residual
        self.sum_total_bill = total_amount

    @api.onchange('select_move_knockoff_invoice_ids')
    def _onchange_select_move_knockoff_invoice_ids(self):
        total_amount = 0
        for rec in self.select_move_knockoff_invoice_ids:
            total_amount += rec.amount_residual
        self.sum_total_knockoff_invoice = total_amount

    @api.onchange('select_refund_ids')
    def _onchange_select_refund_ids(self):
        total_amount = 0
        for rec in self.select_refund_ids:
            total_amount += rec.amount_residual
        self.sum_total_refund = total_amount

    def action_create_account_payment(self):
        payment = self.env['account.payment'].create({
            'partner_id': self.partner_id.id,
            'payment_type': self.payment_type,
            'date': self.payment_date,
            'currency_id': self.currency_id.id,
            'memo': self.reference,
            'amount': self.payment_amount,
            'journal_id': self.journal_id.id,
            'company_id': self.company_id.id,
        })
        if payment.payment_type == 'outbound':
            ar_lines = payment.move_id.line_ids.filtered(lambda line: line.account_id.account_type == 'asset_receivable')
            ar_lines.write({'account_id': self.partner_id.property_account_payable_id.id})
            # lines_write_ap = payment.move_id.mapped('line_ids').filtered(lambda line: line.account_id.reconcile and line.account_id.account_type == 'asset_receivable').mapped('account_id')
            
        payment.action_post()
        self.write({'payment_id': payment.id})
        return payment

    def cancel_cn(self):
        for inv in self.select_move_ids:
            invoice_ids_partial_reconciles = inv.line_ids.matched_debit_ids + inv.line_ids.matched_credit_ids

            cn_lines = self.select_credit_note_ids.line_ids.filtered(lambda line: line.account_id.account_type in ('asset_receivable'))
            cn_partial_reconciles = cn_lines.matched_debit_ids.filtered(lambda partial_reconciles: partial_reconciles in invoice_ids_partial_reconciles) + cn_lines.matched_credit_ids.filtered(lambda partial_reconciles: partial_reconciles in invoice_ids_partial_reconciles)
            cn_partial_reconciles.unlink()

    def cancel_refund(self):
        for inv in self.select_move_bill_ids:
            invoice_ids_partial_reconciles = inv.line_ids.matched_debit_ids + inv.line_ids.matched_credit_ids

            refund_lines = self.select_refund_ids.line_ids.filtered(lambda line: line.account_id.account_type in ('liability_payable'))
            refund_partial_reconciles = refund_lines.matched_debit_ids.filtered(lambda partial_reconciles: partial_reconciles in invoice_ids_partial_reconciles) + refund_lines.matched_credit_ids.filtered(lambda partial_reconciles: partial_reconciles in invoice_ids_partial_reconciles)
            refund_partial_reconciles.unlink()

    def action_cancel(self):
        if self.state != 'done':
            raise UserError(_('You cannot cancel Payment with paid state.'))
        if self.payment_id:
            if self.payment_id.state == 'paid':
                self.payment_id.action_draft()
                self.payment_id.action_cancel()
        if self.select_credit_note_ids:
            self.cancel_cn()
        if self.select_refund_ids:
            self.cancel_refund()
        if self.move_knockoff_id:
            if self.move_knockoff_id.state == 'posted':
                self.move_knockoff_id.button_draft()
                self.move_knockoff_id.write({'name': ''})
                self.move_knockoff_id.button_cancel()
        if self.move_writeoff_id:
            if self.move_writeoff_id.state == 'posted':
                self.move_writeoff_id.button_draft()
                self.move_writeoff_id.write({'name': ''})
                self.move_writeoff_id.button_cancel()
        
        self.write({'state':'cancel'})
    
    def action_draft(self):
        if self.payment_id:
            self.write({'payment_id': ''})
        if self.move_writeoff_id:
            self.write({'move_writeoff_id': ''})
        if self.move_knockoff_id:
            self.write({'move_knockoff_id': ''})
        
        self.write({'state': 'draft'})

    def button_open_knockoff(self):
        ''' Redirect the user to this payment journal.
        :return:    An action on account.move.
        '''
        self.ensure_one()
        return {
            'name': _("Knockoff Journal"),
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'context': {'create': False},
            'view_mode': 'form',
            'res_id': self.move_knockoff_id.id,
        }
    
    def button_open_writeoff(self):
        ''' Redirect the user to this payment journal.
        :return:    An action on account.move.
        '''
        self.ensure_one()
        return {
            'name': _("Writeoff Journal"),
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'context': {'create': False},
            'view_mode': 'form',
            'res_id': self.move_writeoff_id.id,
        }

    def action_open_payment(self):
        self.ensure_one()
        return {
            'name': _('Payment'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'account.payment',
            'res_id': self.payment_id.id,
            'target': 'current',
        }

    @api.onchange('invoice_type')
    def _onchange_invoice_type(self):
        for record in self:
            record.move_type = record.invoice_type

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('sgeede.payment.distribution') or 'New'
        return super(SGEEDEPaymentDistribution, self).create(vals_list)


    # Helper untuk format angka ke style Indonesia
    def _format_number_id(self, number):
        """Format number to Indonesian style: 7.500.000"""
        formatted = '{:,.2f}'.format(number)
        formatted = formatted.replace(',', 'X').replace('.', ',').replace('X', '.')
        # Hapus ,00 jika desimal nol
        if formatted.endswith(',00'):
            formatted = formatted[:-3]
        return formatted

    @api.constrains('distribution_line_ids', 'payment_amount')
    def _check_total_payment_amount(self):
        for rec in self:
            total_lines = sum(line.payment_amount for line in rec.distribution_line_ids)
            if total_lines > rec.payment_amount:
                raise ValidationError(_(
                    "The total distributed amount (%s) cannot exceed the total payment amount (%s)."
                ) % (rec._format_number_id(total_lines), rec._format_number_id(rec.payment_amount)))

    @api.onchange('distribution_line_ids', 'payment_amount')
    def _onchange_check_payment_amount(self):
        for rec in self:
            total_lines = sum(line.payment_amount for line in rec.distribution_line_ids)
            if total_lines > rec.payment_amount:
                return {
                    'warning': {
                        'title': _('Warning'),
                        'message': _(
                            "The total distributed amount (%s) exceeds the total payment amount (%s)."
                        ) % (rec._format_number_id(total_lines), rec._format_number_id(rec.payment_amount))
                    }
                }

    def make_payment_distribution(self):
        self.ensure_one()
        payment_vals = {}
        partner_id = self.partner_id.id

        amount = self.payment_amount - sum(self.distribution_line_ids.mapped('payment_amount'))

        if amount > 0:
            wizard = self.env['sgeede.writeoff.payment.wizard'].with_context(
                active_model='sgeede.payment.distribution',
                active_ids=self.ids,
            ).new({})
            return wizard._action_open_wizard()
        
        else:
            vals = {
                'out_invoice': {'payment_type': 'inbound', 'partner_type': 'customer'},
                'in_invoice': {'payment_type': 'outbound', 'partner_type': 'supplier'},
                'in_refund': {'payment_type': 'inbound', 'partner_type': 'supplier'},
                'out_refund': {'payment_type': 'outbound', 'partner_type': 'customer'}
            }
            
            payment_vals.update(vals[self.invoice_type])
            payment_vals.update({
                'partner_id': partner_id or False,
                'journal_id': self.journal_id.id if self.journal_id else False,
                'date': self.payment_date or fields.Date.context_today(self),
                'currency_id': self.currency_id.id,
                'memo': self.reference
            })

            has_partial = any(j.invoice_total != j.payment_amount for j in self.distribution_line_ids)
            if has_partial:
                debit_total = self.payment_amount
                payment_lines = []

                payment_lines.append((0, 0, {
                    'name': f'Payment {self.name}',
                    'account_id': self.journal_id.default_account_id.id,
                    'debit': debit_total,
                    'credit': 0.0,
                    'partner_id': self.partner_id.id,
                    'currency_id': self.currency_id.id,
                }))

                partner_account = (
                    self.partner_id.property_account_receivable_id
                    if self.invoice_type in ['out_invoice', 'out_refund']
                    else self.partner_id.property_account_payable_id
                )
                for line in self.distribution_line_ids:
                    payment_lines.append((0, 0, {
                        'name': line.invoice_id.name or 'Partial Payment',
                        'account_id': partner_account.id,
                        'debit': 0.0,
                        'credit': line.payment_amount,
                        'partner_id': self.partner_id.id,
                        'currency_id': self.currency_id.id,
                        'sgeede_invoice_id': line.invoice_id.id,
                    }))

                payment_vals.update({
                    'amount': debit_total,
                    'line_ids': payment_lines,
                })
            else:
                payment_vals.update({
                    'amount': self.payment_amount,
                    'payment_method_id': self.env.ref('account.account_payment_method_manual_in').id
                        if self.invoice_type in ['out_invoice', 'in_refund']
                        else self.env.ref('account.account_payment_method_manual_out').id,
                })

            payment = self.env['account.payment'].create(payment_vals)
            partner_account = self.partner_id.property_account_receivable_id if self.invoice_type in ['out_invoice', 'out_refund'] else\
                self.partner_id.property_account_payable_id
            if payment:
                payment.action_post()
                self.write({'payment_id': payment.id})
                
                lines = self.distribution_line_ids
                for line in lines:
                    move_lines = line.invoice_id.mapped('line_ids')
                    
                    invoice_aml = move_lines.filtered(lambda l: l.account_id == partner_account)
                    payment_aml = payment.move_id.line_ids.filtered(lambda l: l.account_id == partner_account)
                    if len(payment_aml) > 1:
                        payment_aml = payment_aml.filtered(lambda l: l.sgeede_invoice_id == line.invoice_id)
                    if line.invoice_total == line.payment_amount: 
                        aml_obj = invoice_aml + payment_aml
                        self.env['account.move.line']._reconcile_plan([aml_obj])
                    else:
                        partial_val = {
                            "amount": line.payment_amount,
                            "debit_amount_currency": line.payment_amount,
                            "credit_amount_currency": line.payment_amount,
                            "debit_move_id": invoice_aml.id,
                            "credit_move_id": payment_aml.id
                        }
                        self.env['account.partial.reconcile'].create(partial_val)
                self.state = 'done'

    #function untuk make payment distribution advance
    # def make_payment_advance(self):
    #     pass

    def make_payment_advance(self):
        ctx = self.env.context
        amount_diff = 0
        account_move_line_obj_ar = self.env['account.move.line']
        account_move_line_obj_ap = self.env['account.move.line']
        account_move_line_obj_voucher = self.env['account.move.line']
        account_move_line_obj_ar_cn = self.env['account.move.line']
        account_move_obj = self.env['account.move']
        if self.payment_type == 'inbound':
            if not self.select_move_knockoff_bill_ids and not self.account_writeoff_ids and not self.select_credit_note_ids:
                check_diff = self.payment_amount - self.sum_total_invoice
                if check_diff > 0:
                    raise UserError(_('You can not post to Pro-Forma a voucher with Total amount = %s Difference amount is %s, You may enter deposit amount or knock off line or knock off deposit line or write off line.', self.payment_amount, check_diff))
                else:
                    if self.payment_amount == 0:
                        raise UserError(_('You can not post to Pro-Forma a voucher with Total amount = %s Difference amount is %s, You may enter deposit amount or knock off line or knock off deposit line or write off line.', self.payment_amount, check_diff))
                    payment_create = self.action_create_account_payment()
                    for rec_inv_residual in self.select_move_ids:
                        reconcile_voucher = (payment_create.move_id.line_ids + rec_inv_residual.line_ids).filtered(lambda line: line.account_id.reconcile and line.account_id.account_type in ('asset_receivable'))
                        account_move_line_obj_voucher |= reconcile_voucher
                    
                    if account_move_line_obj_voucher:
                        account_move_line_obj_voucher.reconcile()
            else:
                if (self.select_move_knockoff_bill_ids and self.account_writeoff_ids and self.select_credit_note_ids) or (self.select_move_knockoff_bill_ids and self.account_writeoff_ids) or (self.select_credit_note_ids and self.account_writeoff_ids):
                    residue = ((self.payment_amount - self.sum_total_invoice) + (self.sum_total_credit_note + self.sum_total_knockoff_bill))

                    payment_residu = self.payment_amount - self.sum_total_invoice
                    if self.payment_amount > self.sum_total_invoice:
                        check_diff = self.payment_amount - self.sum_total_invoice
                        raise UserError(_('You can not post to Pro-Forma a voucher with Total amount = %s Difference amount is %s, You may enter deposit amount or knock off line or knock off deposit line or write off line.', self.payment_amount, check_diff))
                    elif residue != 0 and residue == self.amount_writeoff:
                        if self.payment_amount == 0:
                            amount = self.sum_total_invoice
                            prepare_reconcile = self.action_prepare_inv_crenote_knockoffbill_writeoff(amount)
                        else:
                            payment_create = self.action_create_account_payment()
                            new_payment_move_line = self.action_reconcile_voucher_invoice(payment_create)
                            amount = sum(rec_inv.amount_residual for rec_inv in self.select_move_ids if rec_inv.amount_residual > 0)
                            prepare_reconcile = self.action_prepare_inv_crenote_knockoffbill_writeoff(amount)
                    else:
                        raise UserError(_('There are still remaining payments that have not been distributed!.'))

                elif self.select_move_knockoff_bill_ids and self.select_credit_note_ids:
                    amount_knockoff = 0
                    payment_residu = self.payment_amount - self.sum_total_invoice
                    if self.payment_amount > self.sum_total_invoice:
                        raise UserError(_('You can not post to Pro-Forma a voucher with Total amount = %s Difference amount is %s, You may enter deposit amount or knock off line or knock off deposit line or write off line.', self.payment_amount, payment_residu))
                    elif self.payment_amount == 0:

                        ar_diff = self.sum_total_invoice - self.sum_total_credit_note
                        reconcile_cn_invoice = self.action_reconcile_crenote_invoice()
                        if ar_diff > 0:
                            if ar_diff > self.sum_total_knockoff_bill:
                                amount_knockoff = -1 * self.sum_total_knockoff_bill
                            elif ar_diff <= self.sum_total_knockoff_bill:
                                amount_knockoff = -1 * ar_diff
                            if amount_knockoff != 0:
                                knockoff_line = self.action_prepare_knockoff_bill_invoice_line(amount_knockoff)
                        elif ar_diff < 0:
                            raise UserError(_('The nominal value of the credit note cannot be greater than the nominal value of the invoice, please do write off!'))

                    elif self.payment_amount != 0:
                        payment_create = self.action_create_account_payment()
                        reconcile_voucher_invoice = self.action_reconcile_voucher_invoice(payment_create)
                        if payment_residu < 0:
                            inv_residu = sum(rec_inv.amount_residual for rec_inv in self.select_move_ids if rec_inv.amount_residual > 0)
                            ar_diff = inv_residu - self.sum_total_credit_note
                            reconcile_cn_invoice = self.action_reconcile_crenote_invoice()
                            if ar_diff > 0:
                                if ar_diff > self.sum_total_knockoff_bill:
                                    amount_knockoff = -1 * self.sum_total_knockoff_bill
                                elif ar_diff <= self.sum_total_knockoff_bill:
                                    amount_knockoff = -1 * ar_diff
                                if amount_knockoff != 0:
                                    knockoff_line = self.action_prepare_knockoff_bill_invoice_line(amount_knockoff)
                            elif ar_diff < 0:
                                raise UserError(_('The nominal value of the credit note cannot be greater than the nominal value of the invoice, please do write off!'))
                elif self.select_credit_note_ids:
                    payment_residu = self.payment_amount - self.sum_total_invoice
                    amount_knockoff = 0
                    if self.payment_amount > self.sum_total_invoice:
                        raise UserError(_('You can not post to Pro-Forma a voucher with Total amount = %s Difference amount is %s, You may enter deposit amount or knock off line or knock off deposit line or write off line.', self.payment_amount, payment_residu))
                    elif self.payment_amount == 0:
                        knockoff_line = self.action_reconcile_crenote_invoice()
                    else:
                        payment_create = self.action_create_account_payment()
                        reconcile_voucher_invoice = self.action_reconcile_voucher_invoice(payment_create)
                        if payment_residu:
                            reconcile_cn_invoice = self.action_reconcile_crenote_invoice()

                elif self.select_move_knockoff_bill_ids:
                    payment_residu = self.payment_amount - self.sum_total_invoice
                    amount_knockoff = 0
                    if self.payment_amount > self.sum_total_invoice:
                        raise UserError(_('You can not post to Pro-Forma a voucher with Total amount = %s Difference amount is %s, You may enter deposit amount or knock off line or knock off deposit line or write off line.', self.payment_amount, payment_residu))
                    elif self.payment_amount == 0:
                        if self.sum_total_invoice > self.sum_total_knockoff_bill:
                            amount_knockoff = -1 * self.sum_total_knockoff_bill
                        elif self.sum_total_invoice <= self.sum_total_knockoff_bill:
                            amount_knockoff = -1 * self.sum_total_invoice
                        knockoff_line = self.action_prepare_knockoff_bill_invoice_line(amount_knockoff)
                    else:
                        payment_create = self.action_create_account_payment()
                        reconcile_voucher_invoice = self.action_reconcile_voucher_invoice(payment_create)
                        #####RESIDU
                        if payment_residu < 0:
                            inv_residu = sum(res_inv.amount_residual for res_inv in self.select_move_ids if res_inv.amount_residual > 0)
                            ar_diff = inv_residu - self.sum_total_knockoff_bill
                            if ar_diff > 0:
                                amount_knockoff = -1 * self.sum_total_knockoff_bill
                            elif ar_diff <= 0:
                                amount_knockoff = ar_diff
                            knockoff_line = self.action_prepare_knockoff_bill_invoice_line(amount_knockoff)

                elif self.amount_writeoff:
                    payment_residu = self.payment_amount - self.sum_total_invoice
                    if payment_residu > 0 and self.amount_writeoff < payment_residu or payment_residu < self.amount_writeoff:
                        raise UserError(_('You cannot write off more than the remaining receipt voucher.'))
                    else:
                        if not self.payment_amount == 0:
                            payment_create = self.action_create_account_payment()
                            payment_create.action_draft()
                            new_payment_move_line = []
                            for move_lines in payment_create.move_id.line_ids:
                                if move_lines.account_id.account_type == 'asset_receivable':
                                    total_ar_writeoff = move_lines.amount_currency + self.amount_writeoff
                                    new_payment_move_line.append((0, 0, {
                                        'name': move_lines.name,
                                        'account_id': move_lines.account_id.id,
                                        'partner_id': move_lines.partner_id.id,
                                        'currency_id': move_lines.currency_id.id,
                                        'amount_currency': total_ar_writeoff ,
                                        'balance': total_ar_writeoff,
                                    }))
                                else:
                                    new_payment_move_line.append((0, 0, {
                                        'name': move_lines.name,
                                        'account_id': move_lines.account_id.id,
                                        'partner_id': move_lines.partner_id.id,
                                        'currency_id': move_lines.currency_id.id,
                                        'amount_currency': move_lines.amount_currency,
                                        'balance': move_lines.balance,
                                    }))
                            for rec_writeoff in self.account_writeoff_ids:
                                new_payment_move_line.append((0, 0, {
                                    'name': rec_writeoff.name,
                                    'account_id': rec_writeoff.account_id.id,
                                    'partner_id': self.partner_id.id,
                                    'currency_id': self.currency_id.id,
                                    'amount_currency': -rec_writeoff.amount,
                                    'balance': -rec_writeoff.amount,
                                }))
                            
                            payment_create.move_id.line_ids.unlink()
                            if new_payment_move_line:
                                payment_create.move_id.write({'line_ids': new_payment_move_line + [(4, l.id) for l in payment_create.move_id.line_ids]})
                                payment_create.action_post()

                            for rec_invoice_tot in self.select_move_ids:
                                reconcile_voucher = (payment_create.move_id.line_ids + rec_invoice_tot.line_ids).filtered(lambda line: line.account_id.reconcile and line.account_id.account_type in ('asset_receivable') and not line.reconciled)
                                account_move_line_obj_voucher |= reconcile_voucher
                            
                            if account_move_line_obj_voucher:
                                account_move_line_obj_voucher.reconcile()
                        else:
                            raise UserError(_('You cannot write off more than the remaining receipt voucher.'))
        else:
            # FUNCTION UNTUK VENDOR PAYMENT
            if not self.select_move_knockoff_invoice_ids and not self.account_writeoff_ids and not self.select_refund_ids:
                check_diff = self.payment_amount - self.sum_total_bill
                if check_diff > 0:
                    raise UserError(_('You can not post to Pro-Forma a voucher with Total amount = %s Difference amount is %s, You may enter deposit amount or knock off line or knock off deposit line or write off line.', self.payment_amount, check_diff))
                else:
                    if self.payment_amount == 0:
                        raise UserError(_('You can not post to Pro-Forma a voucher with Total amount = %s Difference amount is %s, You may enter deposit amount or knock off line or knock off deposit line or write off line.', self.payment_amount, check_diff))
                    payment_create = self.action_create_account_payment()
                    for rec_bill_residual in self.select_move_bill_ids:
                        reconcile_voucher = (payment_create.move_id.line_ids + rec_bill_residual.line_ids).filtered(lambda line: line.account_id.reconcile and line.account_id.account_type in ('liability_payable'))
                        account_move_line_obj_voucher |= reconcile_voucher
                    
                    if account_move_line_obj_voucher:
                        account_move_line_obj_voucher.reconcile()
            else:
                if (self.select_move_knockoff_invoice_ids and self.account_writeoff_ids and self.select_refund_ids) or (self.select_move_knockoff_invoice_ids and self.account_writeoff_ids) or (self.select_refund_ids and self.account_writeoff_ids):
                    residue = ((self.payment_amount - self.sum_total_bill) + (self.sum_total_refund + self.sum_total_knockoff_invoice))

                    if self.payment_amount > self.sum_total_bill:
                        check_diff = self.payment_amount - self.sum_total_bill
                        raise UserError(_('You can not post to Pro-Forma a voucher with Total amount = %s Difference amount is %s, You may enter deposit amount or knock off line or knock off deposit line or write off line.', self.payment_amount, check_diff))
                    elif residue != 0 and residue == self.amount_writeoff:
                        if self.payment_amount == 0:
                            amount = self.sum_total_bill
                            prepare_reconcile = self.action_prepare_bill_refund_knockoffinvoice_writeoff(amount)
                        else:
                            payment_create = self.action_create_account_payment()
                            new_payment_move_line = self.action_reconcile_voucher_bill(payment_create)
                            amount = sum(rec_inv.amount_residual for rec_inv in self.select_move_bill_ids)
                            prepare_reconcile = self.action_prepare_bill_refund_knockoffinvoice_writeoff(amount)
                    else:
                        raise UserError(_('There are still remaining payments that have not been distributed!.'))

                elif self.select_move_knockoff_invoice_ids and self.select_refund_ids:
                    amount_knockoff = 0
                    payment_residu = self.payment_amount - self.sum_total_bill
                    if self.payment_amount > self.sum_total_bill:
                        raise UserError(_('You can not post to Pro-Forma a voucher with Total amount = %s Difference amount is %s, You may enter deposit amount or knock off line or knock off deposit line or write off line.', self.payment_amount, payment_residu))
                    elif self.payment_amount == 0:

                        ap_diff = self.sum_total_bill - self.sum_total_refund
                        reconcile_refund_bill = self.action_reconcile_refund_bill()
                        if ap_diff > 0:
                            if ap_diff > self.sum_total_knockoff_invoice:
                                amount_knockoff = self.sum_total_knockoff_invoice
                            elif ap_diff <= self.sum_total_knockoff_invoice:
                                amount_knockoff = ap_diff
                            if amount_knockoff != 0:
                                knockoff_line = self.action_prepare_knockoff_invoice_bill_line(amount_knockoff)
                        elif ap_diff < 0:
                            raise UserError(_('The nominal value of the refund cannot be greater than the nominal value of the bill, please do write off!'))
                    elif self.payment_amount != 0:
                        payment_create = self.action_create_account_payment()
                        reconcile_voucher_bill = self.action_reconcile_voucher_bill(payment_create)
                        if payment_residu < 0:
                            bill_residu = sum(rec_bill.amount_residual for rec_bill in self.select_move_bill_ids if rec_bill.amount_residual > 0)
                            ap_diff = bill_residu - self.sum_total_refund
                            reconcile_refund_bill = self.action_reconcile_refund_bill()
                            if ap_diff > 0:
                                if ap_diff > self.sum_total_knockoff_invoice:
                                    amount_knockoff = self.sum_total_knockoff_invoice
                                elif ap_diff <= self.sum_total_knockoff_invoice:
                                    amount_knockoff = ap_diff
                                if amount_knockoff != 0:
                                    knockoff_line = self.action_prepare_knockoff_invoice_bill_line(amount_knockoff)
                            elif ap_diff < 0:
                                raise UserError(_('The nominal value of the refund cannot be greater than the nominal value of the bill, please do write off!'))

                elif self.select_refund_ids:
                    payment_residu = self.payment_amount - self.sum_total_bill
                    amount_knockoff = 0
                    if self.payment_amount > self.sum_total_bill:
                        raise UserError(_('You can not post to Pro-Forma a voucher with Total amount = %s Difference amount is %s, You may enter deposit amount or knock off line or knock off deposit line or write off line.', self.payment_amount, payment_residu))
                    elif self.payment_amount == 0:
                        knockoff_line = self.action_reconcile_refund_bill()
                    else:
                        payment_create = self.action_create_account_payment()
                        reconcile_voucher_invoice = self.action_reconcile_voucher_bill(payment_create)
                        if payment_residu:
                            reconcile_refund_bill = self.action_reconcile_refund_bill()
                
                elif self.select_move_knockoff_invoice_ids:
                    payment_residu = self.payment_amount - self.sum_total_bill
                    amount_knockoff = 0
                    if self.payment_amount > self.sum_total_bill:
                        raise UserError(_('You can not post to Pro-Forma a voucher with Total amount = %s Difference amount is %s, You may enter deposit amount or knock off line or knock off deposit line or write off line.', self.payment_amount, payment_residu))
                    elif self.payment_amount == 0:
                        if self.sum_total_bill > self.sum_total_knockoff_invoice:
                            amount_knockoff = self.sum_total_knockoff_invoice
                        elif self.sum_total_bill < self.sum_total_knockoff_invoice:
                            amount_knockoff = self.sum_total_bill
                        knockoff_line = self.action_prepare_knockoff_invoice_bill_line(amount_knockoff)
                    else:
                        payment_create = self.action_create_account_payment()
                        reconcile_voucher_invoice = self.action_reconcile_voucher_bill(payment_create)
                        if payment_residu < 0:
                            bill_residu = sum(rec_bill.amount_residual for rec_bill in self.select_move_bill_ids if rec_bill.amount_residual > 0)
                            ap_diff = bill_residu - self.sum_total_knockoff_invoice
                            if ap_diff > 0:
                                amount_knockoff = self.sum_total_knockoff_invoice
                            elif ap_diff <= 0:
                                amount_knockoff = bill_residu
                            knockoff_line = self.action_prepare_knockoff_invoice_bill_line(amount_knockoff)

                elif self.amount_writeoff:
                    payment_residu = self.payment_amount - self.sum_total_bill
                    if payment_residu > 0 and self.amount_writeoff < payment_residu or payment_residu < self.amount_writeoff and self.payment_amount != 0:
                        raise UserError(_('You cannot write off more than the remaining payment voucher.'))
                    else:
                        if not self.payment_amount == 0:
                            payment_create = self.action_create_account_payment()
                            payment_create.action_draft()
                            new_payment_move_line = []
                            for move_lines in payment_create.move_id.line_ids:
                                if move_lines.account_id.account_type == 'liability_payable':
                                    total_ap_writeoff = move_lines.amount_currency - self.amount_writeoff
                                    new_payment_move_line.append((0, 0, {
                                        'name': move_lines.name,
                                        'account_id': move_lines.account_id.id,
                                        'partner_id': move_lines.partner_id.id,
                                        'currency_id': move_lines.currency_id.id,
                                        'amount_currency': total_ap_writeoff ,
                                        'balance': total_ap_writeoff,
                                    }))
                                else:
                                    new_payment_move_line.append((0, 0, {
                                        'name': move_lines.name,
                                        'account_id': move_lines.account_id.id,
                                        'partner_id': move_lines.partner_id.id,
                                        'currency_id': move_lines.currency_id.id,
                                        'amount_currency': move_lines.amount_currency,
                                        'balance': move_lines.balance,
                                    }))
                            for rec_writeoff in self.account_writeoff_ids:
                                new_payment_move_line.append((0, 0, {
                                    'name': rec_writeoff.name,
                                    'account_id': rec_writeoff.account_id.id,
                                    'partner_id': self.partner_id.id,
                                    'currency_id': self.currency_id.id,
                                    'amount_currency': rec_writeoff.amount,
                                    'balance': rec_writeoff.amount,
                                }))
                            
                            payment_create.move_id.line_ids.unlink()
                            if new_payment_move_line:
                                payment_create.move_id.write({'line_ids': new_payment_move_line + [(4, l.id) for l in payment_create.move_id.line_ids]})
                                payment_create.action_post()

                            for rec_bill_tot in self.select_move_bill_ids:
                                reconcile_voucher = (payment_create.move_id.line_ids + rec_bill_tot.line_ids).filtered(lambda line: line.account_id.reconcile and line.account_id.account_type in ('liability_payable') and not line.reconciled)
                                account_move_line_obj_voucher |= reconcile_voucher
                            
                            if account_move_line_obj_voucher:
                                account_move_line_obj_voucher.reconcile()
                        else:
                            raise UserError(_('You cannot write off more than the remaining payment voucher.'))

        self.state = 'done'

    # FUNCTION EKSEKUSI RECONCILEKAN CUSTOMER PAYMENT
    def action_prepare_inv_crenote_knockoffbill_writeoff(self, amount):
        residu = 0
        if self.select_credit_note_ids and not self.select_move_knockoff_bill_ids:
            reconcile_cn_invoice = self.action_reconcile_crenote_invoice_writeoff(amount)
        elif self.select_credit_note_ids:
            residu = amount - self.sum_total_credit_note
            reconcile_cn_invoice = self.action_reconcile_crenote_invoice()
        
        if self.select_move_knockoff_bill_ids:
            if residu > 0:
                inv_residu_two = sum(rec_inv.amount_residual for rec_inv in self.select_move_ids if rec_inv.amount_residual > 0)
                amount_ar = inv_residu_two
                amount_ap = self.sum_total_knockoff_bill
                new_line_knockoff_writeoff = self.action_knockoff_invoice_and_writeoff(amount_ar, amount_ap)
            elif residu < 0:
                cn_residu = sum(rec_cn_due.amount_residual for rec_cn_due in self.select_credit_note_ids if rec_cn_due.amount_residual > 0)
                amount_ar = cn_residu
                amount_ap = self.sum_total_knockoff_bill
                new_line_knockoff_writeoff = self.action_knockoff_crenote_and_writeoff(amount_ar, amount_ap)
            else:
                if not self.select_credit_note_ids:
                    last_inv_residu = sum(rec_inv.amount_residual for rec_inv in self.select_move_ids if rec_inv.amount_residual > 0)
                    amount_due = last_inv_residu - self.sum_total_knockoff_bill
                    if amount_due < 0:
                        amount_knockoff = -1 * last_inv_residu
                        knockoff_line = self.action_prepare_knockoff_bill_invoice_line(amount_knockoff)
                        amount_ap = sum(rec_knockoff_bill.amount_residual for rec_knockoff_bill in self.select_move_knockoff_bill_ids if rec_knockoff_bill.amount_residual > 0)
                        new_line_knockoff_writeoff = self.action_knockoffbill_and_writeoff(amount_ap)
                    else:
                        amount_knockoff = -1 * self.sum_total_knockoff_bill
                        knockoff_line = self.action_prepare_knockoff_bill_invoice_line(amount_knockoff)
                        inv_residu_writeoff = sum(rec_inv.amount_residual for rec_inv in self.select_move_ids if rec_inv.amount_residual > 0)
                        new_line_invoice_writeoff = self.action_reconcile_sisa_invoice_writeoff_setelah_knockoff(inv_residu_writeoff)
                        # harusnya ini nanti writeoff sisa invoicenya
                else:
                    amount_ap = self.sum_total_knockoff_bill
                    new_line_knockoff_writeoff = self.action_knockoffbill_and_writeoff(amount_ap)
    def action_reconcile_sisa_invoice_writeoff_setelah_knockoff(self, amount_due):
        account_move_line_obj_ar = self.env['account.move.line']
        account_move_obj = self.env['account.move']
        # return new_payment_move_line
        lines_to_reconcile_knockoff = self.select_move_ids.mapped('line_ids').filtered(lambda line: line.account_id.reconcile and line.account_id.account_type == 'asset_receivable').mapped('account_id')

        new_lines_vals = [
            (0, 0,{
                'name': _('Writeoff from %s voucher %s', lines_to_reconcile_knockoff.display_name, self.name),
                'account_id': lines_to_reconcile_knockoff.id,
                'partner_id': self.partner_id.id,
                'currency_id': self.currency_id.id,
                'amount_currency': -amount_due,
                'balance': -amount_due,
            }),
        ]
        for rec_writeoff in self.account_writeoff_ids:
            new_lines_vals.append((0, 0, {
                'name': rec_writeoff.name,
                'account_id': rec_writeoff.account_id.id,
                'partner_id': self.partner_id.id,
                'currency_id': self.currency_id.id,
                'amount_currency': -rec_writeoff.amount,
                'balance': -rec_writeoff.amount,
            }))
        
        
        new_move_id = account_move_obj.create({
            'journal_id': self.journal_id.id,
            'line_ids': new_lines_vals,
            'date': self.payment_date,
            'move_type': 'entry',
            'ref': self.reference

        })
        new_move_id.action_post()
        self.write({'move_writeoff_id': new_move_id.id})
        for rec_inv in self.select_move_ids:
            reconcile_writeoff_inv = (new_move_id.line_ids + rec_inv.line_ids).filtered(lambda line: line.account_id.reconcile and line.account_id.account_type in ('asset_receivable') and not line.reconciled)
            account_move_line_obj_ar |= reconcile_writeoff_inv

        if account_move_line_obj_ar:
            account_move_line_obj_ar.reconcile()

    # def action_prepare_writeoff_line(self):
    #     new_payment_move_line = []
    #     for move_lines in self.move_id.line_ids:
    #         if move_lines.account_id.account_type == 'asset_receivable':
    #             total_ar_writeoff = move_lines.amount_currency + self.amount_writeoff
    #             new_payment_move_line.append((0, 0, {
    #                 'name': move_lines.name,
    #                 'account_id': move_lines.account_id.id,
    #                 'partner_id': move_lines.partner_id.id,
    #                 'currency_id': move_lines.currency_id.id,
    #                 'amount_currency': total_ar_writeoff ,
    #                 'balance': total_ar_writeoff,
    #             }))
    #         else:
    #             new_payment_move_line.append((0, 0, {
    #                 'name': move_lines.name,
    #                 'account_id': move_lines.account_id.id,
    #                 'partner_id': move_lines.partner_id.id,
    #                 'currency_id': move_lines.currency_id.id,
    #                 'amount_currency': move_lines.amount_currency,
    #                 'balance': move_lines.balance,
    #             }))
    #     for rec_writeoff in self.account_writeoff_ids:
    #         new_payment_move_line.append((0, 0, {
    #             'name': rec_writeoff.name,
    #             'account_id': rec_writeoff.account_id.id,
    #             'partner_id': self.partner_id.id,
    #             'currency_id': self.currency_id.id,
    #             'amount_currency': -rec_writeoff.amount,
    #             'balance': -rec_writeoff.amount,
    #         }))
        
    #     return new_payment_move_line
    
    def action_reconcile_voucher_invoice(self, payment_create):
        account_move_line_obj_voucher = self.env['account.move.line']
        for rec_invoice_tot in self.select_move_ids:
            reconcile_voucher = (payment_create.move_id.line_ids + rec_invoice_tot.line_ids).filtered(lambda line: line.account_id.reconcile and line.account_id.account_type in ('asset_receivable') and not line.reconciled)
            account_move_line_obj_voucher |= reconcile_voucher
        
        if account_move_line_obj_voucher:
            account_move_line_obj_voucher.reconcile()

    def action_reconcile_crenote_invoice(self):
        account_move_line_obj_ar_cn = self.env['account.move.line']
        for rec_inv in self.select_move_ids:
            ar_inv = (rec_inv.line_ids).filtered(lambda line: line.account_id.reconcile and line.account_id.account_type in ('asset_receivable') and not line.reconciled)
            account_move_line_obj_ar_cn |= ar_inv
        
        for rec_crenote in self.select_credit_note_ids:
            ar_crenote = (rec_crenote.line_ids).filtered(lambda line: line.account_id.reconcile and line.account_id.account_type in ('asset_receivable') and not line.reconciled)
            account_move_line_obj_ar_cn |= ar_crenote

        if account_move_line_obj_ar_cn:
            account_move_line_obj_ar_cn.reconcile()

    def action_reconcile_crenote_invoice_writeoff(self, amount_residu_inv):
        account_move_line_obj_ar = self.env['account.move.line']
        account_move_line_obj_ar_cn = self.env['account.move.line']
        account_move_obj = self.env['account.move']
        
        lines_to_reconcile_invoice = self.select_move_ids.mapped('line_ids').filtered(lambda line: line.account_id.reconcile and line.account_id.account_type == 'asset_receivable').mapped('account_id')
        
        for rec_inv in self.select_move_ids:
            ar_inv = (rec_inv.line_ids).filtered(lambda line: line.account_id.reconcile and line.account_id.account_type in ('asset_receivable') and not line.reconciled)
            account_move_line_obj_ar_cn |= ar_inv
        
        for rec_crenote in self.select_credit_note_ids:
            ar_crenote = (rec_crenote.line_ids).filtered(lambda line: line.account_id.reconcile and line.account_id.account_type in ('asset_receivable') and not line.reconciled)
            account_move_line_obj_ar_cn |= ar_crenote

        if account_move_line_obj_ar_cn:
            account_move_line_obj_ar_cn.reconcile()
        if amount_residu_inv > self.sum_total_credit_note:
            amount_ar_inv = sum(rec_inv.amount_residual for rec_inv in self.select_move_ids if rec_inv.amount_residual > 0)
            new_lines_vals = [
                (0, 0, {
                    'name': _('Knockoff to %s voucher %s', lines_to_reconcile_invoice.display_name, self.name),
                    'account_id': lines_to_reconcile_invoice.id,
                    'partner_id': self.partner_id.id,
                    'currency_id': self.currency_id.id,
                    'amount_currency': -amount_ar_inv,
                    'balance': -amount_ar_inv,
                }),
            ]
        else:
            amount_ar_cn = sum(rec_cn.amount_residual for rec_cn in self.select_credit_note_ids if rec_cn.amount_residual > 0)
            new_lines_vals = [
                (0, 0, {
                    'name': _('Knockoff to %s voucher %s', lines_to_reconcile_invoice.display_name, self.name),
                    'account_id': lines_to_reconcile_invoice.id,
                    'partner_id': self.partner_id.id,
                    'currency_id': self.currency_id.id,
                    'amount_currency': amount_ar_cn,
                    'balance': amount_ar_cn,
                }),
            ]
        for rec_writeoff in self.account_writeoff_ids:
            new_lines_vals.append((0, 0, {
                'name': rec_writeoff.name,
                'account_id': rec_writeoff.account_id.id,
                'partner_id': self.partner_id.id,
                'currency_id': self.currency_id.id,
                'amount_currency': -rec_writeoff.amount,
                'balance': -rec_writeoff.amount,
            }))
        
        new_move_id = account_move_obj.create({
            'journal_id': self.journal_id.id,
            'line_ids': new_lines_vals,
            'date': self.payment_date,
            'move_type': 'entry',
            'ref': self.reference,

        })
        new_move_id.action_post()
        self.write({'move_writeoff_id': new_move_id.id})
        if amount_residu_inv > self.sum_total_credit_note:
            for rec_inv in self.select_move_ids:
                reconcile_knockoff = (new_move_id.line_ids + rec_inv.line_ids).filtered(lambda line: line.account_id.reconcile and line.account_id.account_type in ('asset_receivable') and not line.reconciled)
                account_move_line_obj_ar |= reconcile_knockoff
            account_move_line_obj_ar.reconcile()
        else:
            for rec_cn in self.select_credit_note_ids:
                reconcile_knockoff = (new_move_id.line_ids + rec_cn.line_ids).filtered(lambda line: line.account_id.reconcile and line.account_id.account_type in ('asset_receivable') and not line.reconciled)
                account_move_line_obj_ar |= reconcile_knockoff
            account_move_line_obj_ar.reconcile()

        
    
    def action_knockoff_invoice_and_writeoff(self, amount_ar, amount_ap):
        account_move_line_obj_ar = self.env['account.move.line']
        account_move_line_obj_ap = self.env['account.move.line']
        account_move_obj = self.env['account.move']

        lines_to_reconcile_knockoff = self.select_move_knockoff_bill_ids.mapped('line_ids').filtered(lambda line: line.account_id.reconcile and line.account_id.account_type == 'liability_payable').mapped('account_id')

        lines_to_reconcile_invoice = self.select_move_ids.mapped('line_ids').filtered(lambda line: line.account_id.reconcile and line.account_id.account_type == 'asset_receivable').mapped('account_id')

        new_lines_vals = [
            (0, 0,{
                'name': _('Knockoff from %s voucher %s', lines_to_reconcile_knockoff.display_name, self.name),
                'account_id': lines_to_reconcile_knockoff.id,
                'partner_id': self.partner_id.id,
                'currency_id': self.currency_id.id,
                'amount_currency': amount_ap,
                'balance': amount_ap,
            }),
            (0, 0, {
                'name': _('Knockoff to %s voucher %s', lines_to_reconcile_invoice.display_name, self.name),
                'account_id': lines_to_reconcile_invoice.id,
                'partner_id': self.partner_id.id,
                'currency_id': self.currency_id.id,
                'amount_currency': -amount_ar,
                'balance': -amount_ar,
            }),
        ]
        for rec_writeoff in self.account_writeoff_ids:
            new_lines_vals.append((0, 0, {
                'name': rec_writeoff.name,
                'account_id': rec_writeoff.account_id.id,
                'partner_id': self.partner_id.id,
                'currency_id': self.currency_id.id,
                'amount_currency': -rec_writeoff.amount,
                'balance': -rec_writeoff.amount,
            }))
        
        
        new_move_id = account_move_obj.create({
            'journal_id': self.journal_id.id,
            'line_ids': new_lines_vals,
            'date': self.payment_date,
            'move_type': 'entry',
            'ref': self.reference,

        })
        new_move_id.action_post()
        self.write({'move_writeoff_id': new_move_id.id})
        for rec_inv in self.select_move_ids:
            reconcile_knockoff = (new_move_id.line_ids + rec_inv.line_ids).filtered(lambda line: line.account_id.reconcile and line.account_id.account_type in ('asset_receivable') and not line.reconciled)
            account_move_line_obj_ar |= reconcile_knockoff
        for rec_bill in self.select_move_knockoff_bill_ids:
            reconcile_knockoff = (new_move_id.line_ids + rec_bill.line_ids).filtered(lambda line: line.account_id.reconcile and line.account_id.account_type in ('liability_payable') and not line.reconciled)
            account_move_line_obj_ap |= reconcile_knockoff

        if account_move_line_obj_ar:
            account_move_line_obj_ar.reconcile()
        if account_move_line_obj_ap:
            account_move_line_obj_ap.reconcile()

    def action_knockoff_crenote_and_writeoff(self, amount_ar, amount_ap):
        account_move_line_obj_ap = self.env['account.move.line']
        account_move_line_obj_ar_cn = self.env['account.move.line']
        account_move_obj = self.env['account.move']

        lines_to_reconcile_knockoff = self.select_move_knockoff_bill_ids.mapped('line_ids').filtered(lambda line: line.account_id.reconcile and line.account_id.account_type == 'liability_payable').mapped('account_id')

        lines_to_reconcile_crenote = self.select_credit_note_ids.mapped('line_ids').filtered(lambda line: line.account_id.reconcile and line.account_id.account_type == 'asset_receivable').mapped('account_id')

        new_lines_vals = [
            (0, 0,{
                'name': _('Knockoff from %s voucher %s', lines_to_reconcile_knockoff.display_name, self.name),
                'account_id': lines_to_reconcile_knockoff.id,
                'partner_id': self.partner_id.id,
                'currency_id': self.currency_id.id,
                'amount_currency': amount_ap,
                'balance': amount_ap,
            }),
            (0, 0, {
                'name': _('Knockoff to %s voucher %s', lines_to_reconcile_crenote.display_name, self.name),
                'account_id': lines_to_reconcile_crenote.id,
                'partner_id': self.partner_id.id,
                'currency_id': self.currency_id.id,
                'amount_currency': amount_ar,
                'balance': amount_ar,
            }),
        ]
        for rec_writeoff in self.account_writeoff_ids:
            new_lines_vals.append((0, 0, {
                'name': rec_writeoff.name,
                'account_id': rec_writeoff.account_id.id,
                'partner_id': self.partner_id.id,
                'currency_id': self.currency_id.id,
                'amount_currency': -rec_writeoff.amount,
                'balance': -rec_writeoff.amount,
            }))
        
        
        new_move_id = account_move_obj.create({
            'journal_id': self.journal_id.id,
            'line_ids': new_lines_vals,
            'date': self.payment_date,
            'move_type': 'entry',
            'ref': self.reference,

        })
        new_move_id.action_post()
        self.write({'move_writeoff_id': new_move_id.id})
        for rec_inv in self.select_credit_note_ids:
            reconcile_knockoff = (new_move_id.line_ids + rec_inv.line_ids).filtered(lambda line: line.account_id.reconcile and line.account_id.account_type in ('asset_receivable') and not line.reconciled)
            account_move_line_obj_ar_cn |= reconcile_knockoff
        for rec_bill in self.select_move_knockoff_bill_ids:
            reconcile_knockoff = (new_move_id.line_ids + rec_bill.line_ids).filtered(lambda line: line.account_id.reconcile and line.account_id.account_type in ('liability_payable') and not line.reconciled)
            account_move_line_obj_ap |= reconcile_knockoff

        if account_move_line_obj_ar_cn:
            account_move_line_obj_ar_cn.reconcile()
        if account_move_line_obj_ap:
            account_move_line_obj_ap.reconcile()

    def action_knockoffbill_and_writeoff(self, amount_ap):
        account_move_line_obj_ap = self.env['account.move.line']
        account_move_obj = self.env['account.move']

        lines_to_reconcile_knockoff = self.select_move_knockoff_bill_ids.mapped('line_ids').filtered(lambda line: line.account_id.reconcile and line.account_id.account_type == 'liability_payable').mapped('account_id')

        new_lines_vals = [
            (0, 0,{
                'name': _('Knockoff from %s voucher %s', lines_to_reconcile_knockoff.display_name, self.name),
                'account_id': lines_to_reconcile_knockoff.id,
                'partner_id': self.partner_id.id,
                'currency_id': self.currency_id.id,
                'amount_currency': amount_ap,
                'balance': amount_ap,
            }),
        ]
        for rec_writeoff in self.account_writeoff_ids:
            new_lines_vals.append((0, 0, {
                'name': rec_writeoff.name,
                'account_id': rec_writeoff.account_id.id,
                'partner_id': self.partner_id.id,
                'currency_id': self.currency_id.id,
                'amount_currency': -rec_writeoff.amount,
                'balance': -rec_writeoff.amount,
            }))
        
        
        new_move_id = account_move_obj.create({
            'journal_id': self.journal_id.id,
            'line_ids': new_lines_vals,
            'date': self.payment_date,
            'move_type': 'entry',
            'ref': self.reference,

        })
        new_move_id.action_post()
        self.write({'move_writeoff_id': new_move_id.id})
        for rec_bill in self.select_move_knockoff_bill_ids:
            reconcile_knockoff = (new_move_id.line_ids + rec_bill.line_ids).filtered(lambda line: line.account_id.reconcile and line.account_id.account_type in ('liability_payable') and not line.reconciled)
            account_move_line_obj_ap |= reconcile_knockoff

        if account_move_line_obj_ap:
            account_move_line_obj_ap.reconcile()

    def action_prepare_knockoff_bill_invoice_line(self, amount_knockoff):
        account_move_line_obj_ar = self.env['account.move.line']
        account_move_line_obj_ap = self.env['account.move.line']
        account_move_obj = self.env['account.move']
        
        lines_to_reconcile_knockoff = self.select_move_knockoff_bill_ids.mapped('line_ids').filtered(lambda line: line.account_id.reconcile and line.account_id.account_type == 'liability_payable').mapped('account_id')

        lines_to_reconcile_invoice = self.select_move_ids.mapped('line_ids').filtered(lambda line: line.account_id.reconcile and line.account_id.account_type == 'asset_receivable').mapped('account_id')

        new_lines_vals = [
            (0, 0,{
                'name': _('Knockoff from %s voucher %s', lines_to_reconcile_knockoff.display_name, self.name),
                'account_id': lines_to_reconcile_knockoff.id,
                'partner_id': self.partner_id.id,
                'currency_id': self.currency_id.id,
                'amount_currency': -amount_knockoff,
                'balance': -amount_knockoff,
            }),
            (0, 0, {
                'name': _('Knockoff to %s voucher %s', lines_to_reconcile_invoice.display_name, self.name),
                'account_id': lines_to_reconcile_invoice.id,
                'partner_id': self.partner_id.id,
                'currency_id': self.currency_id.id,
                'amount_currency': amount_knockoff,
                'balance': amount_knockoff,
            }),
        ]
        new_move_id = account_move_obj.create({
            'journal_id': self.journal_id.id,
            'line_ids': new_lines_vals,
            'date': self.payment_date,
            'move_type': 'entry',
            'ref': self.reference,

        })
        new_move_id.action_post()
        self.write({'move_knockoff_id': new_move_id.id})

        for rec_inv in self.select_move_ids:
            reconcile_knockoff = (new_move_id.line_ids + rec_inv.line_ids).filtered(lambda line: line.account_id.reconcile and line.account_id.account_type in ('asset_receivable') and not line.reconciled)
            account_move_line_obj_ar |= reconcile_knockoff
        for rec_bill in self.select_move_knockoff_bill_ids:
            reconcile_knockoff = (new_move_id.line_ids + rec_bill.line_ids).filtered(lambda line: line.account_id.reconcile and line.account_id.account_type in ('liability_payable') and not line.reconciled)
            account_move_line_obj_ap |= reconcile_knockoff

        if account_move_line_obj_ar:
            account_move_line_obj_ar.reconcile()
        if account_move_line_obj_ap:
            account_move_line_obj_ap.reconcile()

    # FUNCTION UNTUK VENDOR PAYMENT
    def action_prepare_bill_refund_knockoffinvoice_writeoff(self, amount):
        residu = 0
        if self.select_refund_ids and not self.select_move_knockoff_invoice_ids:
            reconcile_refund_bill = self.action_reconcile_refund_bill_writeoff(amount)
        elif self.select_refund_ids:
            residu = amount - self.sum_total_refund
            reconcile_refund_bill = self.action_reconcile_refund_bill()

        if self.select_move_knockoff_invoice_ids:
            if residu > 0:
                inv_residu_two = sum(rec_inv.amount_residual for rec_inv in self.select_move_bill_ids if rec_inv.amount_residual > 0)
                amount_ar = inv_residu_two
                amount_ap = self.sum_total_knockoff_invoice
                new_line_knockoff_writeoff = self.action_knockoff_bill_and_writeoff(amount_ar, amount_ap)
            elif residu < 0:
                cn_residu = sum(rec_cn_due.amount_residual for rec_cn_due in self.select_refund_ids if rec_cn_due.amount_residual > 0)
                amount_ar = cn_residu
                amount_ap = self.sum_total_knockoff_invoice
                new_line_knockoff_writeoff = self.action_knockoff_refund_and_writeoff(amount_ar, amount_ap)
            else:
                if not self.select_refund_ids:
                    last_bill_residu = sum(rec_bill.amount_residual for rec_bill in self.select_move_bill_ids if rec_bill.amount_residual > 0)
                    amount_due = last_bill_residu - self.sum_total_knockoff_invoice
                    if amount_due < 0:
                        amount_knockoff = last_bill_residu
                        knockoff_line = self.action_prepare_knockoff_invoice_bill_line(amount_knockoff)
                        amount_ar = sum(rec_knockoff_invoice.amount_residual for rec_knockoff_invoice in self.select_move_knockoff_invoice_ids if rec_knockoff_invoice.amount_residual > 0)
                        new_line_knockoff_writeoff = self.action_knockoffinvoice_and_writeoff(amount_ar)
                    else:
                        amount_knockoff = self.sum_total_knockoff_invoice
                        knockoff_line = self.action_prepare_knockoff_invoice_bill_line(amount_knockoff)
                        bill_residu_writeoff = sum(rec_bill.amount_residual for rec_bill in self.select_move_bill_ids if rec_bill.amount_residual > 0)
                        new_line_invoice_writeoff = self.action_reconcile_sisa_bill_writeoff_setelah_knockoff(bill_residu_writeoff)
                else:
                    amount_ap = self.sum_total_knockoff_invoice
                    new_line_knockoff_writeoff = self.action_knockoffinvoice_and_writeoff(amount_ap)

    def action_reconcile_sisa_bill_writeoff_setelah_knockoff(self, amount_due):
        account_move_line_obj_ap = self.env['account.move.line']
        account_move_obj = self.env['account.move']
        # return new_payment_move_line
        lines_to_reconcile_knockoff = self.select_move_bill_ids.mapped('line_ids').filtered(lambda line: line.account_id.reconcile and line.account_id.account_type == 'liability_payable').mapped('account_id')

        new_lines_vals = [
            (0, 0,{
                'name': _('Writeoff from %s voucher %s', lines_to_reconcile_knockoff.display_name, self.name),
                'account_id': lines_to_reconcile_knockoff.id,
                'partner_id': self.partner_id.id,
                'currency_id': self.currency_id.id,
                'amount_currency': amount_due,
                'balance': amount_due,
            }),
        ]
        for rec_writeoff in self.account_writeoff_ids:
            new_lines_vals.append((0, 0, {
                'name': rec_writeoff.name,
                'account_id': rec_writeoff.account_id.id,
                'partner_id': self.partner_id.id,
                'currency_id': self.currency_id.id,
                'amount_currency': rec_writeoff.amount,
                'balance': rec_writeoff.amount,
            }))
        
        
        new_move_id = account_move_obj.create({
            'journal_id': self.journal_id.id,
            'line_ids': new_lines_vals,
            'date': self.payment_date,
            'move_type': 'entry',
            'ref': self.reference,

        })
        new_move_id.action_post()
        self.write({'move_writeoff_id': new_move_id.id})
        for rec_bill in self.select_move_bill_ids:
            reconcile_writeoff_inv = (new_move_id.line_ids + rec_bill.line_ids).filtered(lambda line: line.account_id.reconcile and line.account_id.account_type in ('liability_payable') and not line.reconciled)
            account_move_line_obj_ap |= reconcile_writeoff_inv

        if account_move_line_obj_ap:
            account_move_line_obj_ap.reconcile()

    def action_reconcile_refund_bill_writeoff(self, amount_residu_inv):
        account_move_line_obj_ap = self.env['account.move.line']
        account_move_line_obj_ap_refund = self.env['account.move.line']
        account_move_obj = self.env['account.move']
        
        lines_to_reconcile_invoice = self.select_move_bill_ids.mapped('line_ids').filtered(lambda line: line.account_id.reconcile and line.account_id.account_type == 'liability_payable').mapped('account_id')
        
        for rec_bill in self.select_move_bill_ids:
            ap_bill = (rec_bill.line_ids).filtered(lambda line: line.account_id.reconcile and line.account_id.account_type in ('liability_payable') and not line.reconciled)
            account_move_line_obj_ap_refund |= ap_bill
        
        for rec_ref in self.select_refund_ids:
            ap_ref = (rec_ref.line_ids).filtered(lambda line: line.account_id.reconcile and line.account_id.account_type in ('liability_payable') and not line.reconciled)
            account_move_line_obj_ap_refund |= ap_ref

        if account_move_line_obj_ap_refund:
            account_move_line_obj_ap_refund.reconcile()
        if amount_residu_inv > self.sum_total_refund:
            amount_ap_bill = sum(rec_bill.amount_residual for rec_bill in self.select_move_bill_ids if rec_bill.amount_residual > 0)
            new_lines_vals = [
                (0, 0, {
                    'name': _('Knockoff to %s voucher %s', lines_to_reconcile_invoice.display_name, self.name),
                    'account_id': lines_to_reconcile_invoice.id,
                    'partner_id': self.partner_id.id,
                    'currency_id': self.currency_id.id,
                    'amount_currency': -amount_ap_bill,
                    'balance': -amount_ap_bill,
                }),
            ]
        else:
            amount_ap_ref = sum(rec_refund.amount_residual for rec_refund in self.select_refund_ids if rec_refund.amount_residual > 0)
            new_lines_vals = [
                (0, 0, {
                    'name': _('Knockoff to %s voucher %s', lines_to_reconcile_invoice.display_name, self.name),
                    'account_id': lines_to_reconcile_invoice.id,
                    'partner_id': self.partner_id.id,
                    'currency_id': self.currency_id.id,
                    'amount_currency': amount_ap_ref,
                    'balance': amount_ap_ref,
                }),
            ]
        for rec_writeoff in self.account_writeoff_ids:
            new_lines_vals.append((0, 0, {
                'name': rec_writeoff.name,
                'account_id': rec_writeoff.account_id.id,
                'partner_id': self.partner_id.id,
                'currency_id': self.currency_id.id,
                'amount_currency': -rec_writeoff.amount,
                'balance': -rec_writeoff.amount,
            }))
        
        new_move_id = account_move_obj.create({
            'journal_id': self.journal_id.id,
            'line_ids': new_lines_vals,
            'date': self.payment_date,
            'move_type': 'entry',
            'ref': self.reference,

        })
        new_move_id.action_post()
        self.write({'move_writeoff_id': new_move_id.id})
        if amount_residu_inv > self.sum_total_refund:
            for rec_bill in self.select_move_bill_ids:
                reconcile_knockoff = (new_move_id.line_ids + rec_bill.line_ids).filtered(lambda line: line.account_id.reconcile and line.account_id.account_type in ('liability_payable') and not line.reconciled)
                account_move_line_obj_ap |= reconcile_knockoff
            account_move_line_obj_ap.reconcile()
        else:
            for rec_refund in self.select_refund_ids:
                reconcile_knockoff = (new_move_id.line_ids + rec_refund.line_ids).filtered(lambda line: line.account_id.reconcile and line.account_id.account_type in ('liability_payable') and not line.reconciled)
                account_move_line_obj_ap |= reconcile_knockoff
            account_move_line_obj_ap.reconcile()
    
    def action_reconcile_refund_bill(self):
        account_move_line_obj_ap_refund = self.env['account.move.line']
        for rec_bill in self.select_move_bill_ids:
            ap_bill = (rec_bill.line_ids).filtered(lambda line: line.account_id.reconcile and line.account_id.account_type in ('liability_payable') and not line.reconciled)
            account_move_line_obj_ap_refund |= ap_bill
        
        for rec_ref in self.select_refund_ids:
            ar_crenote = (rec_ref.line_ids).filtered(lambda line: line.account_id.reconcile and line.account_id.account_type in ('liability_payable') and not line.reconciled)
            account_move_line_obj_ap_refund |= ar_crenote

        if account_move_line_obj_ap_refund:
            account_move_line_obj_ap_refund.reconcile()

    def action_knockoff_bill_and_writeoff(self, amount_ap, amount_ar):
        account_move_line_obj_ar = self.env['account.move.line']
        account_move_line_obj_ap = self.env['account.move.line']
        account_move_obj = self.env['account.move']

        lines_to_reconcile_bill = self.select_move_bill_ids.mapped('line_ids').filtered(lambda line: line.account_id.reconcile and line.account_id.account_type == 'liability_payable').mapped('account_id')

        lines_to_reconcile_knockoff = self.select_move_knockoff_invoice_ids.mapped('line_ids').filtered(lambda line: line.account_id.reconcile and line.account_id.account_type == 'asset_receivable').mapped('account_id')

        new_lines_vals = [
            (0, 0,{
                'name': _('Knockoff from %s voucher %s', lines_to_reconcile_bill.display_name, self.name),
                'account_id': lines_to_reconcile_bill.id,
                'partner_id': self.partner_id.id,
                'currency_id': self.currency_id.id,
                'amount_currency': amount_ap,
                'balance': amount_ap,
            }),
            (0, 0, {
                'name': _('Knockoff to %s voucher %s', lines_to_reconcile_knockoff.display_name, self.name),
                'account_id': lines_to_reconcile_knockoff.id,
                'partner_id': self.partner_id.id,
                'currency_id': self.currency_id.id,
                'amount_currency': -amount_ar,
                'balance': -amount_ar,
            }),
        ]
        for rec_writeoff in self.account_writeoff_ids:
            new_lines_vals.append((0, 0, {
                'name': rec_writeoff.name,
                'account_id': rec_writeoff.account_id.id,
                'partner_id': self.partner_id.id,
                'currency_id': self.currency_id.id,
                'amount_currency': rec_writeoff.amount,
                'balance': rec_writeoff.amount,
            }))
        
        
        new_move_id = account_move_obj.create({
            'journal_id': self.journal_id.id,
            'line_ids': new_lines_vals,
            'date': self.payment_date,
            'move_type': 'entry',
            'ref': self.reference,

        })
        new_move_id.action_post()
        self.write({'move_writeoff_id': new_move_id.id})
        for rec_inv in self.select_move_knockoff_invoice_ids:
            reconcile_knockoff = (new_move_id.line_ids + rec_inv.line_ids).filtered(lambda line: line.account_id.reconcile and line.account_id.account_type in ('asset_receivable') and not line.reconciled)
            account_move_line_obj_ar |= reconcile_knockoff
        for rec_bill in self.select_move_bill_ids:
            reconcile_knockoff = (new_move_id.line_ids + rec_bill.line_ids).filtered(lambda line: line.account_id.reconcile and line.account_id.account_type in ('liability_payable') and not line.reconciled)
            account_move_line_obj_ap |= reconcile_knockoff

        if account_move_line_obj_ar:
            account_move_line_obj_ar.reconcile()
        if account_move_line_obj_ap:
            account_move_line_obj_ap.reconcile()

    def action_knockoff_refund_and_writeoff(self, amount_ap, amount_ar):
        account_move_line_obj_ap_ref = self.env['account.move.line']
        account_move_line_obj_ar = self.env['account.move.line']
        account_move_obj = self.env['account.move']

        lines_to_reconcile_refund = self.select_refund_ids.mapped('line_ids').filtered(lambda line: line.account_id.reconcile and line.account_id.account_type == 'liability_payable').mapped('account_id')

        lines_to_reconcile_knockoff = self.select_move_knockoff_invoice_ids.mapped('line_ids').filtered(lambda line: line.account_id.reconcile and line.account_id.account_type == 'asset_receivable').mapped('account_id')

        new_lines_vals = [
            (0, 0,{
                'name': _('Knockoff from %s voucher %s', lines_to_reconcile_refund.display_name, self.name),
                'account_id': lines_to_reconcile_refund.id,
                'partner_id': self.partner_id.id,
                'currency_id': self.currency_id.id,
                'amount_currency': -amount_ap,
                'balance': -amount_ap,
            }),
            (0, 0, {
                'name': _('Knockoff to %s voucher %s', lines_to_reconcile_knockoff.display_name, self.name),
                'account_id': lines_to_reconcile_knockoff.id,
                'partner_id': self.partner_id.id,
                'currency_id': self.currency_id.id,
                'amount_currency': -amount_ar,
                'balance': -amount_ar,
            }),
        ]
        for rec_writeoff in self.account_writeoff_ids:
            new_lines_vals.append((0, 0, {
                'name': rec_writeoff.name,
                'account_id': rec_writeoff.account_id.id,
                'partner_id': self.partner_id.id,
                'currency_id': self.currency_id.id,
                'amount_currency': rec_writeoff.amount,
                'balance': rec_writeoff.amount,
            }))
        
        
        new_move_id = account_move_obj.create({
            'journal_id': self.journal_id.id,
            'line_ids': new_lines_vals,
            'date': self.payment_date,
            'move_type': 'entry',
            'ref': self.reference,

        })
        new_move_id.action_post()
        self.write({'move_writeoff_id': new_move_id.id})
        for rec_inv in self.select_move_knockoff_invoice_ids:
            reconcile_knockoff = (new_move_id.line_ids + rec_inv.line_ids).filtered(lambda line: line.account_id.reconcile and line.account_id.account_type in ('asset_receivable') and not line.reconciled)
            account_move_line_obj_ar |= reconcile_knockoff
        for rec_bill in self.select_refund_ids:
            reconcile_knockoff = (new_move_id.line_ids + rec_bill.line_ids).filtered(lambda line: line.account_id.reconcile and line.account_id.account_type in ('liability_payable') and not line.reconciled)
            account_move_line_obj_ap_ref |= reconcile_knockoff

        if account_move_line_obj_ar:
            account_move_line_obj_ar.reconcile()
        if account_move_line_obj_ap_ref:
            account_move_line_obj_ap_ref.reconcile()
        
    def action_knockoffinvoice_and_writeoff(self, amount_ar):
        account_move_line_obj_ar = self.env['account.move.line']
        account_move_obj = self.env['account.move']

        lines_to_reconcile_knockoff = self.select_move_knockoff_invoice_ids.mapped('line_ids').filtered(lambda line: line.account_id.reconcile and line.account_id.account_type == 'asset_receivable').mapped('account_id')

        new_lines_vals = [
            (0, 0,{
                'name': _('Knockoff from %s voucher %s', lines_to_reconcile_knockoff.display_name, self.name),
                'account_id': lines_to_reconcile_knockoff.id,
                'partner_id': self.partner_id.id,
                'currency_id': self.currency_id.id,
                'amount_currency': -amount_ar,
                'balance': -amount_ar,
            }),
        ]
        for rec_writeoff in self.account_writeoff_ids:
            new_lines_vals.append((0, 0, {
                'name': rec_writeoff.name,
                'account_id': rec_writeoff.account_id.id,
                'partner_id': self.partner_id.id,
                'currency_id': self.currency_id.id,
                'amount_currency': rec_writeoff.amount,
                'balance': rec_writeoff.amount,
            }))
        
        
        new_move_id = account_move_obj.create({
            'journal_id': self.journal_id.id,
            'line_ids': new_lines_vals,
            'date': self.payment_date,
            'move_type': 'entry',
            'ref': self.reference,

        })
        new_move_id.action_post()
        self.write({'move_writeoff_id': new_move_id.id})
        for rec_inv in self.select_move_knockoff_invoice_ids:
            reconcile_knockoff = (new_move_id.line_ids + rec_inv.line_ids).filtered(lambda line: line.account_id.reconcile and line.account_id.account_type in ('asset_receivable') and not line.reconciled)
            account_move_line_obj_ar |= reconcile_knockoff

        if account_move_line_obj_ar:
            account_move_line_obj_ar.reconcile()

    def action_reconcile_voucher_bill(self, payment_create):
        account_move_line_obj_voucher = self.env['account.move.line']
        for rec_bill_tot in self.select_move_bill_ids:
            reconcile_voucher = (payment_create.move_id.line_ids + rec_bill_tot.line_ids).filtered(lambda line: line.account_id.reconcile and line.account_id.account_type in ('liability_payable') and not line.reconciled)
            account_move_line_obj_voucher |= reconcile_voucher
        
        if account_move_line_obj_voucher:
            account_move_line_obj_voucher.reconcile()

    def action_prepare_knockoff_invoice_bill_line(self, amount_knockoff):
        account_move_line_obj_ar = self.env['account.move.line']
        account_move_line_obj_ap = self.env['account.move.line']
        account_move_obj = self.env['account.move']
        
        lines_to_reconcile_bill = self.select_move_bill_ids.mapped('line_ids').filtered(lambda line: line.account_id.reconcile and line.account_id.account_type == 'liability_payable').mapped('account_id')

        lines_to_reconcile_knockoff = self.select_move_knockoff_invoice_ids.mapped('line_ids').filtered(lambda line: line.account_id.reconcile and line.account_id.account_type == 'asset_receivable').mapped('account_id')

        new_lines_vals = [
            (0, 0,{
                'name': _('Knockoff from %s voucher %s', lines_to_reconcile_bill.display_name, self.name),
                'account_id': lines_to_reconcile_bill.id,
                'partner_id': self.partner_id.id,
                'currency_id': self.currency_id.id,
                'amount_currency': amount_knockoff,
                'balance': amount_knockoff,
            }),
            (0, 0, {
                'name': _('Knockoff to %s voucher %s', lines_to_reconcile_knockoff.display_name, self.name),
                'account_id': lines_to_reconcile_knockoff.id,
                'partner_id': self.partner_id.id,
                'currency_id': self.currency_id.id,
                'amount_currency': -amount_knockoff,
                'balance': -amount_knockoff,
            }),
        ]
        new_move_id = account_move_obj.create({
            'journal_id': self.journal_id.id,
            'line_ids': new_lines_vals,
            'date': self.payment_date,
            'move_type': 'entry',

        })
        new_move_id.action_post()
        self.write({'move_knockoff_id': new_move_id.id})

        for rec_inv in self.select_move_knockoff_invoice_ids:
            reconcile_knockoff = (new_move_id.line_ids + rec_inv.line_ids).filtered(lambda line: line.account_id.reconcile and line.account_id.account_type in ('asset_receivable') and not line.reconciled)
            account_move_line_obj_ar |= reconcile_knockoff
        for rec_bill in self.select_move_bill_ids:
            reconcile_knockoff = (new_move_id.line_ids + rec_bill.line_ids).filtered(lambda line: line.account_id.reconcile and line.account_id.account_type in ('liability_payable') and not line.reconciled)
            account_move_line_obj_ap |= reconcile_knockoff

        if account_move_line_obj_ar:
            account_move_line_obj_ar.reconcile()
        if account_move_line_obj_ap:
            account_move_line_obj_ap.reconcile()

                

class SGEEDEPaymentDistributionLine(models.Model):
    _name = 'sgeede.payment.distribution.line'
    _description = 'Payment Distribution Line'

    invoice_date = fields.Date(string='Invoice Date', readonly=True)
    invoice_total = fields.Monetary(string='Invoice Total', readonly=True)
    payment_difference_handling = fields.Selection([
        ('open', 'Keep Open'),
        ('reconcile', 'Mark Invoice as Fully Paid')
    ], default='open')
    currency_id = fields.Many2one('res.currency', string="Currency", readonly=True)
    distribution_id = fields.Many2one('sgeede.payment.distribution', string='Distribution Reference', required=True, ondelete='cascade')
    invoice_id = fields.Many2one('account.move', string="Invoice", required=True)
    payment_amount = fields.Monetary(string='Amount', required=True, default=0.0)

    @api.onchange('invoice_id')
    def _onchange_invoice_id(self):
        for record in self:
            if record.invoice_id:
                record.payment_amount = record.invoice_id.amount_residual
                record.currency_id = record.invoice_id.currency_id
                record.invoice_date = record.invoice_id.invoice_date
                record.invoice_total = record.invoice_id.amount_residual

class SgeedePaymentWriteoff(models.Model):
    _name = "sgeede.payment.writeoff"

    name = fields.Char('Description')
    account_id = fields.Many2one('account.account', string='Account')
    amount = fields.Float('Amount')
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
    writeoff_id = fields.Many2one('sgeede.payment.distribution', string='Payment Distribution')
