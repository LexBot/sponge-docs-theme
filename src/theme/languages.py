import json
import os.path

import babel
import requests

from . import __version__


LOCAL_LANGUAGES_FILE = os.path.join(os.path.dirname(__file__), 'languages.json')
LANGUAGES_FILE = 'build/languages.json'
languages = None


def get_language_code(locale_code):
    return languages[locale_code]['code']


def get_language_display_name(locale_code):
    lang = languages[locale_code]

    # Compute display name if not already cached
    if 'display_name' not in lang:
        try:
            locale = babel.Locale.parse(lang['code'], sep='-')
            if locale.script:
                # If we have a script (e.g. Simplified for Chinese) then we
                # don't need the territory additionally (e.g. China)
                locale.territory = None

            lang['display_name'] = locale.languages[str(locale)].title()
        except babel.UnknownLocaleError:
            lang['display_name'] = lang['name']

    return lang['display_name']


def load_languages():
    global languages

    # Check if cached languages exists already
    if os.path.exists(LANGUAGES_FILE):
        with open(LANGUAGES_FILE, 'r') as f:
            languages = json.load(f)
    else:
        # Load Crowdin languages from API
        r = requests.get('https://api.crowdin.com/api/supported-languages?json')
        r.raise_for_status()

        languages = {lang['locale'].replace('-', '_'): {
            'name': lang['name'],
            'code': lang['crowdin_code']
        } for lang in r.json()}

        # Load locale data
        with open(LOCAL_LANGUAGES_FILE, 'r') as f:
            local_locales = json.load(f)

        # Replace with local data
        for key, data in local_locales.items():
            if key in languages:
                languages[key].update(data)
            else:
                languages[key] = data

        # Write languages to file
        with open(LANGUAGES_FILE, 'w+') as f:
            json.dump(languages, f)


def init(app):
    # Return if we are not doing a HTML build
    if app.builder.name != 'html':
        return

    # Add Jinja2 filters
    app.builder.templates.environment.filters['language_code'] = get_language_code
    app.builder.templates.environment.filters['language_display_name'] = get_language_display_name

    # Jinja2 needs the filters to compile the templates.
    # However, unless we are doing a translated build they should be never called.
    if not app.config.language:
        return

    app.info('Loading languages...')
    load_languages()
    app.info('%d languages loaded' % len(languages))


# This is the entry point if this module is loaded as a Sphinx extension
def setup(app):
    app.connect('builder-inited', init)
    return {
        'version': __version__,
        'parallel_read_safe': True,
        'parallel_write_safe': True
    }
