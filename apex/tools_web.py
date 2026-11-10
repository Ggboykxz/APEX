"""Web tools: search through several providers and fetch remote pages.

Split out of ``apex.tools`` so that module keeps a single
responsibility: the tool executor core.
"""

from __future__ import annotations

import json
import re
import subprocess
import urllib.parse
from html.parser import HTMLParser
from typing import Any

__all__ = [
    "WebToolsMixin",
]


class WebToolsMixin:
    def _execute_web_search(self, args: dict[str, Any]) -> str:
        query = args["query"]
        import os

        brave_key = os.environ.get("BRAVE_API_KEY") or os.environ.get("BRAVE_SEARCH_API_KEY")
        tavily_key = os.environ.get("TAVILY_API_KEY")
        exa_key = os.environ.get("EXA_API_KEY")

        try:
            if brave_key:
                return self._web_search_brave(query, brave_key)
            if tavily_key:
                return self._web_search_tavily(query, tavily_key)
            if exa_key:
                return self._web_search_exa(query, exa_key)
            return self._web_search_duckduckgo(query)
        except Exception as e:  # noqa: BLE001
            try:
                return self._web_search_duckduckgo(query)
            except Exception:  # noqa: BLE001
                return f"ERROR: Web search failed: {e}"

    def _web_search_duckduckgo(self, query: str) -> str:
        url = f"https://duckduckgo.com/html/?q={urllib.parse.quote(query)}"
        result = subprocess.run(
            ["curl", "-s", "-L", url], capture_output=True, text=True, timeout=30, check=False
        )
        html = result.stdout
        titles = re.findall(r'<a class="result__a"[^>]*href="([^"]*)"[^>]*>([^<]*)', html)
        snippets = re.findall(r'<a class="result__snippet"[^>]*>([^<]*)', html)
        output = []
        for i, (link, title) in enumerate(titles[:5]):
            snippet = snippets[i] if i < len(snippets) else ""
            output.append(f"{i + 1}. {title.strip()}\n   {snippet.strip()}\n   {link}")
        return "\n\n".join(output) if output else "[no results]"

    @staticmethod
    def _curl_json(url: str, headers: list[str], payload: dict | None = None) -> dict:
        """Call an HTTP endpoint with curl and decode its JSON answer."""
        command = ["curl", "-s", "-L", url, *headers]
        if payload is not None:
            command += ["-H", "Content-Type: application/json", "-d", json.dumps(payload)]
        result = subprocess.run(command, capture_output=True, text=True, timeout=30, check=False)
        data = json.loads(result.stdout or "{}")
        return data if isinstance(data, dict) else {}

    @staticmethod
    def _render_results(
        items: list[dict], title_key: str, text_key: str, text_limit: int = 0
    ) -> str:
        """Render up to five search results."""
        output = []
        for i, item in enumerate(items[:5]):
            text = str(item.get(text_key, "")).strip()
            if text_limit:
                text = text[:text_limit]
            output.append(
                f"{i + 1}. {str(item.get(title_key, '')).strip()}\n   {text}\n   {item.get('url', '')}"
            )
        return "\n\n".join(output) if output else "[no results]"

    def _web_search_brave(self, query: str, api_key: str) -> str:
        url = (
            f"https://api.search.brave.com/res/v1/web/search?q={urllib.parse.quote(query)}&count=5"
        )
        data = self._curl_json(url, [f"X-Subscription-Token: {api_key}"])
        items = (data.get("web") or {}).get("results") or []
        return self._render_results(items, "title", "description")

    def _web_search_tavily(self, query: str, api_key: str) -> str:

        data = self._curl_json(
            "https://api.tavily.com/search",
            [],
            {"api_key": api_key, "query": query, "max_results": 5},
        )
        items = data.get("results") or []
        return self._render_results(items, "title", "content")

    def _web_search_exa(self, query: str, api_key: str) -> str:

        data = self._curl_json(
            "https://api.exa.ai/search",
            [f"x-api-key: {api_key}"],
            {"query": query, "numResults": 5},
        )
        items = data.get("results") or []
        return self._render_results(items, "title", "text", text_limit=200)

    def _execute_fetch_url(self, args: dict[str, Any]) -> str:
        url = args["url"]
        try:
            result = subprocess.run(
                ["curl", "-s", "-L", url], capture_output=True, text=True, timeout=30, check=False
            )
            cleaned = _html_to_text(result.stdout)

            return cleaned[:3000] + ("..." if len(cleaned) > 3000 else "")
        except Exception as e:  # noqa: BLE001
            return f"ERROR: Fetch failed: {e}"


class _VisibleTextParser(HTMLParser):
    """Collect the visible text of an HTML document.

    The content of ``script`` and ``style`` elements is skipped; every other
    text node is kept.  Parsing the document — instead of matching tags with
    a regular expression — is what keeps a crafted page from smuggling
    markup into the extracted text.
    """

    SKIPPED_TAGS = frozenset({"script", "style"})

    def __init__(self) -> None:
        super().__init__(convert_charrefs=False)
        self._skip_depth = 0
        self.parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in self.SKIPPED_TAGS:
            self._skip_depth += 1

    def handle_endtag(self, tag: str) -> None:
        if tag in self.SKIPPED_TAGS and self._skip_depth:
            self._skip_depth -= 1

    def handle_data(self, data: str) -> None:
        if not self._skip_depth:
            self.parts.append(data)

    def handle_entityref(self, name: str) -> None:
        if not self._skip_depth:
            self.parts.append(f"&{name};")

    def handle_charref(self, name: str) -> None:
        if not self._skip_depth:
            self.parts.append(f"&#{name};")


def _html_to_text(html: str) -> str:
    """The visible text of an HTML document."""
    parser = _VisibleTextParser()
    try:
        parser.feed(html)
        parser.close()
    except Exception:  # noqa: BLE001
        return ""
    text = " ".join(parser.parts)
    text = re.sub(r"&[a-z]+;", "", text)
    return re.sub(r"\s+", " ", text).strip()
