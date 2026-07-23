"""One-shot browser automation using Playwright or Selenium."""

from __future__ import annotations

from urllib.parse import urlparse

TOOL_SPEC = {
    "name": "browser_automation",
    "description": (
        "Render a page and extract content using Playwright or Selenium. "
        "Useful for JS-heavy sites where simple HTTP fetch is insufficient."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "url": {"type": "string", "description": "Target http/https URL."},
            "backend": {
                "type": "string",
                "enum": ["auto", "playwright", "selenium"],
                "description": "Automation backend. Default: auto.",
            },
            "extract": {
                "type": "string",
                "enum": ["text", "html"],
                "description": "Extract visible text or rendered HTML. Default: text.",
            },
            "wait_ms": {"type": "integer", "description": "Wait after navigation in milliseconds (default 1000)."},
            "max_chars": {"type": "integer", "description": "Maximum characters in content output (default 12000)."},
        },
        "required": ["url"],
    },
}


def run(args: dict, context: dict) -> dict:
    _ = context
    url = str(args.get("url", "")).strip()
    if not url:
        return {"error": "url is required"}
    scheme = urlparse(url).scheme.lower()
    if scheme not in {"http", "https"}:
        return {"error": f"url must start with http:// or https://. Got: {url!r}"}

    backend = str(args.get("backend", "auto")).strip().lower() or "auto"
    if backend not in {"auto", "playwright", "selenium"}:
        return {"error": "backend must be one of: auto, playwright, selenium"}
    extract = str(args.get("extract", "text")).strip().lower() or "text"
    if extract not in {"text", "html"}:
        return {"error": "extract must be one of: text, html"}
    wait_ms = min(max(0, int(args.get("wait_ms", 1000))), 15000)
    max_chars = min(max(100, int(args.get("max_chars", 12000))), 50000)

    attempts = ["playwright", "selenium"] if backend == "auto" else [backend]
    errors = []
    for candidate in attempts:
        if candidate == "playwright":
            result = _run_playwright(url, extract, wait_ms, max_chars)
        else:
            result = _run_selenium(url, extract, wait_ms, max_chars)
        if "error" not in result:
            result["backend"] = candidate
            return result
        errors.append({candidate: result["error"]})
    return {"error": "All backends failed.", "attempt_errors": errors}


def _run_playwright(url: str, extract: str, wait_ms: int, max_chars: int) -> dict:
    try:
        from playwright.sync_api import sync_playwright  # type: ignore[import]
    except ImportError:
        return {"error": "playwright is not installed. Run: pip install playwright && playwright install"}

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(url, wait_until="domcontentloaded", timeout=30000)
            if wait_ms > 0:
                page.wait_for_timeout(wait_ms)
            title = page.title()
            final_url = page.url
            content = page.content() if extract == "html" else page.inner_text("body")
            browser.close()
    except Exception as exc:  # noqa: BLE001
        return {"error": f"Playwright render failed: {exc}"}
    return {
        "ok": True,
        "title": title,
        "url": final_url,
        "extract": extract,
        "content": content[:max_chars],
        "truncated": len(content) > max_chars,
    }


def _run_selenium(url: str, extract: str, wait_ms: int, max_chars: int) -> dict:
    try:
        from selenium import webdriver  # type: ignore[import]
        from selenium.webdriver.chrome.options import Options  # type: ignore[import]
    except ImportError:
        return {"error": "selenium is not installed. Run: pip install selenium"}

    driver = None
    try:
        options = Options()
        options.add_argument("--headless=new")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        driver = webdriver.Chrome(options=options)
        driver.set_page_load_timeout(30)
        driver.get(url)
        if wait_ms > 0:
            import time

            time.sleep(wait_ms / 1000.0)
        title = driver.title
        final_url = driver.current_url
        content = driver.page_source if extract == "html" else driver.find_element("tag name", "body").text
    except Exception as exc:  # noqa: BLE001
        return {"error": f"Selenium render failed: {exc}"}
    finally:
        if driver is not None:
            try:
                driver.quit()
            except Exception:  # noqa: BLE001
                pass
    return {
        "ok": True,
        "title": title,
        "url": final_url,
        "extract": extract,
        "content": content[:max_chars],
        "truncated": len(content) > max_chars,
    }
