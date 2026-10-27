//! Python: `web_search` / `fetch_url` tools (inline in `apex/tools.py`).
//!
//! Provider chain for `web_search`: `BRAVE_API_KEY` / `BRAVE_SEARCH_API_KEY`
//! → Brave, `TAVILY_API_KEY` → Tavily, `EXA_API_KEY` → Exa, otherwise
//! DuckDuckGo. A failed provider falls back to DuckDuckGo; if that also
//! fails the original error is reported as `ERROR: Web search failed: …`.
//! `fetch_url` GETs the page (redirects followed, 30 s timeout) and returns
//! the visible text cleaned of scripts, styles and tags, capped at 3000
//! characters with a trailing `...`.

use regex::Regex;
use serde_json::Value;
use std::time::Duration;

/// Python uses a 30 second `subprocess` timeout for every web call.
const TIMEOUT_SECS: u64 = 30;

/// Python: `urllib.parse.quote(s)` — default `safe='/'`, uppercase hex.
pub(crate) fn quote(s: &str) -> String {
    let mut out = String::with_capacity(s.len());
    for b in s.as_bytes() {
        match b {
            b'A'..=b'Z' | b'a'..=b'z' | b'0'..=b'9' | b'_' | b'.' | b'-' | b'~' | b'/' => {
                out.push(*b as char)
            }
            _ => out.push_str(&format!("%{b:02X}")),
        }
    }
    out
}

/// Python: `fetch_url` cleaning pipeline (script/style removal, tag strip,
/// whitespace collapse, `&[a-z]+;` entity strip, 3000-char cap).
pub fn clean_html(html: &str) -> String {
    let script_re = Regex::new(r"<script[^>]*>.*?</script>").unwrap();
    let style_re = Regex::new(r"<style[^>]*>.*?</style>").unwrap();
    let tag_re = Regex::new(r"<[^>]+>").unwrap();
    let ws_re = Regex::new(r"\s+").unwrap();
    let entity_re = Regex::new(r"&[a-z]+;").unwrap();
    let scripts = script_re.replace_all(html, "");
    let styles = style_re.replace_all(&scripts, "");
    let no_tags = tag_re.replace_all(&styles, "");
    let collapsed = ws_re.replace_all(&no_tags, " ");
    let no_entities = entity_re.replace_all(&collapsed, "");
    let cleaned = no_entities.trim().to_string();
    if cleaned.chars().count() > 3000 {
        format!("{}...", cleaned.chars().take(3000).collect::<String>())
    } else {
        cleaned
    }
}

/// Python: `ToolExecutor._execute_fetch_url`.
pub fn fetch_url(url: &str) -> String {
    match http_request("GET", url, &[], None) {
        Ok(html) => clean_html(&html),
        Err(e) => format!("ERROR: Fetch failed: {e}"),
    }
}

/// Python: `ToolExecutor._execute_web_search` — provider chain with
/// DuckDuckGo fallback.
pub fn web_search(query: &str) -> String {
    let brave_key = env_nonempty("BRAVE_API_KEY").or_else(|| env_nonempty("BRAVE_SEARCH_API_KEY"));
    let tavily_key = env_nonempty("TAVILY_API_KEY");
    let exa_key = env_nonempty("EXA_API_KEY");
    let primary = if let Some(k) = brave_key {
        search_brave(query, &k)
    } else if let Some(k) = tavily_key {
        search_tavily(query, &k)
    } else if let Some(k) = exa_key {
        search_exa(query, &k)
    } else {
        search_duckduckgo(query)
    };
    match primary {
        Ok(out) => out,
        // Python: on any provider failure, retry DuckDuckGo once and report
        // the original error if it fails too.
        Err(e) => match search_duckduckgo(query) {
            Ok(out) => out,
            Err(_) => format!("ERROR: Web search failed: {e}"),
        },
    }
}

fn env_nonempty(name: &str) -> Option<String> {
    std::env::var(name).ok().filter(|v| !v.is_empty())
}

/// Python: `_web_search_duckduckgo`.
fn search_duckduckgo(query: &str) -> Result<String, String> {
    let url = format!("https://duckduckgo.com/html/?q={}", quote(query));
    let html = http_request("GET", &url, &[], None)?;
    Ok(parse_duckduckgo(&html))
}

/// Python: `_web_search_brave`.
fn search_brave(query: &str, api_key: &str) -> Result<String, String> {
    let url = format!(
        "https://api.search.brave.com/res/v1/web/search?q={}&count=5",
        quote(query)
    );
    let body = http_request("GET", &url, &[("X-Subscription-Token", api_key)], None)?;
    Ok(parse_brave(&json_body(&body)?))
}

/// Python: `_web_search_tavily`.
fn search_tavily(query: &str, api_key: &str) -> Result<String, String> {
    let payload = serde_json::json!({"api_key": api_key, "query": query, "max_results": 5});
    let body = http_request("POST", "https://api.tavily.com/search", &[], Some(&payload))?;
    Ok(parse_tavily(&json_body(&body)?))
}

/// Python: `_web_search_exa`.
fn search_exa(query: &str, api_key: &str) -> Result<String, String> {
    let payload = serde_json::json!({"query": query, "numResults": 5});
    let body = http_request(
        "POST",
        "https://api.exa.ai/search",
        &[("x-api-key", api_key)],
        Some(&payload),
    )?;
    Ok(parse_exa(&json_body(&body)?))
}

/// Python: `json.loads(result.stdout or "{}")` — empty body parses as `{}`,
/// a non-empty invalid body is an error (which triggers the fallback).
fn json_body(body: &str) -> Result<Value, String> {
    let text = if body.is_empty() { "{}" } else { body };
    serde_json::from_str(text).map_err(|e| e.to_string())
}

/// Python: DuckDuckGo HTML extraction.
pub fn parse_duckduckgo(html: &str) -> String {
    let title_re = Regex::new(r#"<a class="result__a"[^>]*href="([^"]*)"[^>]*>([^<]*)"#).unwrap();
    let snippet_re = Regex::new(r#"<a class="result__snippet"[^>]*>([^<]*)"#).unwrap();
    let titles: Vec<(String, String)> = title_re
        .captures_iter(html)
        .map(|c| (c[1].to_string(), c[2].to_string()))
        .collect();
    let snippets: Vec<String> = snippet_re
        .captures_iter(html)
        .map(|c| c[1].to_string())
        .collect();
    let mut output: Vec<String> = Vec::new();
    for (i, (link, title)) in titles.iter().take(5).enumerate() {
        let snippet = snippets.get(i).cloned().unwrap_or_default();
        output.push(format!(
            "{}. {}\n   {}\n   {link}",
            i + 1,
            title.trim(),
            snippet.trim()
        ));
    }
    if output.is_empty() {
        "[no results]".to_string()
    } else {
        output.join("\n\n")
    }
}

/// Python: `_web_search_brave` result formatting (`web.results`).
pub fn parse_brave(data: &Value) -> String {
    format_results(&top_items(data, &["web", "results"]), "description", 0)
}

/// Python: `_web_search_tavily` result formatting (`results`, `content`).
pub fn parse_tavily(data: &Value) -> String {
    format_results(&top_items(data, &["results"]), "content", 0)
}

/// Python: `_web_search_exa` result formatting (`results`, `text` capped at 200).
pub fn parse_exa(data: &Value) -> String {
    format_results(&top_items(data, &["results"]), "text", 200)
}

/// First five entries of `data[k1][k2]…` (missing/empty → no results).
fn top_items<'a>(data: &'a Value, keys: &[&str]) -> Vec<&'a Value> {
    let mut v: &Value = data;
    for k in keys {
        v = match v.get(k) {
            Some(x) => x,
            None => return Vec::new(),
        };
    }
    v.as_array()
        .map(|a| a.iter().take(5).collect())
        .unwrap_or_default()
}

/// Shared result shape: `"{i}. {title}\n   {detail}\n   {url}"` joined by
/// two newlines, or `[no results]`.
fn format_results(items: &[&Value], field: &str, truncate_at: usize) -> String {
    let mut output: Vec<String> = Vec::new();
    for (i, r) in items.iter().enumerate() {
        let get = |k: &str| r.get(k).and_then(|v| v.as_str()).unwrap_or("").trim();
        let mut detail = get(field).to_string();
        if truncate_at > 0 {
            detail = detail.chars().take(truncate_at).collect();
        }
        output.push(format!(
            "{}. {}\n   {detail}\n   {}",
            i + 1,
            get("title"),
            get("url")
        ));
    }
    if output.is_empty() {
        "[no results]".to_string()
    } else {
        output.join("\n\n")
    }
}

/// curl -s equivalent: body text on any HTTP status, redirects followed,
/// 30 s timeout. Runs on a dedicated thread with its own runtime — tools
/// execute inside the server's Tokio runtime, so a runtime must not be
/// created or dropped there (same pattern as `github::http_json`).
fn http_request(
    method: &str,
    url: &str,
    headers: &[(&str, &str)],
    body: Option<&Value>,
) -> Result<String, String> {
    let method = method.to_string();
    let url = url.to_string();
    let headers: Vec<(String, String)> = headers
        .iter()
        .map(|(k, v)| (k.to_string(), v.to_string()))
        .collect();
    let body = body.cloned();
    std::thread::spawn(move || {
        let rt = tokio::runtime::Runtime::new().map_err(|e| e.to_string())?;
        rt.block_on(async move {
            let client = reqwest::Client::builder()
                .timeout(Duration::from_secs(TIMEOUT_SECS))
                .build()
                .map_err(|e| e.to_string())?;
            let m = reqwest::Method::from_bytes(method.as_bytes()).map_err(|e| e.to_string())?;
            let mut req = client.request(m, &url);
            for (k, v) in &headers {
                req = req.header(k, v);
            }
            if let Some(b) = &body {
                req = req.json(b);
            }
            let resp = req.send().await.map_err(|e| e.to_string())?;
            resp.text().await.map_err(|e| e.to_string())
        })
    })
    .join()
    .unwrap_or_else(|_| Err("web request thread panicked".to_string()))
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;

    #[test]
    fn quote_matches_urllib_defaults() {
        assert_eq!(quote("hello"), "hello");
        assert_eq!(quote("hello world"), "hello%20world");
        assert_eq!(quote("a/b?c=d&e=f"), "a/b%3Fc%3Dd%26e%3Df");
        assert_eq!(quote("~._-keep"), "~._-keep");
    }

    #[test]
    fn clean_html_strips_scripts_styles_tags_and_entities() {
        let html = "<html><head><style>body{color:red}</style></head><body>\n\
                    <script>var x = 1;</script><h1>Hi There</h1>\n<p>A &amp; B</p>\n\
                    </body></html>";
        // Whitespace is collapsed *before* entity removal (Python order), so
        // `A &amp; B` becomes `A  B` with two spaces - not re-collapsed.
        assert_eq!(clean_html(html), "Hi There A  B");
    }

    #[test]
    fn clean_html_unclosed_style_content_leaks_through() {
        // Python's non-greedy match requires the closing tag; an unclosed
        // <style> keeps its content, and only the tags themselves are
        // removed by the generic strip.
        assert_eq!(clean_html("<style>body{}</p>Visible"), "body{}Visible");
    }

    #[test]
    fn clean_html_caps_at_3000_chars_with_ellipsis() {
        let long = "a".repeat(3500);
        let out = clean_html(&long);
        assert_eq!(out, format!("{}...", "a".repeat(3000)));
        // Exactly 3000 chars: no ellipsis.
        let exact = "b".repeat(3000);
        assert_eq!(clean_html(&exact), exact);
    }

    #[test]
    fn parse_duckduckgo_formats_with_snippet_fallback() {
        let html = r#"<html><a class="result__a" href="http://x.com">Title One</a>\
                      <a class="result__snippet">Snippet one</a>\
                      <a class="result__a" href="http://y.com">Title Two</a></html>"#;
        assert_eq!(
            parse_duckduckgo(html),
            "1. Title One\n   Snippet one\n   http://x.com\n\n2. Title Two\n   \n   http://y.com"
        );
    }

    #[test]
    fn parse_duckduckgo_keeps_five_and_reports_empty() {
        let mut html = String::new();
        for i in 0..7 {
            html.push_str(&format!(
                r#"<a class="result__a" href="http://n{i}.com">T{i}</a><a class="result__snippet">S{i}</a>"#
            ));
        }
        let out = parse_duckduckgo(&html);
        assert!(out.contains("5. T4"), "got {out}");
        assert!(!out.contains("T5"), "got {out}");
        assert_eq!(parse_duckduckgo("<html>nothing</html>"), "[no results]");
    }

    #[test]
    fn parse_brave_takes_first_five_web_results() {
        let data = json!({
            "web": {
                "results": [
                    {"title": " T1 ", "description": " D1 ", "url": "http://1"},
                    {"title": "T2", "description": "D2", "url": "http://2"},
                    {"title": "T3", "description": "D3", "url": "http://3"},
                    {"title": "T4", "description": "D4", "url": "http://4"},
                    {"title": "T5", "description": "D5", "url": "http://5"},
                    {"title": "T6", "description": "D6", "url": "http://6"}
                ]
            }
        });
        let out = parse_brave(&data);
        assert!(out.starts_with("1. T1\n   D1\n   http://1"), "got {out}");
        assert!(out.contains("5. T5\n   D5\n   http://5"), "got {out}");
        assert!(!out.contains("T6"), "got {out}");
        assert_eq!(parse_brave(&json!({})), "[no results]");
    }

    #[test]
    fn parse_tavily_uses_content_field() {
        let data = json!({"results": [{"title": "T", "content": "C", "url": "http://t"}]});
        assert_eq!(parse_tavily(&data), "1. T\n   C\n   http://t");
        assert_eq!(parse_tavily(&json!(null)), "[no results]");
    }

    #[test]
    fn parse_exa_truncates_text_at_200_chars() {
        let long = "x".repeat(250);
        let data = json!({"results": [{"title": "T", "text": long, "url": "http://t"}]});
        let out = parse_exa(&data);
        assert_eq!(out, format!("1. T\n   {}\n   http://t", "x".repeat(200)));
    }
}
