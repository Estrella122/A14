from __future__ import annotations

from django.conf import settings
from django.http import JsonResponse


class ApiAuthenticationMiddleware:
    """Require an authenticated Django session for API access in production mode."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        public_endpoints = {"/api/security/session/", "/api/health/"}
        protected = request.path.startswith("/api/") and request.path not in public_endpoints
        if settings.PROCESSPILOT_REQUIRE_AUTH and protected and not request.user.is_authenticated:
            return JsonResponse(
                {"ok": False, "message": "登录已失效，请通过管理入口登录后重试。", "code": "authentication_required"},
                status=401,
                json_dumps_params={"ensure_ascii": False},
            )
        if protected and settings.PROCESSPILOT_REQUIRE_AUTH:
            import json
            import re
            from .services.pipeline import get_run
            match = re.search(r'/(?:pipeline|agent)/runs/([^/]+)/', request.path)
            run_id = match.group(1) if match and match.group(1) != 'latest' else None
            if request.content_type == 'application/json' and request.method in {'POST', 'PUT', 'PATCH'}:
                try:
                    payload = json.loads(request.body or b'{}')
                    if isinstance(payload, dict): run_id = payload.get('run_id') or payload.get('source_run_id') or run_id
                except (ValueError, UnicodeError):
                    pass
            skill_match = re.search(r'/agent/skill-runs/([^/]+)/', request.path)
            if skill_match:
                from .models import SkillRunRecord
                record = SkillRunRecord.objects.filter(skill_run_id=skill_match.group(1)).first()
                if record:
                    run_id = record.pipeline_run_id
                    if not run_id and not request.user.is_staff:
                        return JsonResponse({'ok': False, 'message': '此记录缺少可核实的运行归属。'}, status=403)
            if run_id:
                snapshot = get_run(run_id)
                if snapshot and not run_accessible(request, snapshot):
                    return JsonResponse({'ok': False, 'message': '无权访问此 A14 运行。'}, status=403)
        return self.get_response(request)


def run_accessible(request, snapshot):
    if not settings.PROCESSPILOT_REQUIRE_AUTH:
        return True
    return bool(request.user.is_authenticated and snapshot.get('project', 'A14') == 'A14'
                and (snapshot.get('owner_id') == request.user.pk
                     or request.user.is_staff and snapshot.get('owner_id') is None))
