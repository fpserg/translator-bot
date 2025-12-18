import logging
import traceback
from typing import Optional, Set

import aiohttp


TRANSLATE_BASE_URL = "https://translate.api.cloud.yandex.net/translate/v2"


async def detect_language(text: str, token: str, folder_id: Optional[str] = None, language_code_hints: Optional[list[str]] = None) -> Optional[str]:
    try:
        payload: dict = {
            "text": text,
        }
        if language_code_hints:
            payload["languageCodeHints"] = language_code_hints
        if folder_id:
            payload["folderId"] = folder_id

        async with aiohttp.ClientSession() as session:
            r = await session.post(
                url=f"{TRANSLATE_BASE_URL}/detect",
                json=payload,
                headers={"Authorization": f"Bearer {token}"},
                timeout=aiohttp.ClientTimeout(total=20),
            )
            data = await r.json()
            if r.status >= 400:
                logging.error("Yandex detect error %s: %s", r.status, data)
                return None
            return data.get("languageCode")
    except Exception:
        logging.error("Error in detect_language: %s", traceback.format_exc())
        return None


async def list_languages(token: str, folder_id: Optional[str] = None) -> Set[str]:
    """Return set of supported language codes via ListLanguages."""
    try:
        payload: dict = {}
        if folder_id:
            payload["folderId"] = folder_id

        async with aiohttp.ClientSession() as session:
            r = await session.post(
                url=f"{TRANSLATE_BASE_URL}/languages",
                json=payload,
                headers={"Authorization": f"Bearer {token}"},
                timeout=aiohttp.ClientTimeout(total=20),
            )
            data = await r.json()
            if r.status >= 400:
                logging.error("Yandex languages error %s: %s", r.status, data)
                return set()

            langs = data.get("languages") or []
            return {item.get("code") for item in langs if item.get("code")}
    except Exception:
        logging.error("Error in list_languages: %s", traceback.format_exc())
        return set()

