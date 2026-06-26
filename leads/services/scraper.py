"""
Website scraper service for Forge OS.

Crawls a website (single page or a shallow same-domain crawl) and extracts
contact intelligence using only free, standard tooling:

    * Emails
    * Phone numbers
    * Social profile links
    * Postal addresses (best-effort, from schema.org / address tags)
    * Page metadata (title, description, keywords)

No paid APIs. Respects a small page cap to stay fast and polite.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from django.conf import settings

logger = logging.getLogger("leads")

EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}")
PHONE_RE = re.compile(
    r"(?:(?:\+|00)\d{1,3}[\s.\-]?)?(?:\(?\d{2,4}\)?[\s.\-]?){2,4}\d{2,4}"
)
SOCIAL_DOMAINS = {
    "facebook": "facebook.com",
    "twitter": "twitter.com",
    "x": "x.com",
    "instagram": "instagram.com",
    "linkedin": "linkedin.com",
    "youtube": "youtube.com",
    "tiktok": "tiktok.com",
    "pinterest": "pinterest.com",
}


@dataclass
class ScrapeResult:
    url: str = ""
    title: str = ""
    description: str = ""
    keywords: str = ""
    emails: list[str] = field(default_factory=list)
    phones: list[str] = field(default_factory=list)
    socials: dict = field(default_factory=dict)
    addresses: list[str] = field(default_factory=list)
    pages_crawled: int = 0
    error: str = ""


def _normalize_url(url: str) -> str:
    url = url.strip()
    if not url:
        return ""
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    return url


def _session() -> requests.Session:
    s = requests.Session()
    s.headers.update(
        {
            "User-Agent": getattr(
                settings, "OSM_USER_AGENT",
                "Mozilla/5.0 (compatible; ForgeOS/1.0)",
            ),
            "Accept": "text/html,application/xhtml+xml",
            "Accept-Language": "en-US,en;q=0.9",
        }
    )
    return s


def _clean_phone(raw: str) -> str:
    digits = re.sub(r"[^\d+]", "", raw)
    return raw.strip() if 7 <= len(digits) <= 16 else ""


def _extract_from_html(html: str, base_url: str, result: ScrapeResult) -> list[str]:
    """Parse one page, update result in-place, return same-domain links."""
    soup = BeautifulSoup(html, "html.parser")

    if not result.title and soup.title:
        result.title = soup.title.get_text(strip=True)[:200]
    if not result.description:
        meta = soup.find("meta", attrs={"name": "description"})
        if meta and meta.get("content"):
            result.description = meta["content"].strip()[:400]
    if not result.keywords:
        kw = soup.find("meta", attrs={"name": "keywords"})
        if kw and kw.get("content"):
            result.keywords = kw["content"].strip()[:300]

    text = soup.get_text(" ", strip=True)

    for email in EMAIL_RE.findall(text):
        email = email.lower()
        if email not in result.emails and not email.endswith((".png", ".jpg")):
            result.emails.append(email)

    # mailto / tel links are the most reliable.
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if href.startswith("mailto:"):
            em = href[7:].split("?")[0].strip().lower()
            if em and em not in result.emails:
                result.emails.append(em)
        elif href.startswith("tel:"):
            ph = _clean_phone(href[4:])
            if ph and ph not in result.phones:
                result.phones.append(ph)
        else:
            low = href.lower()
            for name, domain in SOCIAL_DOMAINS.items():
                if domain in low and name not in result.socials:
                    result.socials[name] = urljoin(base_url, href)

    for match in PHONE_RE.findall(text):
        ph = _clean_phone(match)
        if ph and ph not in result.phones and len(result.phones) < 12:
            result.phones.append(ph)

    # schema.org PostalAddress (best-effort)
    for addr in soup.find_all(attrs={"itemtype": re.compile("PostalAddress")}):
        a_text = addr.get_text(" ", strip=True)
        if a_text and a_text not in result.addresses:
            result.addresses.append(a_text[:300])
    for tag in soup.find_all("address"):
        a_text = tag.get_text(" ", strip=True)
        if a_text and a_text not in result.addresses:
            result.addresses.append(a_text[:300])

    # collect same-domain links for shallow crawl
    base_domain = urlparse(base_url).netloc
    links: list[str] = []
    for a in soup.find_all("a", href=True):
        full = urljoin(base_url, a["href"])
        if urlparse(full).netloc == base_domain and full.startswith("http"):
            links.append(full.split("#")[0])
    return links


def scrape_website(url: str, crawl: bool = False, max_pages: int = 5) -> ScrapeResult:
    """Scrape a single page, or shallow-crawl the same domain when ``crawl``."""
    url = _normalize_url(url)
    result = ScrapeResult(url=url)
    if not url:
        result.error = "Please provide a valid website URL."
        return result

    session = _session()
    to_visit = [url]
    visited: set[str] = set()
    cap = max_pages if crawl else 1

    while to_visit and len(visited) < cap:
        current = to_visit.pop(0)
        if current in visited:
            continue
        visited.add(current)
        try:
            resp = session.get(current, timeout=getattr(settings, "OSM_HTTP_TIMEOUT", 20))
            resp.raise_for_status()
            if "text/html" not in resp.headers.get("Content-Type", ""):
                continue
            links = _extract_from_html(resp.text, current, result)
        except requests.RequestException as exc:
            logger.warning("Scrape failed for %s: %s", current, exc)
            if not visited - {current}:  # first page failed
                result.error = f"Could not reach {url}."
            continue
        if crawl:
            for link in links:
                if link not in visited and link not in to_visit:
                    to_visit.append(link)

    result.pages_crawled = len(visited)
    # de-dupe & trim
    result.emails = result.emails[:50]
    result.phones = result.phones[:20]
    result.addresses = result.addresses[:10]
    if not result.emails and not result.phones and not result.error:
        result.error = ""  # not an error; just nothing found
    return result
