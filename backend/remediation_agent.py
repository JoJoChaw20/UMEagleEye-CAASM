"""Gemini-based remediation generator for drift events."""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI

logger = logging.getLogger(__name__)

# Load project-level .env so GEMINI_API_KEY works without manual shell export.
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(env_path)


def _get_gemini_api_key() -> str | None:
    """Read the Gemini API key from the environment."""
    return os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")


def _build_model() -> ChatGoogleGenerativeAI | None:
    """Create the Gemini chat model if credentials are configured."""
    api_key = _get_gemini_api_key()
    if not api_key:
        logger.warning("Gemini API key not configured. Remediation generation disabled.")
        return None

    model_name = (
        os.getenv("GEMINI_MODEL")
        or os.getenv("GOOGLE_GENAI_MODEL")
        or "gemini-2.5-flash"
    )

    return ChatGoogleGenerativeAI(
        model=model_name,
        temperature=0.2,
        google_api_key=api_key,
    )


def build_remediation_prompt(event_payload: dict[str, Any]) -> str:
    """Create a concise remediation prompt from a drift event payload."""
    return (
        "You are a senior security engineer. "
        "Review the port drift event and return practical remediation steps. "
        "Use this exact format:\n"
        "Summary: <one sentence>\n"
        "Risk: <low|medium|high|critical>\n"
        "Remediation:\n"
        "- <step 1>\n"
        "- <step 2>\n"
        "- <step 3>\n"
        "Verification:\n"
        "- <how to confirm the fix>\n\n"
        f"Drift event JSON:\n{json.dumps(event_payload, indent=2, default=str)}"
    )


def generate_remediation(event_payload: dict[str, Any]) -> str:
    """Send drift details to Gemini and return a formatted remediation response."""
    model = _build_model()
    if not model:
        return (
            "Summary: Review the drift event manually.\n"
            "Risk: medium\n"
            "Remediation:\n"
            "- Verify whether the newly detected port is authorized.\n"
            "- Close or firewall any unauthorized port.\n"
            "- Re-scan the asset to confirm the baseline is restored.\n"
            "Verification:\n"
            "- Re-run drift detection and confirm no new PORT_DRIFT event is created."
        )

    prompt = build_remediation_prompt(event_payload)

    try:
        response = model.invoke(
            [
                SystemMessage(
                    content=(
                        "You generate concise, actionable remediation guidance for port drift. "
                        "Do not mention that you are an AI model. "
                        "Focus on practical steps a SME can follow."
                    )
                ),
                HumanMessage(content=prompt),
            ]
        )
        return getattr(response, "content", str(response)).strip()
    except Exception as exc:
        logger.error("Failed to generate Gemini remediation: %s", exc, exc_info=True)
        return (
            "Summary: Drift was detected, but automated remediation could not be generated.\n"
            "Risk: medium\n"
            "Remediation:\n"
            "- Review the open ports and compare them with the approved baseline.\n"
            "- Remove any unauthorized services or ports.\n"
            "- Re-run the scan after changes.\n"
            "Verification:\n"
            "- Confirm the next drift detection run reports no new drift."
        )