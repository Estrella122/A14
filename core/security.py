from __future__ import annotations

from django.conf import settings
from django.http import JsonResponse


class ApiAuthenticationMiddleware:
    """Require an authenticated Django session for API access in production mode."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        protected = request.path.startswith("/api/") and request.path != "/api/security/session/"
        if settings.PROCESSPILOT_REQUIRE_AUTH and protected and not request.user.is_authenticated:
            return JsonResponse(
                {"ok": False, "message": "登录已失效，请通过管理入口登录后重试。", "code": "authentication_required"},
                status=401,
                json_dumps_params={"ensure_ascii": False},
            )
        return self.get_response(request)
