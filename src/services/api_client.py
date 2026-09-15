"""HTTP REST API Client for centralized NestJS + PostgreSQL backend."""

from __future__ import annotations

import os
import logging
import time
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# Configurar sesión HTTP persistente con pool y reintentos automáticos
_session = requests.Session()
_retry_strategy = Retry(
    total=2,
    backoff_factor=0.5,
    status_forcelist=[502, 503, 504],
    allowed_methods=["HEAD", "GET", "OPTIONS"]
)
_adapter = HTTPAdapter(max_retries=_retry_strategy, pool_connections=10, pool_maxsize=20)
_session.mount("http://", _adapter)
_session.mount("https://", _adapter)


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


def _sanitize_log_data(data: Any) -> Any:
    """Redacta campos sensibles de logs para protección de PII y credenciales."""
    if not isinstance(data, dict):
        return data
    sanitized = {}
    sensitive_keys = {"password", "token", "secret", "api_key", "key", "authorization"}
    for k, v in data.items():
        if any(s in k.lower() for s in sensitive_keys):
            sanitized[k] = "***REDACTED***"
        elif isinstance(v, dict):
            sanitized[k] = _sanitize_log_data(v)
        else:
            sanitized[k] = v
    return sanitized


def api_get(endpoint: str, params: dict | None = None, timeout: int = 8) -> dict | list:
    """Make a GET request to the centralized NestJS API and return parsed JSON."""
    url = f"{get_api_base_url()}{endpoint if endpoint.startswith('/') else '/' + endpoint}"
    headers = get_headers()
    try:
        response = _session.get(url, headers=headers, params=params, timeout=timeout)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.warning(f"[API_CLIENT] Error en GET {url}: {e}")
        raise


def api_post(endpoint: str, body: dict, timeout: int = 8) -> dict:
    """Make a POST request to the centralized NestJS API and return parsed JSON."""
    url = f"{get_api_base_url()}{endpoint if endpoint.startswith('/') else '/' + endpoint}"
    headers = get_headers()
    try:
        response = _session.post(url, headers=headers, json=body, timeout=timeout)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        safe_body = _sanitize_log_data(body)
        logger.warning(f"[API_CLIENT] Error en POST {url} con body {safe_body}: {e}")
        raise


def api_patch(endpoint: str, body: dict, timeout: int = 8) -> dict:
    """Make a PATCH request to the centralized NestJS API and return parsed JSON."""
    url = f"{get_api_base_url()}{endpoint if endpoint.startswith('/') else '/' + endpoint}"
    headers = get_headers()
    try:
        response = _session.patch(url, headers=headers, json=body, timeout=timeout)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        safe_body = _sanitize_log_data(body)
        logger.warning(f"[API_CLIENT] Error en PATCH {url} con body {safe_body}: {e}")
        raise


def is_api_online(timeout: int = 4) -> bool:
    """Check if the centralized NestJS REST API is reachable."""
    try:
        url = f"{get_api_base_url()}/products"
        resp = _session.get(url, headers=get_headers(), timeout=timeout)
        return resp.status_code in (200, 201)
    except Exception:
        return False

