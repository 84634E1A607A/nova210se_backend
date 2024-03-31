import inspect
import json

from django.http import HttpResponse, JsonResponse, HttpRequest
from django.conf import settings
from main.exceptions import FieldMissingError, FieldTypeError, ClientSideError


def api(allowed_methods: list[str] = None, needs_auth: bool = True):
    """
    Decorator for all API views, checks for allowed methods, handles OPTIONS requests,
    parses JSON body and returns JSON response.

    This function never throws, and always returns a JsonResponse (for all but OPTIONS requests).

    The decorated function may have a data (JSON data), request (raw HTTPRequest), method (string request method)
    or auth_user (AuthUser) parameter with *args, **kwargs, and should return an object or a tuple of (status, string).

    Any api accepts an OPTIONS request and returns a response with the allowed methods in the "Allow" header.

    If an API requires valid session but the user is not logged in, the API will return 403 status code:
    {
        "ok": false,
        "error": "Invalid Session"
    }

    If an API is called with a method not in the allowed_methods list, the API will return 405 status code:
    {
        "ok": false,
        "error": "Method not allowed"
    }

    If an API is called with a bad JSON request, the API will return 400 status code:
    {
        "ok": false,
        "error": "Malformed JSON request"
    }

    If an API is called 1. Not with GET verb; 2. With a Content-Type other than application/json, the API will return
    400 status code:
    {
        "ok": false,
        "error": "Content type not recognized"
    }

    If a FieldMissingError or FieldTypeError is thrown, the API will return 400 status code.

    If any internal error occurs, the API will return 500 status code. In debug mode it will trigger a django 500 page
    with detailed stack trace in it; in release mode it will return:
    {
        "ok": false,
        "error": "Internal server error"
    }
    """

    if allowed_methods is None:
        allowed_methods = ["GET"]

    if "OPTIONS" not in allowed_methods:
        allowed_methods.append("OPTIONS")

    def decorator(function):
        def decorated(request: HttpRequest, *args, **kwargs) -> HttpResponse:
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
                }, headers={
                    "Allow": ", ".join(allowed_methods)
                })

            # Check for authentication
            if needs_auth and not request.user.is_authenticated:
                return JsonResponse(status=403, data={
                    "ok": False,
                    "error": "Invalid Session"
                })

            # Try to parse JSON body (if any)
            data: dict | None = None
            if request.method != "GET" and request.content_type != "":
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
                parameters = inspect.signature(function).parameters

                if "request" in parameters:
                    kwargs["request"] = request
                if "auth_user" in parameters:
                    kwargs["auth_user"] = request.user
                if "data" in parameters:
                    kwargs["data"] = data
                if "method" in parameters:
                    kwargs["method"] = request.method

                if "kwargs" in parameters:
                    kwargs["request"] = request
                    kwargs["auth_user"] = request.user
                    kwargs["data"] = data
                    kwargs["method"] = request.method

                response_data = function(*args, **kwargs)

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

            except ClientSideError as e:
                return JsonResponse(status=e.code, data={
                    "ok": False,
                    "error": e.get_message()
                })

            except Exception as e:
                if settings.DEBUG:
                    raise

                return JsonResponse(status=500, data={
                    "ok": False,
                    "error": f"Internal server error: {e}"
                })

        return decorated

    return decorator


def check_fields(struct: dict):
    """
    Decorator to check required fields and throws exception if any is missing.

    Pass in data structure in dict format:
    {
        "field": type
    }

    If the field is missing, this decorator will throw a FieldMissingError.
    If the field is not of the specified type, this decorator will throw a FieldTypeError.
    """

    def decorator(function):
        def decorated(data, **kwargs):
            for key, value in struct.items():
                if key not in data:
                    raise FieldMissingError(key)

                if not isinstance(data[key], value):
                    raise FieldTypeError(key)

            parameters = inspect.signature(function).parameters

            for key in ["request", "auth_user", "method"]:
                if key not in parameters and key in kwargs:
                    del kwargs[key]

            kwargs["data"] = data

            return function(**kwargs)

        return decorated

    return decorator


def not_found(request: HttpRequest):
    return JsonResponse(status=404, data={
        "ok": False,
        "error": f"{request.path} not found on this server"
    })
