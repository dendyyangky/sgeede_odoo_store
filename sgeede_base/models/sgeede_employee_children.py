# -*- coding: utf-8 -*-
from odoo import fields, api, models, _
from odoo.exceptions import ValidationError

class SGEEDEEmployeeChildren(models.Model):
    _name = 'sgeede.employee.children'
    _description = 'Employee Children Details'

    name = fields.Char(string='Child Name', required=True)
    dob = fields.Date(string='Date of Birth', required=True)
    gender = fields.Selection([('male', 'Male'), ('female', 'Female')], string='Gender', required=True)
    employee_id = fields.Many2one('hr.employee', string='Employee', required=True)
    is_singapore_citizen = fields.Selection([('yes', 'Yes'), ('no', 'No')], string='Is Singapore Citizen', required=True)
    children_type = fields.Selection([('biological', 'Biological Child'), ('adopted', 'Adopted Child')], string='Child Type', required=True)
    # adoption_date = fields.Date(string='Adoption Date')
    adoption_type = fields.Selection([
        ('local', 'Local'),
        ('foreign', 'Foreign')
    ], default='local', string='Adoption Type')
    filing_court_date = fields.Date(string='Court Application Filing Date')
    ipa_date = fields.Date(string="In-Principle Approval (IPA) Date")
    adoption_order_date = fields.Date(string="Adoption Order Date")
    formal_intent_to_adopt_date = fields.Date(string="Formal Intent to Adopt Date", compute="_compute_fia_date", store=True)

    @api.constrains('dob', 'formal_intent_to_adopt_date', 'filing_court_date', 'ipa_date', 'adoption_order_date')
    def _constraint_dob_and_fia_date(self):
        for rec in self:
            if rec.children_type != 'adopted':
                continue
            
            if not rec.dob or not rec.formal_intent_to_adopt_date:
                continue
            
            if rec.formal_intent_to_adopt_date < rec.dob:
                raise ValidationError("Formal Intent to Adopt Date Can't be Before Child's Birth of Date")
            
            if rec.adoption_order_date < rec.formal_intent_to_adopt_date:
                raise ValidationError("Adoption Order Date cannot be earlier than Formal Intent to Adopt Date.")
            
    @api.depends('adoption_type', 'ipa_date', 'filing_court_date')
    def _compute_fia_date(self):
        for rec in self:
            if rec.adoption_type == 'local':
                rec.formal_intent_to_adopt_date = rec.filing_court_date
            elif rec.adoption_type == 'foreign':
                rec.formal_intent_to_adopt_date = rec.ipa_date
            else:
                rec.formal_intent_to_adopt_date = False