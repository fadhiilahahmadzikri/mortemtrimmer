# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Fadhiilah Ahmad Zikri
"""Bilingual localization resolver (EN / ID)."""

from __future__ import annotations

import locale
from collections.abc import Mapping
from typing import Any

from autosilenttrimmer.core.constants import DEFAULT_LANGUAGE, SUPPORTED_LANGUAGES
from autosilenttrimmer.core.i18n.catalog_en import MESSAGES_EN
from autosilenttrimmer.core.i18n.catalog_id import MESSAGES_ID

_CATALOGS: dict[str, Mapping[str, str]] = {
    "en": MESSAGES_EN,
    "id": MESSAGES_ID,
}


def detect_system_language() -> str:
    """Detect system default language normalized to 'id' or 'en'."""
    lang, _ = locale.getlocale()
    if not lang:
        return DEFAULT_LANGUAGE
    prefix = lang.split("_", 1)[0].split("-", 1)[0].lower()
    return prefix if prefix in SUPPORTED_LANGUAGES else DEFAULT_LANGUAGE


class Localizer:
    """Stateless-friendly string catalog lookup supporting English and Indonesian."""

    def __init__(self, language: str | None = None) -> None:
        normalized = (language or DEFAULT_LANGUAGE).lower().strip()
        self._language = normalized if normalized in SUPPORTED_LANGUAGES else DEFAULT_LANGUAGE

    @property
    def language(self) -> str:
        """Return active language code."""
        return self._language

    def set_language(self, language: str) -> None:
        """Switch active language if supported."""
        normalized = language.lower().strip()
        if normalized in SUPPORTED_LANGUAGES:
            self._language = normalized

    def toggle_language(self) -> str:
        """Cycle between English and Indonesian."""
        self._language = "id" if self._language == "en" else "en"
        return self._language

    def text(self, key: str, **kwargs: Any) -> str:
        """Resolve localized template by key and apply optional format kwargs."""
        catalog = _CATALOGS.get(self._language, MESSAGES_EN)
        template = catalog.get(key) or MESSAGES_EN.get(key) or key
        if kwargs:
            try:
                return template.format(**kwargs)
            except (KeyError, ValueError):
                return template
        return template
