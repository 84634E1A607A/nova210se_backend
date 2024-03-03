from django.http import HttpResponse, JsonResponse


def api(allowed_methods: list[str] = None):
    """
    Decorator for all API views, checks for allowed methods, handles OPTIONS requests,
    parses JSON body and returns JSON response.

    This function never throws and always returns a JsonResponse (for all but OPTIONS requests).
    """

    if allowed_methods is None:
        allowed_methods = ["GET"]

    def decorator(function, *args, **kwargs):
        def decorated(request, *args, **kwargs):
            # Check for allowed methods
            if request.method not in allowed_methods:
                return JsonResponse(status=405, data={
                    "ok": False,
                    "error": "Method not allowed"
                })

            if request.method == "OPTIONS":
                response = HttpResponse()
                response["Allow"] = ", ".join(allowed_methods)
                return response

            try:
                return JsonResponse(function(request, *args, **kwargs))
            except Exception as e:
                return JsonResponse(status=500, data={
                    "ok": False,
                    "error": f"Internal server error: {e}"
                })

        return decorated

    return decorator

# def api(function):
#     """
#     Decorator for all API views, checks for allowed methods, handles OPTIONS requests.
#     """
#     def decorated(request, *args, **kwargs):
#         print(args, kwargs)
#         return function(request, *args, **kwargs)
#     return decorated


@api(allowed_methods=["GET", "POST"])
def login(request):
    return {
        "ok": True,
        "message": "Hello, world!"
    }
