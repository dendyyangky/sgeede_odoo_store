import requests
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    ai_last_generated = fields.Datetime(string='Last AI Generated', readonly=True)
    ai_generated_count = fields.Integer(string='AI Generate Count', default=0, readonly=True)

    def _get_ai_config(self):
        get_param = self.env['ir.config_parameter'].sudo().get_param
        return {
            'provider': get_param('sgeede_ai_product_desc.ai_provider', 'groq'),
            'groq_key': get_param('sgeede_ai_product_desc.ai_groq_api_key', ''),
            'gemini_key': get_param('sgeede_ai_product_desc.ai_gemini_api_key', ''),
            'tone': get_param('sgeede_ai_product_desc.ai_default_tone', 'professional'),
            'language': get_param('sgeede_ai_product_desc.ai_default_language', 'en'),
        }

    def _build_prompt(self, target_field, tone, language):
        self.ensure_one()

        lang_instruction = {
            'en': 'Write in English.',
            'auto': '',
        }.get(language, '')

        tone_instruction = {
            'professional': 'Use a professional and formal tone.',
            'casual': 'Use a friendly and casual tone.',
            'technical': 'Use a technical and detailed tone, include specs.',
            'marketing': 'Use a persuasive marketing tone, highlight benefits.',
            'minimalist': 'Use a short and concise tone, maximum 2 sentences.',
        }.get(tone, 'Use a professional tone.')

        field_instruction = {
            'description_sale': 'Write a customer-facing sales description.',
            'description': 'Write an internal product note for warehouse or procurement team.',
            'description_ecommerce': 'Write a customer-facing e-commerce description  .',
        }.get(target_field, 'Write a product description.')

        category = self.categ_id.complete_name or ''
        attributes = ', '.join([
            '%s: %s' % (line.attribute_id.name, ', '.join(line.value_ids.mapped('name')))
            for line in self.attribute_line_ids
        ]) or 'No variants'
        price = '%s %s' % (self.currency_id.name, '{:,.0f}'.format(self.list_price))

        prompt = """
You are a product copywriter for an e-commerce and B2B business platform.

Product information:
- Name: %s
- Category: %s
- Price: %s
- Internal Reference: %s
- Attributes: %s

Task: %s
Tone: %s
Language: %s

Return only the description text. No titles, no labels, no extra explanation.
        """.strip() % (
            self.name or '',
            category,
            price,
            self.default_code or 'N/A',
            attributes,
            field_instruction,
            tone_instruction,
            lang_instruction,
        )
        return prompt

    def _call_groq(self, prompt, api_key):
        if not api_key:
            raise UserError(_('Groq API key is not configured. Please set it in Settings.'))

        response = requests.post(
            'https://api.groq.com/openai/v1/chat/completions',
            headers={
                'Authorization': 'Bearer %s' % api_key,
                'Content-Type': 'application/json',
            },
            json={
                'model': 'llama-3.3-70b-versatile',
                'messages': [{'role': 'user', 'content': prompt}],
                'max_tokens': 300,
                'temperature': 0.7,
            },
            timeout=30,
        )
        response.raise_for_status()
        return response.json()['choices'][0]['message']['content'].strip()

    def _call_gemini(self, prompt, api_key):
        if not api_key:
            raise UserError(_('Gemini API key is not configured. Please set it in Settings.'))

        response = requests.post(
            'https://generativelanguage.googleapis.com/v1beta/models/gemini-flash-latest:generateContent?',
            headers={
                'Content-Type': 'application/json',
                'x-goog-api-key': '%s' % api_key
                },
            json={
                'contents': [{'parts': [{'text': prompt}]}],
            },
            timeout=30,
        )
        response.raise_for_status()
        return response.json()['candidates'][0]['content']['parts'][0]['text'].strip()

    def action_open_ai_wizard(self):
        self.ensure_one()
        wizard = self.env['sgeede.ai.desc.wizard'].create({
            'product_id': self.id,
        })
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'sgeede.ai.desc.wizard',
            'res_id': wizard.id,
            'view_mode': 'form',
            'target': 'new',
        }