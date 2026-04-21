{
    'name': 'AI Product Description Generator',
    'version': '18.0.1.0.0',
    'description': """
    Automatically generate product descriptions using AI directly from the product form.

    Powered by Groq (Llama 3.3 70B) and Google Gemini Flash - both completely free,
    no credit card required. Configure your preferred provider and API key once
    from Settings, then generate professional product descriptions in seconds.
    Choose from multiple tones: Professional, Casual, Technical, Marketing, or Minimalist.
    """,

    'summary': 'Generate product descriptions instantly using free AI - Groq and Gemini supported',
    'author': 'SGEEDE',
    'website': 'https://www.sgeede.com',
    'license': 'LGPL-3',
    'category': 'Productivity',
    'depends': [
        'base',
        'website_sale',
    ],
    'data': [
        'security/ir.model.access.csv',

        'views/product_template_views.xml',
        'views/res_config_settings_views.xml',
        'wizards/sgeede_ai_desc_wizard_views.xml',
    ],
    'images': ['static/description/banner.gif'],
    'installable': True,
    'auto_install': False,
    'application': False,
}