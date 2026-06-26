"""
LinkedIn lead intake for Forge OS.

LinkedIn actively blocks automated scraping and it violates their Terms of
Service, so this module does NOT scrape LinkedIn. Instead it provides a
compliant intake path:

* Parse a LinkedIn / Sales Navigator search URL to capture the query
  parameters (keywords, title, geo, industry) for record-keeping.
* Ingest leads that the user pastes (one per line: Name, Position, Company,
  Industry, Company Size, LinkedIn URL) — e.g. exported from their own
  connections or Sales Navigator list.

This keeps the feature useful and fully within policy.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from urllib.parse import parse_qs, urlparse


@dataclass
class LinkedInLead:
    name: str = ""
    position: str = ""
    company: str = ""
    industry: str = ""
    company_size: str = ""
    linkedin_url: str = ""


@dataclass
class LinkedInResult:
    query: str = ""
    parsed_filters: dict = field(default_factory=dict)
    leads: list[LinkedInLead] = field(default_factory=list)
    error: str = ""


def parse_search_url(url: str) -> dict:
    """Extract readable filters from a LinkedIn / Sales Navigator search URL."""
    if not url:
        return {}
    try:
        parts = urlparse(url)
    except ValueError:
        return {}
    q = parse_qs(parts.query)
    interesting = {
        "keywords": "Keywords",
        "title": "Title",
        "geoUrn": "Geo",
        "industry": "Industry",
        "company": "Company",
        "query": "Query",
    }
    out: dict[str, str] = {}
    for key, label in interesting.items():
        if key in q:
            out[label] = ", ".join(q[key])[:120]
    return out


def parse_pasted_leads(raw: str) -> list[LinkedInLead]:
    """Parse pasted rows into structured leads.

    Accepts comma- or tab-separated columns in the order:
    Name, Position, Company, Industry, Company Size, LinkedIn URL
    Missing trailing columns are tolerated.
    """
    leads: list[LinkedInLead] = []
    for line in (raw or "").splitlines():
        line = line.strip()
        if not line or line.lower().startswith("name,"):
            continue
        sep = "\t" if "\t" in line else ","
        cols = [c.strip() for c in line.split(sep)]
        cols += [""] * (6 - len(cols))
        if not cols[0]:
            continue
        leads.append(
            LinkedInLead(
                name=cols[0][:255],
                position=cols[1][:200],
                company=cols[2][:200],
                industry=cols[3][:160],
                company_size=cols[4][:80],
                linkedin_url=cols[5][:400],
            )
        )
    return leads


def ingest(search_url: str = "", pasted: str = "") -> LinkedInResult:
    result = LinkedInResult(query=search_url)
    if search_url:
        result.parsed_filters = parse_search_url(search_url)
    if pasted:
        result.leads = parse_pasted_leads(pasted)
    if not result.leads and not result.parsed_filters:
        result.error = (
            "Paste LinkedIn results (Name, Position, Company, Industry, "
            "Company Size, URL) or provide a search URL. Automated LinkedIn "
            "scraping is not permitted by LinkedIn's terms."
        )
    return result
