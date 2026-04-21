from odoo import api, fields, models, _
from odoo.exceptions import UserError
import requests


class SgeedeAiDescWizard(models.TransientModel):
    _name = 'sgeede.ai.desc.wizard'

    product_id = fields.Many2one('product.template', string='Product', required=True, readonly=True)
    target_field = fields.Selection([
        ('description_sale',    'Sales Description'),
        ('description',         'Internal Notes'),
        ('description_ecommerce', 'eCommerce Description'),
    ], string='Generate For', required=True, default='description_sale')
    tone = fields.Selection([
        ('professional', 'Professional'),
        ('casual', 'Casual'),
        ('technical','Technical'),
        ('marketing', 'Marketing'),
        ('minimalist','Minimalist'),
    ], string='Tone', required=True, default='professional')
    language = fields.Selection([
        ('en',   'English'),
        ('auto', 'Auto'),
    ], string='Language', required=True, default='en',)
    preview_result = fields.Text(string='Preview', readonly=True)
    state = fields.Selection([
        ('configure', 'Configure'),
        ('preview',   'Preview'),
    ], default='configure')

    def action_generate(self):
        self.ensure_one()
        product = self.product_id

        prompt = product._build_prompt(
            target_field=self.target_field,
            tone=self.tone,
            language=self.language,
        )

        config = product._get_ai_config()

        try:
            if config['provider'] == 'groq':
                result = product._call_groq(prompt, config['groq_key'])
            elif config['provider'] == 'gemini':
                result = product._call_gemini(prompt, config['gemini_key'])
            else:
                raise UserError(_('Unknown AI provider.'))
        except requests.exceptions.Timeout:
            raise UserError(_('AI request timed out. Please try again.'))
        except requests.exceptions.HTTPError as e:
            raise UserError(_('AI API error: %s') % str(e))

        self.write({
            'preview_result': result,
            'state': 'preview',
        })

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'sgeede.ai.desc.wizard',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }

    def action_apply(self):
        self.ensure_one()
        if not self.preview_result:
            raise UserError(_('No generated description to apply.'))

        self.product_id.write({
            self.target_field: self.preview_result,
            'ai_last_generated': fields.Datetime.now(),
            'ai_generated_count': self.product_id.ai_generated_count + 1,
        })

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'product.template',
            'res_id': self.product_id.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_regenerate(self):
        self.write({'state': 'configure', 'preview_result': False})
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'sgeede.ai.desc.wizard',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }

    def action_discard(self):
        return {'type': 'ir.actions.act_window_close'}