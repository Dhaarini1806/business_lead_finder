"""
Email Finder & Verifier service for Forge OS.

Free, best-effort professional email discovery and verification — no paid APIs:

* **Find**: generate the common professional email patterns for a person at a
  domain (first.last@, first@, flast@, etc.).
* **Verify**: check domain MX records and attempt a lightweight SMTP RCPT
  probe to estimate deliverability, returning a confidence score and a
  mailbox status (verified / risky / invalid).

SMTP probing is rate-limited and many providers (Google, Microsoft) accept all
RCPTs, so results are heuristic. We never send an actual email.
"""

from __future__ import annotations

import logging
import re
import smtplib
import socket
from dataclasses import dataclass, field

logger = logging.getLogger("leads")

try:
    import dns.resolver  # type: ignore
    _HAS_DNS = True
except Exception:  # noqa: BLE001
    _HAS_DNS = False

EMAIL_RE = re.compile(r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$")


@dataclass
class EmailCandidate:
    email: str
    status: str = "unknown"      # verified / risky / invalid / unknown
    confidence: int = 0          # 0-100
    pattern: str = ""


@dataclass
class EmailResult:
    domain: str = ""
    person: str = ""
    company: str = ""
    candidates: list[EmailCandidate] = field(default_factory=list)
    mx_found: bool = False
    error: str = ""

    @property
    def best(self) -> EmailCandidate | None:
        return self.candidates[0] if self.candidates else None


def _clean_domain(domain: str) -> str:
    domain = (domain or "").strip().lower()
    domain = re.sub(r"^https?://", "", domain)
    domain = domain.split("/")[0]
    if domain.startswith("www."):
        domain = domain[4:]
    return domain


def _name_parts(person: str) -> tuple[str, str]:
    parts = [p for p in re.split(r"\s+", (person or "").strip().lower()) if p]
    parts = [re.sub(r"[^a-z]", "", p) for p in parts]
    parts = [p for p in parts if p]
    if not parts:
        return "", ""
    if len(parts) == 1:
        return parts[0], ""
    return parts[0], parts[-1]


def _patterns(first: str, last: str, domain: str) -> list[tuple[str, str]]:
    """Return (email, pattern_label) ordered by likelihood."""
    out: list[tuple[str, str]] = []
    if first and last:
        out += [
            (f"{first}.{last}@{domain}", "first.last"),
            (f"{first}{last}@{domain}", "firstlast"),
            (f"{first[0]}{last}@{domain}", "flast"),
            (f"{first}@{domain}", "first"),
            (f"{first}_{last}@{domain}", "first_last"),
            (f"{last}.{first}@{domain}", "last.first"),
            (f"{first[0]}.{last}@{domain}", "f.last"),
        ]
    elif first:
        out += [(f"{first}@{domain}", "first")]
    # generic role inboxes as fallback
    out += [
        (f"info@{domain}", "info"),
        (f"contact@{domain}", "contact"),
        (f"hello@{domain}", "hello"),
        (f"sales@{domain}", "sales"),
    ]
    # de-dupe preserving order
    seen, uniq = set(), []
    for email, label in out:
        if email not in seen:
            seen.add(email)
            uniq.append((email, label))
    return uniq


def _get_mx(domain: str) -> list[str]:
    if _HAS_DNS:
        try:
            answers = dns.resolver.resolve(domain, "MX", lifetime=6)
            records = sorted(
                ((r.preference, str(r.exchange).rstrip(".")) for r in answers)
            )
            return [host for _, host in records]
        except Exception as exc:  # noqa: BLE001
            logger.info("MX lookup failed for %s: %s", domain, exc)
            return []
    # Fallback: no dnspython -> can only confirm the domain resolves.
    try:
        socket.gethostbyname(domain)
        return [domain]
    except OSError:
        return []


def _smtp_probe(mx_host: str, email: str) -> str:
    """Return 'verified', 'risky' (accept-all/unknown) or 'invalid'."""
    try:
        server = smtplib.SMTP(timeout=8)
        server.connect(mx_host, 25)
        server.helo("forge-os.local")
        server.mail("verify@forge-os.local")
        code, _ = server.rcpt(email)
        # Probe a clearly bogus address to detect accept-all servers.
        bogus = "zz-nonexistent-" + email.split("@")[0] + "@" + email.split("@")[1]
        bogus_code, _ = server.rcpt(bogus)
        server.quit()
        if code in (250, 251):
            return "risky" if bogus_code in (250, 251) else "verified"
        if code in (550, 551, 553):
            return "invalid"
        return "risky"
    except (smtplib.SMTPException, socket.error, OSError) as exc:
        logger.info("SMTP probe failed for %s: %s", email, exc)
        return "risky"


def find_emails(person: str, domain: str, company: str = "",
                verify: bool = True, max_candidates: int = 6) -> EmailResult:
    domain = _clean_domain(domain)
    result = EmailResult(domain=domain, person=person, company=company)
    if not domain or "." not in domain:
        result.error = "Please provide a valid company domain (e.g. acme.com)."
        return result

    first, last = _name_parts(person)
    patterns = _patterns(first, last, domain)[:max_candidates]

    mx = _get_mx(domain)
    result.mx_found = bool(mx)

    for email, label in patterns:
        cand = EmailCandidate(email=email, pattern=label)
        if not EMAIL_RE.match(email):
            cand.status, cand.confidence = "invalid", 0
        elif not result.mx_found:
            cand.status, cand.confidence = "invalid", 10
        elif verify and mx and mx[0] != domain:
            status = _smtp_probe(mx[0], email)
            cand.status = status
            cand.confidence = {"verified": 95, "risky": 60, "invalid": 5}.get(status, 50)
        else:
            # MX exists but we couldn't SMTP-probe -> pattern likelihood only.
            base = {"first.last": 80, "flast": 72, "firstlast": 68,
                    "first": 60}.get(label, 45)
            cand.status, cand.confidence = "risky", base
        result.candidates.append(cand)

    result.candidates.sort(key=lambda c: c.confidence, reverse=True)
    return result
