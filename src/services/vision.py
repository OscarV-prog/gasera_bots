"""Vision AI service for reading tank rotogauge and dial meters from photos."""

from __future__ import annotations

import base64
import json
import logging
import os
import re
from pathlib import Path
from typing import Any

import httpx
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
DEFAULT_VISION_MODEL = "openai/gpt-4o-mini"


def _encode_image_to_base64(image_path: str | Path) -> str:
    """Read local image file and return its base64 encoded string."""
    path = Path(image_path)
    if not path.exists():
        raise FileNotFoundError(f"No se encontró la imagen en: {path}")

    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def _determine_mime_type(image_path: str | Path) -> str:
    """Guess mime type based on file extension."""
    suffix = Path(image_path).suffix.lower()
    if suffix in [".png"]:
        return "image/png"
    if suffix in [".webp"]:
        return "image/webp"
    return "image/jpeg"


async def analyze_tank_meter_image(
    image_path: str | Path,
    api_key: str | None = None,
    model: str = DEFAULT_VISION_MODEL,
    timeout_seconds: float = 12.0,
) -> dict[str, Any]:
    """Analyze a photo of a gas tank / pipa rotogauge dial using Vision AI.

    Returns a dict with:
    - success: bool
    - reading_value: str | None (e.g. '85%', '4500 L')
    - confidence: str ('alta', 'media', 'baja', 'desconocida')
    - details: str (human readable description of what was observed)
    """
    token = api_key or os.getenv("OPENROUTER_API_KEY")
    if not token:
        logger.warning("OPENROUTER_API_KEY no configurado para análisis de visión.")
        return {
            "success": False,
            "reading_value": None,
            "confidence": "ninguna",
            "details": "API key de OpenRouter no disponible",
        }

    try:
        b64_data = _encode_image_to_base64(image_path)
        mime = _determine_mime_type(image_path)
    except Exception as e:
        logger.error(f"Error preparando imagen para visión: {e}")
        return {
            "success": False,
            "reading_value": None,
            "confidence": "ninguna",
            "details": f"Error leyendo imagen: {e}",
        }

    prompt_system = (
        "Eres un perito técnico experto en lectura de medidores de gas LP, rotogauges, "
        "relojes de porcentaje de tanques estacionarios y carátulas de pipas de gas.\n"
        "Analiza la fotografía y determina el valor numérico marcado por la aguja o indicador.\n"
        "Reglas obligatorias:\n"
        "1. Si el reloj es de porcentaje (0% a 100%), responde con el porcentaje exacto o aproximado, ej: '85%'.\n"
        "2. Si es un contador de litros o galones, responde con el número y la unidad, ej: '3500 L'.\n"
        "3. Responde ÚNICAMENTE en formato JSON válido con las llaves:\n"
        "   - 'detected_value': texto corto con el valor formateado (ej. '85%' o '4200 L') o null si no se distingue\n"
        "   - 'confidence': 'alta', 'media' o 'baja'\n"
        "   - 'details': breve explicación en español (ej. 'Aguja entre el 80% y 90%, marca ~85%')\n"
        "No agregues texto fuera del JSON."
    )

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/petroil-gas",
        "X-Title": "Petroil Tank Meter Vision Reader",
    }

    payload = {
        "model": model,
        "temperature": 0.1,
        "max_tokens": 250,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt_system},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:{mime};base64,{b64_data}"},
                    },
                ],
            }
        ],
    }

    try:
        async with httpx.AsyncClient(timeout=timeout_seconds) as client:
            response = await client.post(OPENROUTER_URL, headers=headers, json=payload)

        if response.status_code != 200:
            logger.warning(
                f"OpenRouter vision falló con status {response.status_code}: {response.text}"
            )
            return {
                "success": False,
                "reading_value": None,
                "confidence": "ninguna",
                "details": f"Error de servicio de visión ({response.status_code})",
            }

        data = response.json()
        raw_text = data.get("choices", [{}])[0].get("message", {}).get("content", "").strip()

        # Limpiar bloques markdown ```json ... ``` si vinieran
        cleaned = raw_text
        if "```" in cleaned:
            match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", cleaned)
            if match:
                cleaned = match.group(1)

        result_json = json.loads(cleaned)
        detected_val = result_json.get("detected_value")

        return {
            "success": bool(detected_val),
            "reading_value": str(detected_val).strip() if detected_val else None,
            "confidence": result_json.get("confidence", "media"),
            "details": result_json.get("details", ""),
        }

    except Exception as exc:
        logger.error(f"Excepción en análisis de visión: {exc}")
        return {
            "success": False,
            "reading_value": None,
            "confidence": "ninguna",
            "details": f"Excepción durante análisis: {exc}",
        }
