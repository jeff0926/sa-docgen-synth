"""
quality_audit.py
----------------
Real Quality Audit for Tech Specs

This script performs ACTUAL content quality validation, not just regex pattern matching.
It checks:
1. Source Authority - Are sources from authoritative domains?
2. Product Relevance - Does evidence actually reference the target product?
3. Text Quality - Are there concatenation/truncation artifacts?
4. URL Validity - Do source links actually work? (optional, slow)

Usage:
    python quality_audit.py                    # Audit all specs
    python quality_audit.py --product sap-event-mesh  # Audit one product
    python quality_audit.py --verify-urls      # Also check if URLs are reachable
    python quality_audit.py --output report.md # Save report to file

Author: Quality Fix Session 2026-04-13
"""

import re
import json
import argparse
from pathlib import Path
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlparse
import requests
from datetime import datetime

# ============================================================
# CONFIGURATION
# ============================================================

PRODUCTS_DIR = Path(r"C:\Users\I820965\dev\SA-Synthesis-Kit\products")
TECH_SPEC_FILENAME = "tech_spec_v3_0.md"

# Source Authority Weights (0.0 - 1.0)
AUTHORITY_WEIGHTS = {
    # SAP Official (highest authority)
    "help.sap.com": 1.0,
    "api.sap.com": 1.0,
    "developers.sap.com": 0.95,
    "www.sap.com": 0.9,
    "sap.com": 0.9,
    "community.sap.com": 0.7,
    "blogs.sap.com": 0.65,
    "news.sap.com": 0.6,

    # Adobe Official
    "experienceleague.adobe.com": 0.95,
    "developer.adobe.com": 0.95,
    "adobe.com": 0.85,

    # Tech Documentation (good)
    "docs.microsoft.com": 0.8,
    "learn.microsoft.com": 0.8,
    "cloud.google.com": 0.8,
    "docs.aws.amazon.com": 0.8,

    # Developer Resources (acceptable)
    "github.com": 0.6,
    "stackoverflow.com": 0.5,
    "medium.com": 0.4,

    # Low Authority (suspicious for enterprise docs)
    "linkedin.com": 0.2,
    "twitter.com": 0.1,
    "habr.com": 0.1,  # Russian tech blog
    "leverx.com": 0.3,

    # Default for unknown
    "_default": 0.3,
}

# Text artifact patterns (indicate poor quality)
TEXT_ARTIFACT_PATTERNS = [
    # Concatenation artifacts (missing spaces)
    (r'[a-z][A-Z]{2,}[a-z]', "CamelCase concatenation"),  # theOAuth -> theOAuth
    (r'\w{3,}OAuth', "OAuth concatenation"),  # theOAuth2.0
    (r'\w{3,}API\w', "API concatenation"),  # theAPIkey
    (r'\w{3,}JSON\w', "JSON concatenation"),  # theJSONSchema
    (r'\w{3,}HTTP\w', "HTTP concatenation"),  # theHTTPstatus
    (r'[a-z]{3,}Schema[a-z]', "Schema concatenation"),
    (r'[a-z]{3,}Error[a-z]', "Error concatenation"),
    (r'codes[a-z]{3,}', "codes concatenation"),  # errorcodesthat

    # Truncation artifacts
    (r'\.\.\.\s*$', "Truncated content (ends with ...)"),
    (r'\w{5,}\s*\.\.\.\s*\w{5,}', "Mid-sentence truncation"),

    # Wrong language content
    (r'[а-яА-Я]{5,}', "Russian/Cyrillic text"),
    (r'[一-龥]{3,}', "Chinese characters"),
]

# Irrelevant content markers (wrong product references)
IRRELEVANT_MARKERS = [
    "Gmail",
    "Auth0",
    "Okta",  # Unless specifically about identity
    "Firebase",
    "Twilio",
]


# ============================================================
# DATA STRUCTURES
# ============================================================

@dataclass
class EvidenceItem:
    """Represents a single piece of evidence from the spec."""
    text: str
    source_url: Optional[str] = None
    pillar_id: Optional[str] = None
    line_number: int = 0


@dataclass
class QualityScore:
    """Quality scores for a single tech spec."""
    product_slug: str
    source_authority_score: float = 0.0
    product_relevance_score: float = 0.0
    text_quality_score: float = 0.0
    url_validity_score: float = 0.0  # Only if --verify-urls

    # Detailed findings
    total_evidence_items: int = 0
    authoritative_sources: int = 0
    low_authority_sources: int = 0
    relevant_evidence: int = 0
    irrelevant_evidence: int = 0
    text_artifacts_found: List[str] = field(default_factory=list)
    broken_urls: List[str] = field(default_factory=list)
    wrong_product_refs: List[str] = field(default_factory=list)

    # Source breakdown
    sources_by_domain: Dict[str, int] = field(default_factory=dict)

    @property
    def overall_score(self) -> float:
        """Compute weighted overall score (0-3 scale like current system)."""
        weights = {
            "authority": 0.35,
            "relevance": 0.35,
            "text_quality": 0.20,
            "url_validity": 0.10,
        }

        score = (
            self.source_authority_score * weights["authority"] +
            self.product_relevance_score * weights["relevance"] +
            self.text_quality_score * weights["text_quality"] +
            self.url_validity_score * weights["url_validity"]
        )

        return round(score * 3.0, 2)  # Scale to 0-3

    @property
    def grade(self) -> str:
        """Determine grade based on actual quality."""
        score = self.overall_score

        # Hard failures
        if self.irrelevant_evidence > 3:
            return "BLOCKED"
        if len(self.text_artifacts_found) > 10:
            return "BLOCKED"
        if self.source_authority_score < 0.3:
            return "BLOCKED"

        # Grade thresholds
        if score >= 2.4 and self.product_relevance_score >= 0.9:
            return "ELITE"
        elif score >= 2.0:
            return "ACCEPTABLE"
        else:
            return "BLOCKED"


# ============================================================
# PARSING FUNCTIONS
# ============================================================

def extract_evidence_items(content: str) -> List[EvidenceItem]:
    """Extract evidence items from tech spec content."""
    evidence_items = []
    lines = content.split('\n')

    current_pillar = None

    for i, line in enumerate(lines, 1):
        # Track current pillar
        pillar_match = re.match(r'##\s*(P\d{2}):', line)
        if pillar_match:
            current_pillar = pillar_match.group(1)
            continue

        # Extract evidence from table rows
        if '| **Evidence**' in line or '| Evidence |' in line.replace(' ', ''):
            # Extract the evidence text after the pipe
            parts = line.split('|')
            if len(parts) >= 3:
                evidence_text = parts[2].strip()
                evidence_items.append(EvidenceItem(
                    text=evidence_text,
                    pillar_id=current_pillar,
                    line_number=i,
                ))

        # Extract source URLs
        if '| **Source**' in line:
            parts = line.split('|')
            if len(parts) >= 3:
                url_text = parts[2].strip()
                # Find URL in text
                url_match = re.search(r'https?://[^\s\|]+', url_text)
                if url_match and evidence_items:
                    evidence_items[-1].source_url = url_match.group(0)

    return evidence_items


def extract_all_urls(content: str) -> List[str]:
    """Extract all URLs from content."""
    url_pattern = r'https?://[^\s\)\]\|<>\"\'`]+'
    urls = re.findall(url_pattern, content)
    # Clean up trailing punctuation
    cleaned = []
    for url in urls:
        url = url.rstrip('.,;:')
        if url:
            cleaned.append(url)
    return list(set(cleaned))


def get_domain(url: str) -> str:
    """Extract domain from URL."""
    try:
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        # Remove www. prefix
        if domain.startswith('www.'):
            domain = domain[4:]
        return domain
    except:
        return "unknown"


# ============================================================
# SCORING FUNCTIONS
# ============================================================

def score_source_authority(urls: List[str]) -> Tuple[float, Dict[str, int]]:
    """Score source authority based on URL domains."""
    if not urls:
        return 0.0, {}

    domain_counts = {}
    total_weight = 0.0

    for url in urls:
        domain = get_domain(url)
        domain_counts[domain] = domain_counts.get(domain, 0) + 1

        # Find matching weight
        weight = AUTHORITY_WEIGHTS.get("_default")
        for pattern, w in AUTHORITY_WEIGHTS.items():
            if pattern in domain:
                weight = w
                break

        total_weight += weight

    avg_score = total_weight / len(urls)
    return avg_score, domain_counts


def score_product_relevance(
    content: str,
    evidence_items: List[EvidenceItem],
    product_slug: str
) -> Tuple[float, int, int, List[str]]:
    """Check if evidence is relevant to the target product."""

    # Extract product name variations from slug
    product_name = product_slug.replace("-", " ").title()
    product_parts = product_slug.replace("-", " ").split()

    # Key terms that should appear in relevant evidence
    key_terms = [product_slug, product_name.lower()]
    key_terms.extend([p for p in product_parts if len(p) > 3])

    relevant_count = 0
    irrelevant_count = 0
    wrong_refs = []

    for item in evidence_items:
        text_lower = item.text.lower()

        # Check for irrelevant markers
        found_irrelevant = False
        for marker in IRRELEVANT_MARKERS:
            if marker.lower() in text_lower:
                # Exception: If it's actually about that product
                if marker.lower() not in product_slug:
                    irrelevant_count += 1
                    wrong_refs.append(f"Line {item.line_number}: Found '{marker}' in {product_slug} doc")
                    found_irrelevant = True
                    break

        if not found_irrelevant:
            # Check for product relevance
            has_relevance = any(term.lower() in text_lower for term in key_terms)

            # Also check for generic SAP terms if it's an SAP product
            if product_slug.startswith("sap-"):
                if "sap" in text_lower or "btp" in text_lower:
                    has_relevance = True

            if has_relevance:
                relevant_count += 1
            # Don't count as irrelevant if it's generic tech content

    total = len(evidence_items)
    if total == 0:
        return 0.0, 0, 0, []

    # Penalize heavily for wrong product references
    relevance_score = relevant_count / total
    if irrelevant_count > 0:
        penalty = min(0.5, irrelevant_count * 0.1)
        relevance_score = max(0, relevance_score - penalty)

    return relevance_score, relevant_count, irrelevant_count, wrong_refs


def score_text_quality(content: str) -> Tuple[float, List[str]]:
    """Check for text artifacts indicating poor quality."""
    artifacts_found = []

    for pattern, description in TEXT_ARTIFACT_PATTERNS:
        matches = re.findall(pattern, content)
        if matches:
            # Limit to first 3 examples
            examples = matches[:3]
            artifacts_found.append(f"{description}: {examples}")

    # Score: 1.0 = no artifacts, decreases with more artifacts
    artifact_count = len(artifacts_found)
    if artifact_count == 0:
        score = 1.0
    elif artifact_count <= 2:
        score = 0.8
    elif artifact_count <= 5:
        score = 0.5
    else:
        score = 0.2

    return score, artifacts_found


def verify_urls(urls: List[str], timeout: int = 5) -> Tuple[float, List[str]]:
    """Verify URLs are reachable (optional, slow)."""
    if not urls:
        return 1.0, []

    broken = []
    valid_count = 0

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }

    # Sample up to 10 URLs to avoid slowness
    sample = urls[:10]

    for url in sample:
        try:
            r = requests.head(url, timeout=timeout, headers=headers, allow_redirects=True)
            if r.status_code < 400:
                valid_count += 1
            else:
                broken.append(f"{url} (HTTP {r.status_code})")
        except requests.RequestException as e:
            broken.append(f"{url} (Error: {type(e).__name__})")

    score = valid_count / len(sample) if sample else 1.0
    return score, broken


# ============================================================
# MAIN AUDIT FUNCTION
# ============================================================

def audit_tech_spec(
    product_slug: str,
    spec_path: Path,
    verify_urls_flag: bool = False
) -> QualityScore:
    """Run full quality audit on a tech spec."""

    content = spec_path.read_text(encoding="utf-8")

    # Extract data
    evidence_items = extract_evidence_items(content)
    all_urls = extract_all_urls(content)

    # Score components
    authority_score, domain_counts = score_source_authority(all_urls)
    relevance_score, relevant, irrelevant, wrong_refs = score_product_relevance(
        content, evidence_items, product_slug
    )
    text_score, artifacts = score_text_quality(content)

    # Optional URL verification
    url_score = 1.0
    broken_urls = []
    if verify_urls_flag:
        url_score, broken_urls = verify_urls(all_urls)

    # Build result
    result = QualityScore(
        product_slug=product_slug,
        source_authority_score=authority_score,
        product_relevance_score=relevance_score,
        text_quality_score=text_score,
        url_validity_score=url_score,
        total_evidence_items=len(evidence_items),
        authoritative_sources=sum(1 for u in all_urls if score_source_authority([u])[0] >= 0.7),
        low_authority_sources=sum(1 for u in all_urls if score_source_authority([u])[0] < 0.4),
        relevant_evidence=relevant,
        irrelevant_evidence=irrelevant,
        text_artifacts_found=artifacts,
        broken_urls=broken_urls,
        wrong_product_refs=wrong_refs,
        sources_by_domain=domain_counts,
    )

    return result


def audit_all_products(
    products_dir: Path,
    verify_urls_flag: bool = False,
    single_product: Optional[str] = None
) -> List[QualityScore]:
    """Audit all products or a single product."""

    results = []

    if single_product:
        product_dirs = [products_dir / single_product]
    else:
        product_dirs = sorted([d for d in products_dir.iterdir() if d.is_dir()])

    for product_dir in product_dirs:
        spec_path = product_dir / TECH_SPEC_FILENAME

        if not spec_path.exists():
            continue

        product_slug = product_dir.name

        # Skip non-SAP products for this audit
        if not product_slug.startswith("sap-"):
            continue

        print(f"  Auditing: {product_slug}...", end=" ", flush=True)

        try:
            result = audit_tech_spec(product_slug, spec_path, verify_urls_flag)
            results.append(result)
            print(f"{result.grade} ({result.overall_score})")
        except Exception as e:
            print(f"ERROR: {e}")

    return results


# ============================================================
# REPORT GENERATION
# ============================================================

def generate_report(results: List[QualityScore]) -> str:
    """Generate markdown quality report."""

    lines = [
        "# Real Quality Audit Report",
        f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        f"**Products Audited:** {len(results)}",
        "",
        "---",
        "",
        "## Summary",
        "",
    ]

    # Count grades
    grade_counts = {"ELITE": 0, "ACCEPTABLE": 0, "BLOCKED": 0}
    for r in results:
        grade_counts[r.grade] = grade_counts.get(r.grade, 0) + 1

    lines.append(f"| Grade | Count |")
    lines.append(f"|-------|-------|")
    for grade, count in grade_counts.items():
        marker = {"ELITE": "[OK]", "ACCEPTABLE": "[--]", "BLOCKED": "[XX]"}[grade]
        lines.append(f"| {marker} {grade} | {count} |")

    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## Detailed Results")
    lines.append("")
    lines.append("| Product | Old Grade | Real Grade | Score | Authority | Relevance | Text Quality | Issues |")
    lines.append("|---------|-----------|------------|-------|-----------|-----------|--------------|--------|")

    for r in sorted(results, key=lambda x: x.overall_score, reverse=True):
        issues = []
        if r.irrelevant_evidence > 0:
            issues.append(f"{r.irrelevant_evidence} wrong refs")
        if len(r.text_artifacts_found) > 0:
            issues.append(f"{len(r.text_artifacts_found)} artifacts")
        if r.low_authority_sources > r.authoritative_sources:
            issues.append("low auth sources")

        issue_str = ", ".join(issues) if issues else "None"

        lines.append(
            f"| {r.product_slug} | ELITE | **{r.grade}** | {r.overall_score} | "
            f"{r.source_authority_score:.0%} | {r.product_relevance_score:.0%} | "
            f"{r.text_quality_score:.0%} | {issue_str} |"
        )

    # Detailed findings for blocked products
    blocked = [r for r in results if r.grade == "BLOCKED"]
    if blocked:
        lines.append("")
        lines.append("---")
        lines.append("")
        lines.append("## Blocked Products - Detailed Issues")
        lines.append("")

        for r in blocked:
            lines.append(f"### {r.product_slug}")
            lines.append("")

            if r.wrong_product_refs:
                lines.append("**Wrong Product References:**")
                for ref in r.wrong_product_refs[:5]:
                    lines.append(f"- {ref}")
                lines.append("")

            if r.text_artifacts_found:
                lines.append("**Text Artifacts:**")
                for artifact in r.text_artifacts_found[:5]:
                    lines.append(f"- {artifact}")
                lines.append("")

            if r.sources_by_domain:
                lines.append("**Sources by Domain:**")
                for domain, count in sorted(r.sources_by_domain.items(), key=lambda x: -x[1])[:5]:
                    weight = AUTHORITY_WEIGHTS.get(domain, AUTHORITY_WEIGHTS["_default"])
                    lines.append(f"- {domain}: {count} refs (authority: {weight})")
                lines.append("")

    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## Methodology")
    lines.append("")
    lines.append("This audit checks:")
    lines.append("1. **Source Authority** - Are evidence sources from official documentation?")
    lines.append("2. **Product Relevance** - Does evidence actually reference the target product?")
    lines.append("3. **Text Quality** - Are there concatenation/truncation artifacts?")
    lines.append("4. **URL Validity** - Do source links work? (if --verify-urls)")
    lines.append("")
    lines.append("Unlike the broken regex-only checker, this validates actual content quality.")

    return "\n".join(lines)


# ============================================================
# CLI
# ============================================================

def main():
    parser = argparse.ArgumentParser(description="Real Quality Audit for Tech Specs")
    parser.add_argument("--product", help="Audit single product by slug")
    parser.add_argument("--verify-urls", action="store_true", help="Also verify URLs are reachable (slow)")
    parser.add_argument("--output", help="Save report to file")

    args = parser.parse_args()

    print("=" * 70)
    print("REAL QUALITY AUDIT")
    print("=" * 70)
    print()

    if not PRODUCTS_DIR.exists():
        print(f"ERROR: Products directory not found: {PRODUCTS_DIR}")
        return 1

    print(f"Products directory: {PRODUCTS_DIR}")
    print(f"Verify URLs: {args.verify_urls}")
    print()

    results = audit_all_products(
        PRODUCTS_DIR,
        verify_urls_flag=args.verify_urls,
        single_product=args.product,
    )

    if not results:
        print("No products found to audit.")
        return 1

    print()
    print("=" * 70)
    print("GENERATING REPORT")
    print("=" * 70)
    print()

    report = generate_report(results)

    if args.output:
        output_path = Path(args.output)
        output_path.write_text(report, encoding="utf-8")
        print(f"Report saved to: {output_path}")
    else:
        # Print summary to console
        print(report)

    # Summary stats
    print()
    print("=" * 70)
    grade_counts = {"ELITE": 0, "ACCEPTABLE": 0, "BLOCKED": 0}
    for r in results:
        grade_counts[r.grade] = grade_counts.get(r.grade, 0) + 1

    print(f"ELITE: {grade_counts['ELITE']} | ACCEPTABLE: {grade_counts['ACCEPTABLE']} | BLOCKED: {grade_counts['BLOCKED']}")
    print("=" * 70)

    return 0


if __name__ == "__main__":
    exit(main())
