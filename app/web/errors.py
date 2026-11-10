"""Designed error pages for browsers; API and fetch() callers keep the JSON errors."""

import logging

from fastapi import Request
from fastapi.exception_handlers import (
    http_exception_handler,
    request_validation_exception_handler,
)
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger(__name__)

EXPLORE = ("Explore experiences", "/#experiences")


def error_copy(status: int, path: str) -> dict:
    """Title, message and the one next step for an error. href None means "go back"."""
    booking = path.removesuffix("/cancel").removesuffix("/translate")

    def page(title, message, action, href):
        return {"title": title, "message": message, "action": action, "href": href}

    if status == 409 and path == "/book":
        return page(
            "That date just filled up",
            "Someone booked the last seats a moment ago. Nothing was charged. "
            "Other dates may still be open.",
            *EXPLORE,
        )
    if status == 409 and path.endswith("/verify"):
        return page(
            "Your reservation time ended",
            "The seats were held for a few minutes and have been released. Nothing was "
            "charged. Please choose the date again.",
            *EXPLORE,
        )
    if status == 409 and path.endswith("/cancel"):
        return page(
            "This booking can no longer be cancelled",
            "It may have started already, or it was cancelled or changed earlier.",
            "Back to your booking",
            booking,
        )
    if status == 403 and path.endswith("/translate"):
        return page(
            "Language help opens once your host confirms",
            "As soon as your host says yes, you can use the translation page.",
            "Back to your booking",
            booking,
        )
    if status == 422:
        return page(
            "Some details were missing",
            "Please go back and check the form. Every field except dietary needs is required.",
            "Go back to the form",
            None,
        )
    if status == 404 and path.startswith("/listings/"):
        return page(
            "This experience is not available",
            "The host may have paused it, or the link is wrong.",
            *EXPLORE,
        )
    if status == 404 and path.startswith("/b/"):
        return page(
            "We could not find this booking",
            "Please open the booking link from your email again. It is long, so copy all of it.",
            "Go to the homepage",
            "/",
        )
    if status >= 500:
        return page(
            "Something went wrong on our side",
            "Nothing was charged. Please try again in a moment.",
            "Go to the homepage",
            "/",
        )
    if status == 404:
        return page(
            "This door is closed",
            "We could not find that page. The homes you are looking for are just inside.",
            "Go to the homepage",
            "/",
        )
    return page(
        "Something did not work",
        "Please go back and try again.",
        "Go to the homepage",
        "/",
    )


def wants_html(request: Request) -> bool:
    return "text/html" in request.headers.get("accept", "")


def render(request: Request, status: int):
    from app.web.routes import templates  # import here: routes imports the app's models

    return templates.TemplateResponse(
        request=request,
        name="error.html",
        context={"status": status, **error_copy(status, request.url.path)},
        status_code=status,
    )


async def http_error(request: Request, exc: StarletteHTTPException):
    if wants_html(request):
        return render(request, exc.status_code)
    return await http_exception_handler(request, exc)


async def validation_error(request: Request, exc: RequestValidationError):
    if wants_html(request):
        # On a page visit a validation error means a mangled link (e.g. /listings/abc): not found.
        return render(request, 404 if request.method == "GET" else 422)
    return await request_validation_exception_handler(request, exc)


async def server_error(request: Request, exc: Exception):
    logger.exception("Unhandled error on %s", request.url.path, exc_info=exc)
    if wants_html(request):
        return render(request, 500)
    return JSONResponse({"detail": "Internal Server Error"}, status_code=500)
