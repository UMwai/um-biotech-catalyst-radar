"""n8n workflow integration."""

import logging
from typing import Any, Dict

import requests

from .config import Config

logger = logging.getLogger(__name__)


def trigger_workflow(workflow_key: str, payload: Dict[str, Any]) -> bool:
    """Trigger an n8n workflow via webhook.

    Args:
        workflow_key: The key/slug of the workflow (appended to base URL)
        payload: Data to send to the workflow

    Returns:
        True if successful, False otherwise
    """
    config = Config.from_env()

    if not config.n8n_webhook_base_url:
        logger.warning("n8n webhook base URL not configured, skipping workflow: %s", workflow_key)
        return False

    # Construct URL - ensure no double slashes
    base_url = config.n8n_webhook_base_url.rstrip("/")
    url = f"{base_url}/{workflow_key}"

    try:
        response = requests.post(url, json=payload, timeout=10)
        response.raise_for_status()
        logger.info("Successfully triggered n8n workflow: %s", workflow_key)
        return True
    except Exception as e:
        logger.error("Failed to trigger n8n workflow %s: %s", workflow_key, str(e))
        return False
