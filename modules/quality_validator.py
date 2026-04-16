"""
modules/quality_validator.py
----------------------------
Real Quality Validation for Tech Specs

This module provides actual content quality validation to replace
the broken regex-only checking in the orchestrator.

Validates:
1. Source Authority - Are sources from authoritative domains?
2. Product Relevance - Does evidence reference the target product?
3. Text Quality - Are there concatenation/truncation artifacts?
4. Content Coherence - Is the content well-formed?

Usage in orchestrator.py:
    from modules.quality_validator import validate_spec_quality, QualityGrade

    result = validate_spec_quality(content, product_slug)
    if result.grade == QualityGrade.ELITE:
        # Proceed
    else:
        # Reject with result.issues

Author: Quality Fix Session 2026-04-13
"""

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlparse


# ============================================================
# ENUMS & CONSTANTS
# ============================================================

class QualityGrade(Enum):
    """Quality grades based on real validation."""
    ELITE = "ELITE"
    ACCEPTABLE = "ACCEPTABLE"
    BLOCKED = "BLOCKED"


# Source Authority Weights (0.0 - 1.0)
AUTHORITY_WEIGHTS = {
    # SAP Official (highest authority)
    "help.sap.com": 1.0,
    "api.sap.com": 1.0,
    "developers.sap.com": 0.95,
    "www.sap.com": 0.9,
    "sap.com": 0.9,
    ".sap": 0.9,  # SAP cloud domains (*.services.cloud.sap, *.em.services.cloud.sap)
    "community.sap.com": 0.7,
    "blogs.sap.com": 0.65,
    "news.sap.com": 0.6,
    "learning.sap.com": 0.6,

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
    "habr.com": 0.1,
    "leverx.com": 0.3,

    # Default for unknown
    "_default": 0.3,
}


# Text artifact patterns that indicate poor quality
TEXT_ARTIFACT_PATTERNS = [
    # Concatenation artifacts (missing spaces)
    (r'[a-z][A-Z]{2,}[a-z]', "camelcase_concat"),
    (r'\w{3,}OAuth', "oauth_concat"),
    (r'\w{3,}API\w', "api_concat"),
    (r'\w{3,}JSON\w', "json_concat"),
    (r'\w{3,}HTTP\w', "http_concat"),
    (r'[a-z]{3,}Schema[a-z]', "schema_concat"),
    (r'[a-z]{3,}Error[a-z]', "error_concat"),
    (r'codes[a-z]{3,}', "codes_concat"),

    # Truncation artifacts
    (r'\w{5,}\s*\.\.\.\s*\w{5,}', "mid_truncation"),

    # Wrong language content
    (r'[а-яА-Я]{5,}', "cyrillic_text"),
]


# Markers that indicate wrong product evidence
IRRELEVANT_PRODUCT_MARKERS = [
    "Gmail",
    "Auth0",
    "Okta",
    "Firebase",
    "Twilio",
    "Stripe",
]


# ============================================================
# DATA STRUCTURES
# ============================================================

@dataclass
class QualityResult:
    """Complete quality validation result."""
    grade: QualityGrade
    overall_score: float  # 0.0 - 3.0 scale

    # Component scores (0.0 - 1.0)
    source_authority_score: float = 0.0
    product_relevance_score: float = 0.0
    text_quality_score: float = 0.0
    content_coherence_score: float = 0.0

    # Issues found
    issues: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    # Detailed findings
    text_artifacts: List[str] = field(default_factory=list)
    wrong_product_refs: List[str] = field(default_factory=list)
    low_authority_sources: List[str] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        """Check if spec passed minimum quality bar."""
        return self.grade in (QualityGrade.ELITE, QualityGrade.ACCEPTABLE)

    @property
    def summary(self) -> str:
        """One-line summary for logging."""
        return (
            f"{self.grade.value} ({self.overall_score:.2f}) - "
            f"Auth:{self.source_authority_score:.0%} "
            f"Rel:{self.product_relevance_score:.0%} "
            f"Text:{self.text_quality_score:.0%}"
        )


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def get_domain(url: str) -> str:
    """Extract domain from URL."""
    try:
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        if domain.startswith('www.'):
            domain = domain[4:]
        return domain
    except:
        return "unknown"


def get_authority_weight(domain: str) -> float:
    """Get authority weight for a domain."""
    # Check exact match first
    if domain in AUTHORITY_WEIGHTS:
        return AUTHORITY_WEIGHTS[domain]

    # Check suffix match (for patterns like .sap, .adobe.com)
    for pattern, weight in AUTHORITY_WEIGHTS.items():
        if pattern != "_default":
            if pattern.startswith('.') and domain.endswith(pattern):
                return weight
            elif pattern in domain:
                return weight

    return AUTHORITY_WEIGHTS["_default"]


def extract_urls(content: str) -> List[str]:
    """Extract all URLs from content."""
    url_pattern = r'https?://[^\s\)\]\|<>\"\'`]+'
    urls = re.findall(url_pattern, content)
    return [url.rstrip('.,;:') for url in set(urls) if url]


def extract_evidence_text(content: str) -> List[str]:
    """Extract evidence text from content."""
    evidence_items = []

    # Match evidence in table rows
    evidence_pattern = r'\|\s*\*?\*?Evidence\*?\*?\s*\|\s*([^|]+)\|'
    matches = re.findall(evidence_pattern, content, re.IGNORECASE)
    evidence_items.extend(matches)

    # Also match from Implementation Details sections
    impl_pattern = r'^\d+\.\s+(.+)$'
    for line in content.split('\n'):
        match = re.match(impl_pattern, line.strip())
        if match and len(match.group(1)) > 20:
            evidence_items.append(match.group(1))

    return evidence_items


# ============================================================
# SCORING FUNCTIONS
# ============================================================

def score_source_authority(content: str) -> Tuple[float, List[str]]:
    """
    Score source authority based on URL domains.

    Returns:
        Tuple of (score 0-1, list of low authority sources)
    """
    urls = extract_urls(content)

    if not urls:
        return 0.5, ["No source URLs found"]

    total_weight = 0.0
    low_authority = []

    for url in urls:
        domain = get_domain(url)
        weight = get_authority_weight(domain)
        total_weight += weight

        if weight < 0.5:
            low_authority.append(f"{domain} ({weight:.1f})")

    avg_score = total_weight / len(urls)
    return avg_score, low_authority


def score_product_relevance(
    content: str,
    product_slug: str
) -> Tuple[float, List[str]]:
    """
    Check if evidence is relevant to the target product.

    Returns:
        Tuple of (score 0-1, list of wrong product references)
    """
    evidence_items = extract_evidence_text(content)

    if not evidence_items:
        return 0.5, ["No evidence items found"]

    # Build product name variations
    product_name = product_slug.replace("-", " ").lower()
    key_terms = [product_slug.lower(), product_name]

    # Add component terms (e.g., "event" and "mesh" for "sap-event-mesh")
    parts = product_slug.replace("sap-", "").split("-")
    key_terms.extend([p for p in parts if len(p) > 3])

    # For SAP products, "sap" and "btp" are always relevant
    if product_slug.startswith("sap-"):
        key_terms.extend(["sap", "btp"])

    relevant_count = 0
    wrong_refs = []

    for evidence in evidence_items:
        evidence_lower = evidence.lower()

        # Check for irrelevant markers
        found_irrelevant = False
        for marker in IRRELEVANT_PRODUCT_MARKERS:
            if marker.lower() in evidence_lower:
                # Only flag if this product shouldn't reference it
                if marker.lower() not in product_slug.lower():
                    wrong_refs.append(f"'{marker}' in evidence")
                    found_irrelevant = True
                    break

        if not found_irrelevant:
            # Check for product relevance
            if any(term in evidence_lower for term in key_terms):
                relevant_count += 1

    total = len(evidence_items)
    base_score = relevant_count / total if total > 0 else 0

    # Penalize for wrong product references
    if wrong_refs:
        penalty = min(0.3, len(wrong_refs) * 0.05)
        base_score = max(0, base_score - penalty)

    return base_score, wrong_refs


def score_text_quality(content: str) -> Tuple[float, List[str]]:
    """
    Check for text artifacts indicating poor quality.

    Returns:
        Tuple of (score 0-1, list of artifacts found)
    """
    artifacts_found = []

    for pattern, artifact_type in TEXT_ARTIFACT_PATTERNS:
        matches = re.findall(pattern, content)
        if matches:
            # Dedupe and limit
            unique_matches = list(set(matches))[:3]
            artifacts_found.append(f"{artifact_type}: {unique_matches}")

    # Score based on artifact count
    artifact_count = len(artifacts_found)
    if artifact_count == 0:
        score = 1.0
    elif artifact_count <= 2:
        score = 0.8
    elif artifact_count <= 4:
        score = 0.5
    elif artifact_count <= 6:
        score = 0.3
    else:
        score = 0.2

    return score, artifacts_found


def score_content_coherence(content: str, product_slug: str) -> Tuple[float, List[str]]:
    """
    Check content coherence and structure.

    Returns:
        Tuple of (score 0-1, list of issues)
    """
    issues = []

    # Check minimum length
    if len(content) < 5000:
        issues.append(f"Content too short ({len(content)} chars, min 5000)")

    # Check for critical sections
    required_sections = ["Authentication", "Error Handling", "Evidence"]
    for section in required_sections:
        if section.lower() not in content.lower():
            issues.append(f"Missing section: {section}")

    # Check pillar coverage
    pillar_count = len(re.findall(r'##\s*P\d{2}:', content))
    if pillar_count < 10:
        issues.append(f"Low pillar coverage ({pillar_count}/23)")

    # Check product name appears in content
    product_name = product_slug.replace("-", " ").title()
    if product_name.lower() not in content.lower():
        issues.append(f"Product name '{product_name}' not found in content")

    # Calculate score
    issue_count = len(issues)
    if issue_count == 0:
        score = 1.0
    elif issue_count <= 1:
        score = 0.8
    elif issue_count <= 2:
        score = 0.6
    else:
        score = 0.4

    return score, issues


# ============================================================
# MAIN VALIDATION FUNCTION
# ============================================================

def validate_spec_quality(
    content: str,
    product_slug: str,
    strict: bool = True
) -> QualityResult:
    """
    Validate tech spec quality with real content checks.

    Args:
        content: The markdown content to validate
        product_slug: The product slug (e.g., "sap-event-mesh")
        strict: If True, apply stricter grading criteria

    Returns:
        QualityResult with grade, scores, and issues
    """
    # Run all scoring functions
    authority_score, low_auth_sources = score_source_authority(content)
    relevance_score, wrong_refs = score_product_relevance(content, product_slug)
    text_score, text_artifacts = score_text_quality(content)
    coherence_score, coherence_issues = score_content_coherence(content, product_slug)

    # Calculate weighted overall score
    weights = {
        "authority": 0.25,
        "relevance": 0.35,
        "text": 0.25,
        "coherence": 0.15,
    }

    overall = (
        authority_score * weights["authority"] +
        relevance_score * weights["relevance"] +
        text_score * weights["text"] +
        coherence_score * weights["coherence"]
    )

    # Scale to 0-3
    overall_score = round(overall * 3.0, 2)

    # Collect all issues
    issues = []
    warnings = []

    # Hard failures (automatic BLOCKED)
    if len(wrong_refs) > 3:
        issues.append(f"Too many wrong product references: {len(wrong_refs)}")
    if len(text_artifacts) > 6:
        issues.append(f"Too many text artifacts: {len(text_artifacts)}")
    if authority_score < 0.3:
        issues.append(f"Source authority too low: {authority_score:.0%}")
    if relevance_score < 0.3:
        issues.append(f"Product relevance too low: {relevance_score:.0%}")

    # Warnings
    if low_auth_sources:
        warnings.append(f"Low authority sources: {', '.join(low_auth_sources[:3])}")
    if text_artifacts:
        warnings.append(f"Text artifacts detected: {len(text_artifacts)} types")

    # Determine grade
    if issues:
        grade = QualityGrade.BLOCKED
    elif overall_score >= 2.4 and relevance_score >= 0.8 and text_score >= 0.7:
        grade = QualityGrade.ELITE
    elif overall_score >= 2.0 and relevance_score >= 0.6:
        grade = QualityGrade.ACCEPTABLE
    else:
        grade = QualityGrade.BLOCKED
        issues.append("Overall quality below minimum threshold")

    return QualityResult(
        grade=grade,
        overall_score=overall_score,
        source_authority_score=authority_score,
        product_relevance_score=relevance_score,
        text_quality_score=text_score,
        content_coherence_score=coherence_score,
        issues=issues,
        warnings=warnings,
        text_artifacts=text_artifacts,
        wrong_product_refs=wrong_refs,
        low_authority_sources=low_auth_sources,
    )


# ============================================================
# CONVENIENCE FUNCTIONS FOR ORCHESTRATOR
# ============================================================

def quick_quality_check(content: str, product_slug: str) -> Tuple[bool, str]:
    """
    Quick pass/fail check for orchestrator integration.

    Returns:
        Tuple of (passed: bool, message: str)
    """
    result = validate_spec_quality(content, product_slug)

    if result.passed:
        return True, f"PASSED: {result.summary}"
    else:
        return False, f"FAILED: {result.summary} - Issues: {'; '.join(result.issues)}"


def get_quality_grade(content: str, product_slug: str) -> Tuple[str, float]:
    """
    Get grade and score for orchestrator.

    Returns:
        Tuple of (grade_string, score_float)
    """
    result = validate_spec_quality(content, product_slug)
    return result.grade.value, result.overall_score
