"""
AI Lead Enrichment service for Forge OS.

Enriches a lead with firmographics and an AI-generated summary / score.
It combines free website scraping (for real signals such as social links,
emails and description) with an LLM call (via the sandbox OpenAI-compatible
endpoint configured in the environment) to produce:

    * Company description / AI business summary
    * Industry & business category
    * Estimated employee count
    * Technologies used (best-effort)
    * Social links & domain
    * AI lead score (0-100)

If the LLM is unavailable, a deterministic heuristic fallback is used so the
feature still works offline.
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field
from urllib.parse import urlparse

from .scraper import scrape_website

logger = logging.getLogger("leads")


@dataclass
class EnrichmentResult:
    description: str = ""
    industry: str = ""
    employee_count: str = ""
    technologies: list = field(default_factory=list)
    social_links: dict = field(default_factory=dict)
    domain: str = ""
    business_category: str = ""
    ai_summary: str = ""
    ai_score: int = 0
    error: str = ""


def _domain_from(business) -> str:
    site = getattr(business, "website", "") or ""
    if site:
        return urlparse(site if site.startswith("http") else "https://" + site).netloc
    return ""


def _llm_enrich(context: dict) -> dict | None:
    """Call the OpenAI-compatible endpoint; return parsed JSON or None."""
    if not os.environ.get("OPENAI_API_KEY"):
        return None
    try:
        from openai import OpenAI

        client = OpenAI()
        model = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
        prompt = (
            "You are a B2B lead enrichment engine. Given the business data "
            "below, respond ONLY with compact JSON having keys: description, "
            "industry, employee_count, technologies (array), business_category, "
            "ai_summary, ai_score (0-100 integer estimating lead quality). "
            "Base it on the data; do not invent contact details.\n\n"
            f"DATA:\n{json.dumps(context, ensure_ascii=False)}"
        )
        resp = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.4,
            max_tokens=500,
        )
        text = resp.choices[0].message.content.strip()
        if text.startswith("```"):
            text = text.strip("`")
            text = text[text.find("{"):]
        return json.loads(text[text.find("{"): text.rfind("}") + 1])
    except Exception as exc:  # noqa: BLE001
        logger.info("LLM enrichment unavailable: %s", exc)
        return None


def _heuristic(context: dict, scrape) -> dict:
    name = context.get("name", "")
    category = context.get("category", "") or "Business"
    has_site = bool(context.get("website"))
    has_phone = bool(context.get("phone"))
    has_email = bool(context.get("email") or (scrape and scrape.emails))
    score = 40 + (20 if has_site else 0) + (15 if has_phone else 0) + (15 if has_email else 0)
    score = min(score, 95)
    desc = scrape.description if scrape and scrape.description else (
        f"{name} is a {category.lower()} business."
    )
    return {
        "description": desc,
        "industry": category,
        "employee_count": "Unknown",
        "technologies": [],
        "business_category": category,
        "ai_summary": (
            f"{name} ({category}). Reachability: "
            f"{'website ' if has_site else ''}"
            f"{'phone ' if has_phone else ''}"
            f"{'email' if has_email else ''}".strip()
            or "Limited public contact signals."
        ),
        "ai_score": score,
    }


def enrich_business(business) -> EnrichmentResult:
    """Enrich a :class:`leads.models.Business` instance."""
    result = EnrichmentResult()
    domain = _domain_from(business)
    result.domain = domain

    scrape = None
    if getattr(business, "website", ""):
        try:
            scrape = scrape_website(business.website, crawl=False)
            if scrape.socials:
                result.social_links = scrape.socials
        except Exception as exc:  # noqa: BLE001
            logger.info("Enrichment scrape failed: %s", exc)

    context = {
        "name": getattr(business, "name", ""),
        "category": getattr(business, "category", ""),
        "address": getattr(business, "address", ""),
        "phone": getattr(business, "phone", ""),
        "email": getattr(business, "email", ""),
        "website": getattr(business, "website", ""),
        "domain": domain,
        "scraped_description": getattr(scrape, "description", "") if scrape else "",
        "scraped_emails": getattr(scrape, "emails", []) if scrape else [],
    }

    data = _llm_enrich(context) or _heuristic(context, scrape)

    result.description = str(data.get("description", ""))[:2000]
    result.industry = str(data.get("industry", ""))[:160]
    result.employee_count = str(data.get("employee_count", ""))[:80]
    techs = data.get("technologies", [])
    result.technologies = techs if isinstance(techs, list) else [str(techs)]
    result.business_category = str(data.get("business_category", ""))[:160]
    result.ai_summary = str(data.get("ai_summary", ""))[:2000]
    try:
        result.ai_score = max(0, min(100, int(data.get("ai_score", 0))))
    except (TypeError, ValueError):
        result.ai_score = 0
    if scrape and scrape.socials and not result.social_links:
        result.social_links = scrape.socials
    return result
