import json
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from core.runtime_retention import prune_runtime


class Command(BaseCommand):
    help = "按保留数量和天数清理流水线/Skill运行产物；默认仅预览。"

    def add_arguments(self, parser):
        parser.add_argument("--keep", type=int, default=100, help="每类至少保留的最新记录数量")
        parser.add_argument("--days", type=int, default=30, help="保留天数")
        parser.add_argument("--apply", action="store_true", help="实际执行清理；省略时只做 dry-run")

    def handle(self, *args, **options):
        try:
            result = prune_runtime(settings.BASE_DIR, keep=options["keep"], days=options["days"], apply=options["apply"], runtime_root=Path(settings.PROCESSPILOT_RUNTIME_ROOT))
        except ValueError as exc:
            raise CommandError(str(exc)) from exc
        self.stdout.write(json.dumps(result, ensure_ascii=False, indent=2))
