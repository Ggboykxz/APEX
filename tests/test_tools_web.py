"""Tests for apex/tools_web.py - web search and URL fetch tools."""

from unittest.mock import MagicMock, patch

from apex.tools_web import WebToolsMixin, _html_to_text


class TestExecuteWebSearchRouting:
    def test_uses_brave_when_key_set(self, monkeypatch):
        monkeypatch.setenv("BRAVE_API_KEY", "bkey")
        tool = WebToolsMixin()
        with patch.object(tool, "_web_search_brave", return_value="brave results") as mock_brave:
            assert tool._execute_web_search({"query": "python"}) == "brave results"
        mock_brave.assert_called_once_with("python", "bkey")

    def test_uses_brave_search_key_fallback(self, monkeypatch):
        monkeypatch.setenv("BRAVE_SEARCH_API_KEY", "bkey2")
        monkeypatch.delenv("BRAVE_API_KEY", raising=False)
        tool = WebToolsMixin()
        with patch.object(tool, "_web_search_brave", return_value="ok") as mock_brave:
            tool._execute_web_search({"query": "q"})
        mock_brave.assert_called_once_with("q", "bkey2")

    def test_uses_tavily(self, monkeypatch):
        monkeypatch.setenv("TAVILY_API_KEY", "tkey")
        monkeypatch.delenv("BRAVE_API_KEY", raising=False)
        monkeypatch.delenv("BRAVE_SEARCH_API_KEY", raising=False)
        tool = WebToolsMixin()
        with patch.object(tool, "_web_search_tavily", return_value="tavily results") as mock_t:
            assert tool._execute_web_search({"query": "q"}) == "tavily results"
        mock_t.assert_called_once_with("q", "tkey")

    def test_uses_exa(self, monkeypatch):
        monkeypatch.setenv("EXA_API_KEY", "ekey")
        monkeypatch.delenv("BRAVE_API_KEY", raising=False)
        monkeypatch.delenv("BRAVE_SEARCH_API_KEY", raising=False)
        monkeypatch.delenv("TAVILY_API_KEY", raising=False)
        tool = WebToolsMixin()
        with patch.object(tool, "_web_search_exa", return_value="exa results") as mock_e:
            assert tool._execute_web_search({"query": "q"}) == "exa results"
        mock_e.assert_called_once_with("q", "ekey")

    def test_falls_back_to_duckduckgo_without_keys(self, monkeypatch):
        for key in ("BRAVE_API_KEY", "BRAVE_SEARCH_API_KEY", "TAVILY_API_KEY", "EXA_API_KEY"):
            monkeypatch.delenv(key, raising=False)
        tool = WebToolsMixin()
        with patch.object(tool, "_web_search_duckduckgo", return_value="ddg results") as mock_d:
            assert tool._execute_web_search({"query": "q"}) == "ddg results"
        mock_d.assert_called_once_with("q")

    def test_provider_failure_falls_back_to_duckduckgo(self, monkeypatch):
        monkeypatch.setenv("BRAVE_API_KEY", "bkey")
        tool = WebToolsMixin()
        with (
            patch.object(tool, "_web_search_brave", side_effect=RuntimeError("boom")),
            patch.object(tool, "_web_search_duckduckgo", return_value="ddg rescue") as mock_d,
        ):
            assert tool._execute_web_search({"query": "q"}) == "ddg rescue"
        mock_d.assert_called_once_with("q")

    def test_all_providers_fail(self, monkeypatch):
        for key in ("BRAVE_API_KEY", "BRAVE_SEARCH_API_KEY", "TAVILY_API_KEY", "EXA_API_KEY"):
            monkeypatch.delenv(key, raising=False)
        tool = WebToolsMixin()
        with patch.object(tool, "_web_search_duckduckgo", side_effect=RuntimeError("net down")):
            result = tool._execute_web_search({"query": "q"})
        assert result == "ERROR: Web search failed: net down"


DDG_HTML = """
<html>
  <a class="result__a" href="https://a.example">Title A</a>
  <a class="result__snippet">Snippet A</a>
  <a class="result__a" href="https://b.example">Title B</a>
  <a class="result__snippet">Snippet B</a>
</html>
"""


class TestWebSearchDuckDuckGo:
    @patch("subprocess.run")
    def test_parses_results(self, mock_run):
        mock_run.return_value = MagicMock(stdout=DDG_HTML)
        tool = WebToolsMixin()
        result = tool._web_search_duckduckgo("hello world")
        assert "1. Title A" in result
        assert "Snippet A" in result
        assert "https://a.example" in result
        assert "2. Title B" in result
        url = mock_run.call_args.args[0][3]
        assert "q=hello%20world" in url

    @patch("subprocess.run")
    def test_no_results(self, mock_run):
        mock_run.return_value = MagicMock(stdout="<html></html>")
        tool = WebToolsMixin()
        assert tool._web_search_duckduckgo("q") == "[no results]"

    @patch("subprocess.run")
    def test_captures_curl_command(self, mock_run):
        mock_run.return_value = MagicMock(stdout="")
        WebToolsMixin()._web_search_duckduckgo("q")
        command = mock_run.call_args.args[0]
        assert command[:3] == ["curl", "-s", "-L"]
        assert mock_run.call_args.kwargs["timeout"] == 30


class TestCurlJson:
    @patch("subprocess.run")
    def test_decodes_dict(self, mock_run):
        mock_run.return_value = MagicMock(stdout='{"ok": true}')
        assert WebToolsMixin._curl_json("http://x", ["-H", "h"]) == {"ok": True}
        command = mock_run.call_args.args[0]
        assert command[0] == "curl"
        assert "-H" in command and "h" in command

    @patch("subprocess.run")
    def test_with_payload(self, mock_run):
        import json

        mock_run.return_value = MagicMock(stdout="{}")
        WebToolsMixin._curl_json("http://x", [], {"a": 1})
        command = mock_run.call_args.args[0]
        assert "-d" in command
        assert json.dumps({"a": 1}) in command
        assert "Content-Type: application/json" in command

    @patch("subprocess.run")
    def test_non_dict_json_becomes_empty(self, mock_run):
        mock_run.return_value = MagicMock(stdout="[1, 2, 3]")
        assert WebToolsMixin._curl_json("http://x", []) == {}

    @patch("subprocess.run")
    def test_empty_stdout_becomes_empty(self, mock_run):
        mock_run.return_value = MagicMock(stdout="")
        assert WebToolsMixin._curl_json("http://x", []) == {}


class TestRenderResults:
    def test_renders_items(self):
        items = [
            {"title": "A", "text": "text A", "url": "https://a"},
            {"title": "B", "text": "text B", "url": "https://b"},
        ]
        out = WebToolsMixin._render_results(items, "title", "text")
        assert "1. A\n   text A\n   https://a" in out
        assert "2. B\n   text B\n   https://b" in out

    def test_limits_to_five(self):
        items = [{"title": f"T{i}", "text": f"t{i}", "url": "u"} for i in range(8)]
        out = WebToolsMixin._render_results(items, "title", "text")
        assert "5. T4" in out
        assert "T5" not in out

    def test_text_limit_truncates(self):
        items = [{"title": "A", "text": "x" * 50, "url": "u"}]
        out = WebToolsMixin._render_results(items, "title", "text", text_limit=10)
        assert "x" * 10 in out
        assert "x" * 11 not in out

    def test_missing_keys(self):
        out = WebToolsMixin._render_results([{"other": 1}], "title", "text")
        assert "1. \n" in out

    def test_empty(self):
        assert WebToolsMixin._render_results([], "title", "text") == "[no results]"


class TestProviderSearchers:
    @patch.object(WebToolsMixin, "_curl_json")
    def test_brave(self, mock_curl):
        mock_curl.return_value = {"web": {"results": [{"title": "A", "description": "d"}]}}
        tool = WebToolsMixin()
        result = tool._web_search_brave("q", "key")
        assert "1. A" in result
        url = mock_curl.call_args.args[0]
        assert url.startswith("https://api.search.brave.com")
        assert mock_curl.call_args.args[1] == ["X-Subscription-Token: key"]

    @patch.object(WebToolsMixin, "_curl_json")
    def test_brave_without_web_block(self, mock_curl):
        mock_curl.return_value = {}
        tool = WebToolsMixin()
        assert tool._web_search_brave("q", "key") == "[no results]"

    @patch.object(WebToolsMixin, "_curl_json")
    def test_tavily(self, mock_curl):
        mock_curl.return_value = {"results": [{"title": "A", "content": "c"}]}
        tool = WebToolsMixin()
        result = tool._web_search_tavily("q", "key")
        assert "1. A\n   c" in result
        assert mock_curl.call_args.args[2] == {"api_key": "key", "query": "q", "max_results": 5}

    @patch.object(WebToolsMixin, "_curl_json")
    def test_exa(self, mock_curl):
        mock_curl.return_value = {"results": [{"title": "A", "text": "long" * 100}]}
        tool = WebToolsMixin()
        result = tool._web_search_exa("q", "key")
        assert "1. A" in result
        assert mock_curl.call_args.args[2] == {"query": "q", "numResults": 5}


class TestExecuteFetchUrl:
    @patch("subprocess.run")
    def test_fetches_and_cleans(self, mock_run):
        mock_run.return_value = MagicMock(
            stdout="<html><body><script>var x=1;</script><p>Visible</p></body></html>"
        )
        tool = WebToolsMixin()
        assert tool._execute_fetch_url({"url": "https://x.example"}) == "Visible"

    @patch("subprocess.run")
    def test_truncates_long_output(self, mock_run):
        mock_run.return_value = MagicMock(stdout="<html>" + "a" * 5000 + "</html>")
        tool = WebToolsMixin()
        result = tool._execute_fetch_url({"url": "https://x.example"})
        assert len(result) == 3003
        assert result.endswith("...")

    @patch("subprocess.run")
    def test_error(self, mock_run):
        mock_run.side_effect = RuntimeError("timeout")
        tool = WebToolsMixin()
        assert (
            tool._execute_fetch_url({"url": "https://x.example"}) == "ERROR: Fetch failed: timeout"
        )


class TestHtmlToText:
    def test_strips_script_and_style(self):
        html = "<div>keep<script>secret()</script><style>.a{}</style>also</div>"
        assert _html_to_text(html) == "keep also"

    def test_collapses_whitespace(self):
        assert _html_to_text("<p>a\n\n  b</p>") == "a b"

    def test_script_cdata_terminates_at_first_endtag(self):
        # HTMLParser treats script as CDATA: the skip ends at the first
        # </script>, so text after it is kept (Python parity).
        html = "<script>outer<script>inner</script>still</script>text"
        assert _html_to_text(html) == "still text"

    def test_entity_references_removed(self):
        assert _html_to_text("<p>a &amp; b</p>") == "a b"

    def test_charref_kept(self):
        assert _html_to_text("<p>&#65;</p>") == "&#65;"

    def test_empty(self):
        assert _html_to_text("") == ""
