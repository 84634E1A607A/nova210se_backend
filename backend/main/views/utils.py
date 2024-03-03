import json

from django.http import HttpResponse, JsonResponse
from django.conf import settings
from .exceptions import *


def api(allowed_methods: list[str] = None):
    """
    Decorator for all API views, checks for allowed methods, handles OPTIONS requests,
    parses JSON body and returns JSON response.

    This function never throws and always returns a JsonResponse (for all but OPTIONS requests).

    The decorated function should return a dictionary or a tuple of (status, string).
    """

    if allowed_methods is None:
        allowed_methods = ["GET"]

    if "OPTIONS" not in allowed_methods:
        allowed_methods.append("OPTIONS")

    # Apply CORS headers
    def with_cors(function):
        def decorated(request, *args, **kwargs) -> HttpResponse:
            response = function(request, *args, **kwargs)
            response["Access-Control-Allow-Origin"] = settings.CORS_ORIGIN
            response["Access-Control-Allow-Methods"] = ", ".join(allowed_methods)
            return response

        return decorated

    def decorator(function):
        @with_cors
        def decorated(request, *args, **kwargs) -> HttpResponse:
            # Always allow OPTIONS requests
            if request.method == "OPTIONS":
                response = HttpResponse()
                response["Allow"] = ", ".join(allowed_methods)
                return response

            # Check for allowed methods
            if request.method not in allowed_methods:
                return JsonResponse(status=405, data={
                    "ok": False,
                    "error": "Method not allowed"
                })

            # Try to parse JSON body (if any)
            data = None
            if request.method != "GET":
                if request.content_type != "application/json":
                    return JsonResponse(status=400, data={
                        "ok": False,
                        "error": f"Content type \"{request.content_type}\" not recognized"
                    })

                try:
                    data = json.loads(request.body)
                except json.JSONDecodeError as e:
                    return JsonResponse(status=400, data={
                        "ok": False,
                        "error": f"Malformed JSON request:\nf{e}"
                    })

            try:
                response_data = function(data, request=request, *args, **kwargs)
                if isinstance(response_data, tuple):
                    status, data = response_data
                    return JsonResponse(status=status, data={
                        "ok": False,
                        "error": data
                    })

                return JsonResponse({
                    "ok": True,
                    "data": response_data,
                })

            except DataTypeError as e:
                return JsonResponse(status=400, data={
                    "ok": False,
                    "error": f"Data type error for key \"{e.key}\""
                })

            except Exception as e:
                return JsonResponse(status=500, data={
                    "ok": False,
                    "error": f"Internal server error: {e}"
                })

        return decorated

    return decorator
