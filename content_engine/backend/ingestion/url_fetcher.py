# ============================================================
# backend/ingestion/url_fetcher.py (PRODUCTION VERSION)
# ============================================================

import re
from typing import List, Optional
from dataclasses import dataclass

import httpx

from content_engine.backend.utils.logger import get_logger
from content_engine.backend.cache.cache_manager import get_cache
from content_engine.backend.llm.providers import get_llm

logger = get_logger(__name__)
cache = get_cache()

# Limit text sent to LLM (token control)
MAX_TEXT_CHARS = 4000
MAX_URLS = 3

# Browser-like headers (avoid blocking)
DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
}


# ============================================================
# DATA STRUCTURE
# ============================================================

@dataclass
class FetchedURL:
    url: str
    title: str = ""
    extracted_text: str = ""
    summary: str = ""
    success: bool = False
    error: Optional[str] = None


# ============================================================
# FETCHER CLASS
# ============================================================

class URLFetcher:

    def fetch(self, url: str) -> FetchedURL:
        """
        Fetch HTML safely with retries + headers
        """
        try:
            with httpx.Client(timeout=10, follow_redirects=True, headers=DEFAULT_HEADERS) as client:
                r = client.get(url)

            if r.status_code != 200:
                logger.warning("url_fetch_failed_status", url=url, status=r.status_code)
                return FetchedURL(url=url, error=f"HTTP {r.status_code}")

            html = r.text[:200000]

            return FetchedURL(
                url=url,
                title=self._extract_title(html),
                extracted_text=self._clean_html(html),
                success=True,
            )

        except Exception as e:
            logger.error("url_fetch_exception", url=url, error=str(e))
            return FetchedURL(url=url, error=str(e))

    # --------------------------------------------------------
    # HTML PARSING
    # --------------------------------------------------------

    def _extract_title(self, html: str) -> str:
        match = re.search(r"<title>(.*?)</title>", html, re.I | re.S)
        return match.group(1).strip() if match else ""

    def _clean_html(self, html: str) -> str:
        """
        Lightweight HTML cleaning (fast, no BeautifulSoup)
        """

        # Remove scripts & styles
        html = re.sub(r"<script.*?>.*?</script>", " ", html, flags=re.S | re.I)
        html = re.sub(r"<style.*?>.*?</style>", " ", html, flags=re.S | re.I)

        # Remove tags
        text = re.sub(r"<[^>]+>", " ", html)

        # Normalize whitespace
        text = re.sub(r"\s+", " ", text)

        return text.strip()

    # --------------------------------------------------------
    # SUMMARIZATION (LLM + CACHE)
    # --------------------------------------------------------

    def summarize(self, obj: FetchedURL) -> FetchedURL:
        """
        Summarize extracted text using LLM with caching
        """

        if not obj.success:
            return obj

        text = obj.extracted_text[:MAX_TEXT_CHARS]

        if not text:
            obj.summary = ""
            return obj

        # -------------------------------
        # CACHE CHECK
        # -------------------------------
        cached = cache.read(input_data=text, node_name="url_summary")

        if cached and isinstance(cached, dict) and "summary" in cached:
            logger.info("url_summary_cache_hit", url=obj.url)
            obj.summary = cached["summary"]
            return obj

        # -------------------------------
        # LLM CALL
        # -------------------------------
        try:
            llm = get_llm()

            from langchain_core.messages import HumanMessage

            prompt = f"""
Summarize the following content into a concise, technical summary.

Focus on:
- Key ideas
- Technical insights
- Important concepts

Avoid fluff.

CONTENT:
{text}
"""

            response = llm.invoke(
                [HumanMessage(content=prompt)],
                task="parse",
            )

            summary = response.content.strip() if response else text[:300]

        except Exception as e:
            logger.error("url_summary_error", url=obj.url, error=str(e))
            summary = text[:300]

        # -------------------------------
        # CACHE WRITE
        # -------------------------------
        cache.write(
            input_data=text,
            result={"summary": summary},
            node_name="url_summary",
        )

        obj.summary = summary
        return obj


# ============================================================
# PIPELINE FUNCTION
# ============================================================

def fetch_and_summarize_urls(urls: List[str]) -> str:
    """
    Main pipeline entry used in run_pipeline.py

    Returns:
        Combined summarized context string
    """

    if not urls:
        return ""

    fetcher = URLFetcher()
    summaries = []

    for url in urls[:MAX_URLS]:

        logger.info("processing_url", url=url)

        fetched = fetcher.fetch(url)

        if not fetched.success:
            logger.warning("url_skipped", url=url, error=fetched.error)
            continue

        fetched = fetcher.summarize(fetched)

        if fetched.summary:
            summaries.append(
                f"URL: {url}\nTITLE: {fetched.title}\nSUMMARY:\n{fetched.summary}"
            )

    return "\n\n".join(summaries)