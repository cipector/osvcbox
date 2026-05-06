from django.utils import translation

from .i18n import DEFAULT_LANGUAGE, LANGUAGE_SESSION_KEY, SUPPORTED_LANGUAGES


class SessionLanguageMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        language = request.session.get(LANGUAGE_SESSION_KEY, DEFAULT_LANGUAGE)
        if language not in SUPPORTED_LANGUAGES:
            language = DEFAULT_LANGUAGE
        request.LANGUAGE_CODE = language
        translation.activate(language)
        response = self.get_response(request)
        response.headers.setdefault("Content-Language", language)
        return response
