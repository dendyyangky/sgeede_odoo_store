from odoo import fields, models

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    ai_provider = fields.Selection([
        ('groq', 'Groq (Llama 3.3 70B)'),
        ('gemini', 'Google Gemini Flash'),
    ],string='AI Provider', default='groq', config_parameter='sgeede_ai_product_desc.ai_provider')
    ai_groq_api_key = fields.Char(string='Groq API Key', config_parameter='sgeede_ai_product_desc.ai_groq_api_key')
    ai_gemini_api_key = fields.Char(string='Gemini API Key',config_parameter='sgeede_ai_product_desc.ai_gemini_api_key')
    ai_default_tone = fields.Selection([
        ('professional', 'Professional'),
        ('casual', 'Casual'),
        ('technical', 'Technical'),
        ('marketing', 'Marketing'),
        ('minimalist', 'Minimalist'),
    ], string='Default Tone', default='professional', config_parameter='sgeede_ai_product_desc.ai_default_tone')
    ai_default_language = fields.Selection([
        ('en', 'English'),
        ('auto', 'Auto (follow Odoo language)'),
    ], string='Output Language', default='en', config_parameter='sgeede_ai_product_desc.ai_default_language')