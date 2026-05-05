import threading
import time
import logging

from django.conf import settings

from ACI_Backend.objects.siem_schema_retrieval.siem_schema_retrieval_service import (
    refresh_siem_schema,
)
from siem_endpoint.models import SIEMInfo
from siem_endpoint.objects.siem_wrapper.siem_wrapper_builder import SIEMWrapperBuilder


_RETRIEVAL_STARTED = False
_RETRIEVAL_START_LOCK = threading.Lock()
logger = logging.getLogger(__name__)


def _retrieve_schema_for_single_siem(siem_id: int):
    logger.info("Starting SIEM schema retrieval for siem_id=%s", siem_id)
    try:
        siem_info = SIEMInfo.objects.get(id=siem_id)
    except SIEMInfo.DoesNotExist:
        logger.warning("SIEM not found while retrieving schema for siem_id=%s", siem_id)
        return {"error": f"SIEM {siem_id} not found"}

    logger.debug("Built SIEM model for siem_id=%s; retrieving schema", siem_id)
    siem_wrapper = SIEMWrapperBuilder().build_from_model_object(siem_info_obj=siem_info)
    refresh_siem_schema(siem_wrapper=siem_wrapper, siem_id=siem_id)
    logger.info("Retrieved SIEM schema for siem_id=%s", siem_id)
    return {"message": f"Retrieved SIEM schema for SIEM {siem_id}"}


def _retrieve_schema_for_all_siems():
    siem_ids = list(SIEMInfo.objects.values_list("id", flat=True))
    logger.debug("Starting SIEM schema retrieval batch for %s SIEMs", len(siem_ids))
    for siem_id in siem_ids:
        try:
            _retrieve_schema_for_single_siem(siem_id=siem_id)
        except Exception as exc:
            logger.exception("Failed schema retrieval for siem_id=%s: %s", siem_id, exc)


def _siem_schema_retrieval_loop():
    interval_seconds = settings.SIEM_SCHEMA_RETRIEVAL_INTERVAL_MINUTES * 60
    logger.info(
        "Starting SIEM schema retrieval loop in 5 seconds with interval_seconds=%s",
        interval_seconds,
    )
    time.sleep(5)

    while True:
        try:
            _retrieve_schema_for_all_siems()
        except Exception as exc:
            logger.exception("Failed during SIEM schema retrieval loop: %s", exc)

        time.sleep(interval_seconds)


def start_periodic_siem_schema_retrieval() -> None:
    global _RETRIEVAL_STARTED

    if settings.SIEM_SCHEMA_RETRIEVAL_INTERVAL_MINUTES <= 0:
        logger.info("SIEM schema retrieval loop disabled because interval is <= 0")
        return

    with _RETRIEVAL_START_LOCK:
        if _RETRIEVAL_STARTED:
            logger.info("SIEM schema retrieval loop already started in this process")
            return
        
        retrieval_thread = threading.Thread(
            target=_siem_schema_retrieval_loop,
            daemon=True,
            name="siem-schema-retrieval",
        )
        retrieval_thread.start()
        _RETRIEVAL_STARTED = True
        logger.info("Started background SIEM schema retrieval thread")
