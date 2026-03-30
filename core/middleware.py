import logging
import time
from os import getenv

from services.callmebot import callmebot


request_logger = logging.getLogger("obox.request")
exception_logger = logging.getLogger("obox.exception")


class RequestContextMixin:
    @staticmethod
    def _get_client_ip(request) -> str:
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            return x_forwarded_for.split(",")[0].strip()

        return request.META.get("REMOTE_ADDR", "unknown")

    @staticmethod
    def _get_user_id(request) -> str | None:
        user = getattr(request, "user", None)
        if user and getattr(user, "is_authenticated", False):
            return str(user.id)
        return None


class ExceptionMiddleware(RequestContextMixin):
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        try:
            return self.get_response(request)
        except Exception as exc:
            self.process_exception(request, exc)
            raise

    def process_exception(self, request, exc):
        client_ip = self._get_client_ip(request)
        user_id = self._get_user_id(request)

        exception_logger.exception(
            (
                "Unhandled exception captured | method=%s | path=%s | "
                "ip=%s | user_id=%s | error=%s"
            ),
            request.method,
            request.get_full_path(),
            client_ip,
            user_id,
            str(exc),
        )

        self._notify_whatsapp(
            request=request,
            exc=exc,
            client_ip=client_ip,
            user_id=user_id,
        )

    def _notify_whatsapp(self, request, exc, client_ip: str, user_id: str | None):
        message = (
            "[Obox] Unhandled exception\n"
            f"method: {request.method}\n"
            f"path: {request.get_full_path()}\n"
            f"ip: {client_ip}\n"
            f"user_id: {user_id}\n"
            f"error: {str(exc)}"
        )

        exception_logger.info("Sending exception notification via WhatsApp")

        bot = callmebot()
        recipients = [
            ("5519999894514", getenv("API_KEY_MI")),
            ("5519997751263", getenv("API_KEY_MA")),
        ]

        for number, api_key in recipients:
            if not api_key:
                exception_logger.warning(
                    "WhatsApp notification skipped due to missing API key | number=%s",
                    number,
                )
                continue

            try:
                bot(number=number, message=message, api_key=api_key)
            except Exception:
                exception_logger.exception(
                    "Failed to send WhatsApp notification | number=%s",
                    number,
                )


class RequestLoggingMiddleware(RequestContextMixin):
    SKIPPED_PATHS = (
        "/robots.txt",
        "/favicon.ico",
    )

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path in self.SKIPPED_PATHS:
            return self.get_response(request)

        start_time = time.perf_counter()

        try:
            response = self.get_response(request)
        except Exception:
            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
            client_ip = self._get_client_ip(request)
            user_id = self._get_user_id(request)

            request_logger.exception(
                (
                    "HTTP request failed with exception | method=%s | path=%s | "
                    "ip=%s | user_id=%s | duration_ms=%s"
                ),
                request.method,
                request.get_full_path(),
                client_ip,
                user_id,
                duration_ms,
            )
            raise

        duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
        client_ip = self._get_client_ip(request)
        user_id = self._get_user_id(request)

        if response.status_code >= 500:
            log_method = request_logger.error
        elif response.status_code >= 400:
            log_method = request_logger.warning
        else:
            log_method = request_logger.info

        log_method(
            (
                "HTTP request completed | method=%s | path=%s | status=%s | "
                "ip=%s | user_id=%s | duration_ms=%s"
            ),
            request.method,
            request.get_full_path(),
            response.status_code,
            client_ip,
            user_id,
            duration_ms,
        )

        return response
