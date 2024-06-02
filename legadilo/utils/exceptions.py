import httpx


def format_exception(exception: Exception) -> str:
    text = str(exception)
    if text:
        return f"{exception.__class__.__name__}({text})"

    return exception.__class__.__name__


def extract_debug_information(exception: httpx.HTTPError) -> dict | None:
    request: httpx.Request | None = None
    try:
        # Request may not be set or access may raise a RuntimeError. Prevent errors with a try/catch
        if hasattr(exception, "request"):
            request = exception.request
    except RuntimeError:
        pass

    response: httpx.Response | None = None
    if hasattr(exception, "response"):
        response = exception.response

    return {
        "request": {
            "headers": dict(request.headers),
            "url": str(request.url),
            "method": request.method,
        }
        if request
        else None,
        "response": {
            "headers": dict(response.headers),
            "status_code": response.status_code,
            "reason_phrase": response.reason_phrase,
        }
        if response
        else None,
    }
