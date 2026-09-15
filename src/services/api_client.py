"""HTTP REST API Client for centralized NestJS + PostgreSQL backend."""

from __future__ import annotations

import os
import logging
import requests
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


def get_api_base_url() -> str:
    """Get configured API base URL."""
    return os.getenv("API_BASE_URL", "https://api-gasera-x.loca.lt/api").rstrip("/")


def get_headers() -> dict[str, str]:
    """Get standard headers including multi-tenant header."""
    return {
        "Content-Type": "application/json",
        "x-tenant-id": os.getenv("TENANT_ID", "petroil"),
        "Bypass-Tunnel-Reminder": "true",
    }


def api_get(endpoint: str, params: dict | None = None, timeout: int = 10) -> dict | list:
    """Make a GET request to the centralized NestJS API and return parsed JSON."""
    url = f"{get_api_base_url()}{endpoint if endpoint.startswith('/') else '/' + endpoint}"
    headers = get_headers()
    logger.debug(f"[API_CLIENT] GET {url} params={params}")
    response = requests.get(url, headers=headers, params=params, timeout=timeout)
    response.raise_for_status()
    return response.json()


def api_post(endpoint: str, body: dict, timeout: int = 10) -> dict:
    """Make a POST request to the centralized NestJS API and return parsed JSON."""
    url = f"{get_api_base_url()}{endpoint if endpoint.startswith('/') else '/' + endpoint}"
    headers = get_headers()
    logger.debug(f"[API_CLIENT] POST {url} body={body}")
    response = requests.post(url, headers=headers, json=body, timeout=timeout)
    response.raise_for_status()
    return response.json()


def api_patch(endpoint: str, body: dict, timeout: int = 10) -> dict:
    """Make a PATCH request to the centralized NestJS API and return parsed JSON."""
    url = f"{get_api_base_url()}{endpoint if endpoint.startswith('/') else '/' + endpoint}"
    headers = get_headers()
    logger.debug(f"[API_CLIENT] PATCH {url} body={body}")
    response = requests.patch(url, headers=headers, json=body, timeout=timeout)
    response.raise_for_status()
    return response.json()


def is_api_online(timeout: int = 5) -> bool:
    """Check if the centralized NestJS REST API is reachable."""
    try:
        url = f"{get_api_base_url()}/products"
        resp = requests.get(url, headers=get_headers(), timeout=timeout)
        return resp.status_code in (200, 201)
    except Exception:
        return False
