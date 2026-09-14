import time

from django.core.management.base import BaseCommand

from core.services.jobs import run_one


class Command(BaseCommand):
    help = "运行可恢复的数据库任务队列 Worker"

    def add_arguments(self, parser):
        parser.add_argument("--once", action="store_true", help="最多执行一个任务后退出")
        parser.add_argument("--poll-seconds", type=float, default=1.0)

    def handle(self, *args, **options):
        while True:
            worked = run_one()
            if options["once"]:
                return
            if not worked:
                time.sleep(max(0.1, options["poll_seconds"]))
