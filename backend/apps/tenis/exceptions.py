from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework.exceptions import ValidationError as RestValidationError
from rest_framework.views import exception_handler


def api_exception_handler(exc, context):
    """Convierte validaciones del dominio Django en respuestas JSON HTTP 400."""
    if isinstance(exc, DjangoValidationError):
        detail = getattr(exc, "message_dict", None) or getattr(exc, "messages", None) or [str(exc)]
        exc = RestValidationError(detail=detail)
    return exception_handler(exc, context)
