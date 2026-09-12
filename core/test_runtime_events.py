import tempfile
from pathlib import Path
from unittest.mock import patch

from django.test import SimpleTestCase

from core.skills.runtime_events import RuntimeEventStore, get_runtime_event_store


class RuntimeEventStoreTests(SimpleTestCase):
    def test_events_are_persisted_ordered_and_cursor_addressable(self):
        with tempfile.TemporaryDirectory() as directory, patch("core.skills.runtime_events.EVENTS_DIR", Path(directory)):
            store = RuntimeEventStore("skillrun_live", "pipeline_1")
            first = store.emit("executor_started", stage="execution", executor="cleaning", status="executing", message="cleaning started")
            second = store.emit("executor_completed", stage="execution", executor="cleaning", status="success", message="cleaning completed", metadata={"duration_ms": 8})
            store.finish("completed", result={"answer": "done"})

            replay = get_runtime_event_store("skillrun_live").snapshot(after=0)
            incremental = get_runtime_event_store("skillrun_live").snapshot(after=first["sequence"])

            self.assertEqual([event["sequence"] for event in replay["events"]], [1, 2])
            self.assertEqual([event["sequence"] for event in incremental["events"]], [second["sequence"]])
            self.assertEqual(replay["status"], "completed")
            self.assertEqual(replay["result"], {"answer": "done"})
            self.assertEqual(replay["metrics"]["event_count"], 2)
            self.assertGreater(replay["metrics"]["average_payload_bytes"], 0)

    def test_concurrent_writers_keep_unique_sequences(self):
        import threading
        with tempfile.TemporaryDirectory() as directory, patch("core.skills.runtime_events.EVENTS_DIR", Path(directory)):
            store = RuntimeEventStore("skillrun_concurrent", "pipeline_2")
            threads = [threading.Thread(target=store.emit, args=("executor_started",), kwargs={"stage": "execution", "executor": f"worker-{index}", "status": "executing", "message": "started"}) for index in range(12)]
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join()
            events = store.snapshot(after=0, limit=100)["events"]
            self.assertEqual([event["sequence"] for event in events], list(range(1, 13)))
