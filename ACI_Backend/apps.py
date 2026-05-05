from django.apps import AppConfig
from django.apps import apps as django_apps
import os
import sys
import logging
import threading

logger = logging.getLogger(__name__)

class MainBackendConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "ACI_Backend"

    @staticmethod
    def _start_siem_refresher() -> None:
        # Wait until Django has completed all AppConfig.ready() hooks.
        django_apps.ready_event.wait()

        from ACI_Backend.objects.siem_schema_retrieval.siem_schema_retrieval_refresher import (
            start_periodic_siem_schema_retrieval,
        )

        start_periodic_siem_schema_retrieval()

    def ready(self):
        if os.getenv("ACI_DISABLE_SIEM_SCHEMA_RETRIEVAL", "0") == "1":
            return

        if len(sys.argv) > 1 and sys.argv[1] in {
            "makemigrations",
            "migrate",
            "collectstatic",
            "test",
        }:
            return

        # With runserver autoreload, a parent watcher process is also started.
        # Start the refresher only in the serving child process.
        is_runserver = len(sys.argv) > 1 and sys.argv[1] == "runserver"
        if (
            is_runserver
            and "--noreload" not in sys.argv
            and os.environ.get("RUN_MAIN") != "true"
        ):
            return
        
        threading.Thread(
            target=self._start_siem_refresher,
            daemon=True,
            name="siem-refresher-bootstrap",
        ).start()
