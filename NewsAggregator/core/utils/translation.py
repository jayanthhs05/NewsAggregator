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
        f'{settings.LIBRETRANSLATE_API}/translate',
        json={
            'q': text,
            'source': 'en',
            'target': target_lang,
            'format': 'text'
        },
        timeout=settings.LIBRETRANSLATE_TIMEOUT
    )
    return response.json()['translatedText']
