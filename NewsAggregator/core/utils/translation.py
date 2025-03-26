import requests
from django.conf import settings

SUPPORTED_LANGUAGES = {
    'es': 'Spanish',
    'fr': 'French',
    'de': 'German',
    'it': 'Italian',
    'pt': 'Portuguese',
    'ru': 'Russian',
    'ja': 'Japanese',
    'zh': 'Chinese',
    'ar': 'Arabic'
}

def translate_article_content(text, target_lang):
    if target_lang not in SUPPORTED_LANGUAGES:
        raise ValueError(f"Unsupported language: {target_lang}")
    
    response = requests.post(
        f'{settings.LIBRETRANSLATE_URL}/translate',
        json={
            'q': text,
            'source': 'en',
            'target': target_lang,
            'format': 'text'
        },
        timeout=15
    )
    return response.json()['translatedText']
