# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    # === PAYMENT DISTRIBUTION FEATURE ===
    is_module_sgeede_payment_distribution = fields.Boolean(
        string='Payment Distribution',
        implied_group='sgeede_base.sgeede_payment_distribution_groups',
        config_parameter='sgeede_base.is_module_sgeede_payment_distribution',
    )
    is_module_sgeede_singapore_leave = fields.Boolean(
        string="Singapore Leave",
        implied_group="sgeede_base.sgeede_singaporean_leave_groups",
        config_parameter="sgeede_base.is_module_sgeede_singapore_leave",
    )

    @api.model
    def get_values(self):
        res = super().get_values()
        icp = self.env['ir.config_parameter'].sudo()

        payment_distribution_param = icp.get_param(
            'sgeede_base.is_module_sgeede_payment_distribution', default=False
        )
        singaporean_leave_param = icp.get_param(
            'sgeede_base.is_module_sgeede_singapore_leave', default=False
        )


        res.update(
            is_module_sgeede_payment_distribution=payment_distribution_param == 'True',
            is_module_sgeede_singapore_leave = singaporean_leave_param == 'True',
        )
        
        return res

    def set_values(self):
        super().set_values()
        icp = self.env['ir.config_parameter'].sudo()

        # === Payment Distribution ===
        payment_distribution_param = self.is_module_sgeede_payment_distribution
        icp.set_param('sgeede_base.is_module_sgeede_payment_distribution', payment_distribution_param)

        payment_group = self.env.ref('sgeede_base.sgeede_payment_distribution_groups')
        users = self.env.ref('base.group_user').all_user_ids
        for user in users:
            if payment_distribution_param:
                user.sudo().write({'group_ids': [(4, payment_group.id)]})
            else:
                user.sudo().write({'group_ids': [(3, payment_group.id)]})

        # === Singaporean Leave ===
        singaporean_leave_param = self.is_module_sgeede_singapore_leave
        icp.set_param('sgeede_base.is_module_sgeede_singapore_leave', singaporean_leave_param)

        singaporean_leave_group = self.env.ref('sgeede_base.sgeede_singaporean_leave_groups')
        users = self.env.ref('base.group_user').all_user_ids

        for user in users:
            if singaporean_leave_param:
                user.sudo().write({'group_ids': [(4, singaporean_leave_group.id)]})
            else:
                user.sudo().write({'group_ids': [(3, singaporean_leave_group.id)]})

