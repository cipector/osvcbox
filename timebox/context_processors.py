from .i18n import current_language, ui_for


def ui(request):
    language = current_language(request)
    return {
        "current_language": language,
        "ui": ui_for(language),
        "supported_languages": ["cs", "en"],
    }
