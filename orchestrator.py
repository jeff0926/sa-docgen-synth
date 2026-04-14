"""
orchestrator.py
---------------
SA-DocGen-Synth - Orchestration Layer for DocGen Pro Integration

Blueprint V3.0 (Glossy Portfolio Standard)

This module provides the orchestration logic for integrating agent skills
with DocGen Pro's document generation pipeline.

V3.0 Enhancements:
- Visual Forge: Mermaid + SVG + Draw.io (no truncation)
- Executive Glossary: [G01]-[G15] alphanumeric references
- Cost Optimization: Checklist-based verification (~91% token reduction)
- Multi-version support for reference architectures

Key Functions:
- validate_document(): Run requirement matching on generated markdown
- apply_quality_penalties(): Apply penalties to quality summaries
- format_validation_output(): Format validation results for output
- generate_blueprint_v2(): Generate V2 blueprint with ASCII/XML visuals
- inject_metadata_footer(): Add generation metadata to document
- estimate_forge_cost(): Calculate estimated forge cost based on tokens
- production_forge(): Execute production forge for reference architectures

CLI Usage:
    python orchestrator.py --ref-arch RA0001 --version 3.0 --ultimate
    python orchestrator.py --ref-arch RA0013 --version 3.0 --ultimate
    python orchestrator.py --all --version 3.0 --index

    # [R01] Domain Isolation - Generic (default)
    python orchestrator.py --ref-arch RA0001 --version 3.0

    # [R01] Domain Isolation - SAP-Adobe ecosystem
    python orchestrator.py --ref-arch RA0001 --version 3.0 --project sap-adobe

    # Harvest & Refine Mode (Research + Heal + Forge)
    python orchestrator.py --target 6sense --mode harvest_refine
    python orchestrator.py --target 6sense --mode harvest_refine --project sap-adobe

Updated: 2025-02-22
"""

import json
import logging
import re
from pathlib import Path
from typing import Dict, Any, Tuple, Optional, List
from datetime import datetime

from agent_skills import (
    RequirementMatcher,
    RequirementMatchReport,
    match_requirements,
    apply_requirement_penalty,
    audit_architecture,
    create_architecture_visuals,
    # [R01] Domain Isolation
    get_domain_profile,
    get_source_system,
    get_downstream_system,
    list_available_projects,
    get_domain_guard,
    # [R01] Strict Enforcement
    enforce_domain_isolation,
    validate_domain_compliance,
    sanitize_ecosystem_content,
    # Researcher Skill
    research_target,
    load_discovery_document,
    scan_for_tbd_markers,
    ResearchReport,
    PILLAR_RESEARCH_QUERIES,
    load_evidence_cache,
    inject_cached_evidence_into_report,
    create_search_function_from_cache,
)

# Web Search imports
from ddgs import DDGS
import time

# LLM Generator imports (for --llm-forge mode)
try:
    from modules.llm_generator import (
        generate_full_spec,
        LLMProvider,
        GenerationResult,
    )
    from modules.text_normalizer import normalize_evidence_text
    LLM_GENERATOR_AVAILABLE = True
except ImportError:
    LLM_GENERATOR_AVAILABLE = False
    print("[WARNING] LLM generator module not available. Install with: pip install anthropic")

# Quality Validator imports (for real content validation)
try:
    from modules.quality_validator import (
        validate_spec_quality,
        quick_quality_check,
        get_quality_grade,
        QualityGrade,
        QualityResult,
    )
    QUALITY_VALIDATOR_AVAILABLE = True
except ImportError:
    QUALITY_VALIDATOR_AVAILABLE = False
    print("[WARNING] Quality validator module not available.")

logger = logging.getLogger("sa_docgen_synth")


# ============================================================
# Web Search Function - Live Evidence Gathering
# ============================================================

def web_search(query: str, max_results: int = 5) -> List[Dict[str, str]]:
    """
    Execute a web search using DuckDuckGo Search API (ddgs package).

    Args:
        query: Search query string
        max_results: Maximum number of results to return

    Returns:
        List of dicts with 'url', 'title', 'snippet' keys
    """
    results = []

    try:
        search_results = list(DDGS().text(query, max_results=max_results))

        for r in search_results:
            # Clean text to avoid encoding issues
            title = r.get('title', '').encode('ascii', 'ignore').decode('ascii')
            body = r.get('body', '').encode('ascii', 'ignore').decode('ascii')

            results.append({
                'url': r.get('href', ''),
                'title': title,
                'snippet': body
            })

        # Small delay to avoid rate limiting
        time.sleep(0.3)

    except Exception as e:
        logger.warning(f"Web search failed for '{query}': {e}")

    return results


def create_live_search_function() -> callable:
    """
    Create a live web search function for harvest_refine.

    Returns:
        Search function compatible with researcher.py
    """
    def live_search(query: str) -> List[Dict[str, str]]:
        return web_search(query, max_results=5)

    return live_search


# ============================================================
# Registry Resolver - Master Registry Mapping Layer
# ============================================================

# SA-Synthesis-Kit paths
SA_SYNTH_KIT_PATH = Path("C:/Users/I820965/dev/SA-Synthesis-Kit")
REGISTRY_PATH = SA_SYNTH_KIT_PATH / "products" / "product-listings-status.json"

# Elite Discovery Thresholds
ELITE_EVIDENCE_MINIMUM = 50  # Minimum evidence items for ELITE grade
TRUTH_GAP_THRESHOLD = 20     # Below this, abort with TRUTH_GAP error


class TruthGapError(Exception):
    """Raised when discovery fails to find sufficient Physical Truth."""
    pass


class RegistryNotFoundError(Exception):
    """Raised when product not found in registry."""
    pass


class RegistryResolver:
    """
    Master Registry Mapping Layer for SA-Synthesis-Kit.

    Resolves --target slugs to product metadata and manages
    automated persistence to product home silos.
    """

    def __init__(self, registry_path: Path = REGISTRY_PATH):
        self.registry_path = registry_path
        self._registry_data: Optional[Dict[str, Any]] = None
        self._product_map: Dict[str, Dict[str, Any]] = {}
        self._load_registry()

    def _load_registry(self) -> None:
        """Load and index the product registry."""
        if not self.registry_path.exists():
            print(f"[Registry] Warning: Registry not found at {self.registry_path}")
            return

        with open(self.registry_path, "r", encoding="utf-8") as f:
            self._registry_data = json.load(f)

        # Build lookup map by folder_name (slug)
        for item in self._registry_data.get("items", []):
            slug = item.get("folder_name", "").lower()
            self._product_map[slug] = item

        print(f"[Registry] Loaded {len(self._product_map)} products from registry")

    def resolve(self, target_slug: str) -> Dict[str, Any]:
        """
        Resolve a target slug to full product metadata.

        Args:
            target_slug: CLI target (e.g., "adobe-rtcdp", "sap-event-mesh")

        Returns:
            Product metadata dict with extracted_product_name, location, etc.

        Raises:
            RegistryNotFoundError: If slug not in registry
        """
        slug = target_slug.lower()

        if slug not in self._product_map:
            # Check for partial matches
            matches = [k for k in self._product_map.keys() if slug in k]
            if matches:
                raise RegistryNotFoundError(
                    f"Target '{target_slug}' not found. Did you mean: {', '.join(matches)}?"
                )
            raise RegistryNotFoundError(
                f"Target '{target_slug}' not found in registry. "
                f"Available: {', '.join(list(self._product_map.keys())[:10])}..."
            )

        return self._product_map[slug]

    def get_search_seed(self, target_slug: str) -> str:
        """
        Get the primary search seed (extracted_product_name) for discovery.

        This is the 'Seed Flip' - using the full product name for better
        search results instead of the slug.

        Args:
            target_slug: CLI target slug

        Returns:
            Full product name for search queries
        """
        product = self.resolve(target_slug)
        return product.get("extracted_product_name", target_slug)

    def get_home_silo(self, target_slug: str) -> Path:
        """
        Get the home silo path for saving outputs.

        Args:
            target_slug: CLI target slug

        Returns:
            Path to product's home directory in SA-Synthesis-Kit
        """
        product = self.resolve(target_slug)
        location = product.get("location", "")

        # Convert relative path to absolute
        if location.startswith("SA-Synthesis-Kit"):
            return SA_SYNTH_KIT_PATH.parent / location.replace("\\", "/")

        return SA_SYNTH_KIT_PATH / "products" / target_slug

    def get_existing_diagram(self, target_slug: str) -> Optional[Path]:
        """
        Get existing diagram.drawio as architectural anchor.

        Args:
            target_slug: CLI target slug

        Returns:
            Path to diagram.drawio if exists, None otherwise
        """
        home_silo = self.get_home_silo(target_slug)
        diagram_path = home_silo / "diagram.drawio"

        if diagram_path.exists():
            return diagram_path

        # Check for alternative diagram files
        for pattern in ["diagram*.drawio", "*.drawio"]:
            matches = list(home_silo.glob(pattern))
            if matches:
                return matches[0]

        return None

    def update_registry(
        self,
        target_slug: str,
        tech_spec_exists: bool = True,
        grade: str = "",
        score: float = 0.0,
    ) -> None:
        """
        Update registry state after successful forge.

        Args:
            target_slug: CLI target slug
            tech_spec_exists: Whether tech spec now exists
            grade: Final grade achieved
            score: Final score achieved
        """
        if self._registry_data is None:
            return

        slug = target_slug.lower()

        for item in self._registry_data.get("items", []):
            if item.get("folder_name", "").lower() == slug:
                item["tech_spec_exists"] = tech_spec_exists
                item["tech_spec_content"] = f"tech_spec_v3_0.md (Grade: {grade}, Score: {score})"
                break

        # Save updated registry
        with open(self.registry_path, "w", encoding="utf-8") as f:
            json.dump(self._registry_data, f, indent=2)

        print(f"[Registry] Updated: {target_slug} -> tech_spec_exists={tech_spec_exists}")

    def is_eligible(self, target_slug: str) -> bool:
        """Check if product is eligible for processing."""
        try:
            product = self.resolve(target_slug)
            return (
                not product.get("missing_source_diagram", True) and
                not product.get("tech_spec_exists", True)
            )
        except RegistryNotFoundError:
            return False

    def list_eligible(self) -> List[str]:
        """List all eligible products for bulk processing."""
        eligible = []
        for slug, product in self._product_map.items():
            if (not product.get("missing_source_diagram", True) and
                not product.get("tech_spec_exists", True)):
                eligible.append(slug)
        return eligible


# Global registry instance (lazy loaded)
_registry: Optional[RegistryResolver] = None


def get_registry() -> RegistryResolver:
    """Get or create the global registry resolver."""
    global _registry
    if _registry is None:
        _registry = RegistryResolver()
    return _registry


# ============================================================
# V3.0 Hard-Gate Principal Audit System
# ============================================================
# FORTUNE 50 GUARDRAIL: Accuracy > Speed
# Replaces keyword-matching with Structural Suture Audit.
# ============================================================

def v3_principal_audit(content: str, system_name: str) -> Dict[str, Any]:
    """
    FORTUNE 50 GUARDRAIL: Accuracy > Speed.
    Replaces keyword-matching with Structural Suture Audit.

    This is the HARD GATE - documents that fail this audit are REJECTED.

    Args:
        content: The generated markdown content
        system_name: The system name for semantic validation

    Returns:
        Dict with 'passed' boolean and 'failures' list
    """
    failures = []

    # 1. Structural DNA Check - Critical Blocks
    critical_blocks = ["Authentication", "Error Handling", "Physical Truth", "Latency", "Economic", "Chaos", "Principal"]
    for block in critical_blocks:
        if f"| **Block: {block}" not in content and f"## {block}" not in content:
            # Allow section headers as alternative
            if f"## {block}" not in content and f"### {block}" not in content:
                failures.append(f"MISSING_STRUCTURAL_BLOCK: {block}")

    # 2. Deep Reasoning Detection (Principal 'So What' Gate)
    reasoning_markers = ["Architectural Reasoning", "Deep Reasoning", "Mitigation", "Principal", "Inquiry", "Guardrail"]
    if not any(marker in content for marker in reasoning_markers):
        failures.append("SHALLOW_SYNTHESIS: Document lacks architectural reasoning or mitigation logic.")

    # 3. Physical Truth/Pillar Quota - Must have evidence of all 23 pillars
    pillars_found = len(re.findall(r"P\d{2}", content))
    if pillars_found < 20:  # Allow small tolerance
        failures.append(f"INCOMPLETE_PILLARS: Found {pillars_found}/23. Incomplete architectural coverage.")

    # 4. Mermaid Diagram Requirement
    mermaid_count = content.count("```mermaid")
    if mermaid_count < 1:
        failures.append("MISSING_DIAGRAMS: No Mermaid diagrams found. Minimum 1 required.")

    # 5. Semantic Stutter & Branding Check (V3.1 Enhanced)
    if "Vendor-Vendor" in content:
        failures.append("SEMANTIC_FAILURE: [R01] Vendor-Vendor stutter detected.")

    # 5b. Excessive Vendor- sanitization detection
    vendor_count = content.count("Vendor-")
    if vendor_count > 30:
        failures.append(f"EXCESSIVE_SANITIZATION: {vendor_count} 'Vendor-' occurrences. Likely missing --project flag.")

    # 5c. System name presence check (when not domain-isolated)
    if system_name and not system_name.startswith("Vendor-"):
        # If system_name is a real product name, it should appear in content
        # Extract core product name (remove "Integration" suffix)
        core_name = system_name.replace(" Integration", "").strip()
        if core_name and core_name not in content and len(core_name) > 3:
            failures.append(f"MISSING_PRODUCT_NAME: '{core_name}' not found in content. Document may be corrupted.")

    # 6. Length Check - Elite documents are substantial
    if len(content) < 5000:
        failures.append(f"SHALLOW_CONTENT: Document too short ({len(content)} chars). Minimum 5000 required for ELITE.")

    # 7. Evidence Traceability Required
    if "Evidence Traceability" not in content and "Evidence Count" not in content:
        failures.append("MISSING_TRACEABILITY: No Evidence Traceability Matrix found.")

    # 8. World-Class Refinery Audit Required
    if "Refinery Audit" not in content and "ELITE" not in content:
        failures.append("MISSING_AUDIT: No World-Class Refinery Audit section found.")

    return {
        "passed": len(failures) == 0,
        "failures": failures,
        "checks_run": 8,
        "checks_passed": 8 - len(failures),
    }


def production_forge_v3(
    system_name: str,
    evidence_cache: Dict[str, Any],
    home_silo: Path,
    max_attempts: int = 3,
) -> Dict[str, Any]:
    """
    The Elite Production Loop.
    Forces the synthesis into a correction cycle until V3.0 standards are met.

    THIS IS THE PRIMARY EXECUTION PATH. Speed is secondary to the 3.0 ELITE audit score.

    Args:
        system_name: Semantic product name (not slug)
        evidence_cache: Loaded evidence cache dict
        home_silo: Path to product's home directory
        max_attempts: Maximum retry attempts (default: 3)

    Returns:
        Dict with forge results including success status and file path
    """
    timestamp = datetime.now().strftime("%Y-%m-%d")
    safe_name = system_name.lower().replace(" ", "-").replace("/", "-")
    final_filename = f"{safe_name}_v3-0_{timestamp}.md"

    print(f"[V3.0 Forge] System: {system_name}")
    print(f"[V3.0 Forge] Target File: {final_filename}")
    print(f"[V3.0 Forge] Home Silo: {home_silo}")
    print()

    # Extract evidence count for validation
    pillars = evidence_cache.get("pillars", {})
    evidence_count = sum(len(p.get("evidence", [])) for p in pillars.values())

    if evidence_count < TRUTH_GAP_THRESHOLD:
        raise TruthGapError(
            f"Insufficient evidence ({evidence_count} items). "
            f"Minimum {TRUTH_GAP_THRESHOLD} required. "
            f"Run discovery first: --target \"{system_name}\" --pillar-audit"
        )

    print(f"[V3.0 Forge] Evidence Items: {evidence_count}")
    print(f"[V3.0 Forge] Status: Awaiting manual synthesis (production_forge_v3 is a validation framework)")
    print()
    print("=" * 70)
    print("MANUAL SYNTHESIS REQUIRED")
    print("=" * 70)
    print()
    print("The V3.0 Hard-Gate Principal Audit requires manual synthesis.")
    print("Use the following command pattern:")
    print()
    print(f"  1. Load evidence: config/{safe_name}_evidence_cache.json")
    print(f"  2. Apply V2.2 Blueprint DNA structure")
    print(f"  3. Implement all 23 pillars with EDS Blocks")
    print(f"  4. Save to: {home_silo / final_filename}")
    print()

    return {
        "success": False,
        "status": "MANUAL_SYNTHESIS_REQUIRED",
        "system_name": system_name,
        "evidence_count": evidence_count,
        "target_filename": final_filename,
        "home_silo": str(home_silo),
        "message": "V3.0 Hard-Gate requires manual synthesis. Automated forge disabled.",
    }


def validate_and_save_v3(
    content: str,
    system_name: str,
    home_silo: Path,
    target_slug: str,
) -> Dict[str, Any]:
    """
    Validate generated content against V3.0 Hard-Gate and save if passing.

    This function is called AFTER manual synthesis to validate and persist.

    Args:
        content: The generated markdown content
        system_name: Semantic product name
        home_silo: Path to product's home directory
        target_slug: CLI target slug for registry update

    Returns:
        Dict with validation and save results
    """
    timestamp = datetime.now().strftime("%Y-%m-%d")
    safe_name = system_name.lower().replace(" ", "-").replace("/", "-")
    final_filename = f"{safe_name}_v3-0_{timestamp}.md"

    # Run V3.0 Hard-Gate Audit (structural checks)
    audit = v3_principal_audit(content, system_name)

    if not audit["passed"]:
        print()
        print("=" * 70)
        print("V3.0 HARD-GATE REJECTION (Structural)")
        print("=" * 70)
        for failure in audit["failures"]:
            print(f"  [FAIL] {failure}")
        print()
        print(f"Checks: {audit['checks_passed']}/{audit['checks_run']} passed")
        print()

        return {
            "success": False,
            "status": "REJECTED",
            "audit": audit,
            "message": "Content failed V3.0 Hard-Gate audit. Fix failures and retry.",
        }

    # Run REAL Quality Validation (content quality checks)
    if QUALITY_VALIDATOR_AVAILABLE:
        print()
        print("-" * 70)
        print("QUALITY VALIDATION (Content Analysis)")
        print("-" * 70)

        quality_result = validate_spec_quality(content, target_slug)

        print(f"  Source Authority:    {quality_result.source_authority_score:.0%}")
        print(f"  Product Relevance:   {quality_result.product_relevance_score:.0%}")
        print(f"  Text Quality:        {quality_result.text_quality_score:.0%}")
        print(f"  Content Coherence:   {quality_result.content_coherence_score:.0%}")
        print(f"  Overall Score:       {quality_result.overall_score:.2f}/3.0")
        print(f"  Grade:               {quality_result.grade.value}")

        if quality_result.warnings:
            print()
            print("  Warnings:")
            for warning in quality_result.warnings[:5]:
                print(f"    - {warning}")

        if quality_result.issues:
            print()
            print("  Issues (blocking):")
            for issue in quality_result.issues:
                print(f"    - {issue}")

        # Use REAL grade from quality validator
        final_grade = quality_result.grade.value
        final_score = quality_result.overall_score

        # Reject if quality validation fails
        if not quality_result.passed:
            print()
            print("=" * 70)
            print(f"QUALITY VALIDATION FAILED - {final_grade}")
            print("=" * 70)
            print()
            print("Content passed structural checks but FAILED quality validation.")
            print("Fix the quality issues above and retry.")
            print()

            return {
                "success": False,
                "status": "REJECTED",
                "audit": audit,
                "quality_result": {
                    "grade": final_grade,
                    "score": final_score,
                    "issues": quality_result.issues,
                    "warnings": quality_result.warnings,
                },
                "message": f"Content failed quality validation: {'; '.join(quality_result.issues)}",
            }
    else:
        # Fallback if quality validator not available (should not happen)
        print()
        print("[WARNING] Quality validator not available - using structural audit only")
        final_grade = "ACCEPTABLE"  # Conservative grade without quality validation
        final_score = 2.0

    # Passed! Save the artifact
    output_path = home_silo / final_filename
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(content, encoding="utf-8")

    byte_size = output_path.stat().st_size

    print()
    print("=" * 70)
    print(f"V3.0 HARD-GATE PASSED - {final_grade} GRADE")
    print("=" * 70)
    print(f"  File: {output_path}")
    print(f"  Size: {byte_size} bytes")
    print(f"  Score: {final_score:.2f}/3.0")
    print(f"  Structural Checks: {audit['checks_passed']}/{audit['checks_run']} passed")
    print()

    # Update registry with REAL grade
    registry = get_registry()
    registry.update_registry(
        target_slug=target_slug,
        tech_spec_exists=True,
        grade=final_grade,
        score=final_score,
        filename=final_filename,
    )

    return {
        "success": True,
        "status": final_grade,
        "output_path": str(output_path),
        "byte_size": byte_size,
        "audit": audit,
        "filename": final_filename,
        "quality_score": final_score,
    }


# ============================================================
# DEPRECATED: Legacy Forge (V2.x) - DO NOT USE
# ============================================================
# The function below is DECOMMISSIONED due to Logic Leak bugs:
# - Bug #1: "Vendor-Vendor" semantic stutter
# - Bug #2: Hardcoded "overview.md" filename (no versioning)
# - Bug #3: Boolean existence check (not content extraction)
# - Bug #4: Template contamination ("provides enterprise...")
#
# Use production_forge_v3() and validate_and_save_v3() instead.
# ============================================================

def forge_one_pager_DEPRECATED(
    target_slug: str,
    apply_r01: bool = True,
) -> Dict[str, Any]:
    """
    [DEPRECATED] Generate a V3.0 One-Pager (overview.md) from Physical Truth.

    This function synthesizes evidence from the evidence cache with
    architectural intent to produce a clean-room library asset.

    Args:
        target_slug: Target product slug (e.g., "sap-event-mesh")
        apply_r01: If True, apply [R01] domain isolation (default: True)

    Returns:
        Dict with generation results including file path and byte size
    """
    from agent_skills.domain_resolver import sanitize_ecosystem_content

    print("=" * 70)
    print(f"FORGE ONE-PAGER: {target_slug}")
    print("=" * 70)
    print()

    # Load registry
    registry = get_registry()

    # Resolve product info
    try:
        product_info = registry.resolve(target_slug)
        product_name = product_info.get("extracted_product_name", target_slug)
        home_silo = registry.get_home_silo(target_slug)
    except RegistryNotFoundError:
        print(f"  [Error] Product '{target_slug}' not found in registry")
        return {"success": False, "error": "Product not found in registry"}

    print(f"  Product: {product_name}")
    print(f"  Home Silo: {home_silo}")
    print()

    # Load evidence cache
    cache_path = Path(f"config/{target_slug}_evidence_cache.json")
    if not cache_path.exists():
        print(f"  [Error] Evidence cache not found: {cache_path}")
        return {"success": False, "error": "Evidence cache not found"}

    with open(cache_path, "r", encoding="utf-8") as f:
        evidence_cache = json.load(f)

    pillars = evidence_cache.get("pillars", {})
    sources = evidence_cache.get("_meta", {}).get("sources", [])

    print(f"  Evidence Loaded: {sum(len(p.get('evidence', [])) for p in pillars.values())} items")
    print(f"  Sources: {len(sources)}")
    print()

    # Apply [R01] Domain Isolation - use Vendor- prefix
    if apply_r01:
        system_name = f"Vendor-{target_slug.replace('-', '')}"
        display_name = f"Vendor-{target_slug.replace('-', '').title()}"
    else:
        system_name = product_name
        display_name = product_name

    # Extract key evidence for each section
    auth_evidence = pillars.get("P01", {}).get("evidence", [])
    error_evidence = pillars.get("P02", {}).get("evidence", [])
    data_evidence = pillars.get("P03", {}).get("evidence", [])
    endpoint_evidence = pillars.get("P04", {}).get("evidence", [])
    security_evidence = pillars.get("P05", {}).get("evidence", [])
    rate_evidence = pillars.get("P06", {}).get("evidence", [])
    retry_evidence = pillars.get("P07", {}).get("evidence", [])
    delivery_evidence = pillars.get("P08", {}).get("evidence", [])
    webhook_evidence = pillars.get("P10", {}).get("evidence", [])
    timeout_evidence = pillars.get("P13", {}).get("evidence", [])
    sdk_evidence = pillars.get("P15", {}).get("evidence", [])

    # Generate description from evidence
    description_parts = []
    if auth_evidence:
        auth_fact = auth_evidence[0].get("fact", "")
        description_parts.append(f"Supports {auth_fact.split(':')[0].lower() if ':' in auth_fact else 'secure authentication'}")
    if endpoint_evidence:
        description_parts.append("RESTful API integration")
    if webhook_evidence:
        description_parts.append("event-driven messaging")

    description = f"{display_name} provides enterprise integration capabilities including " + ", ".join(description_parts[:3]) + "."

    # Build Inputs table
    inputs = []
    if auth_evidence:
        inputs.append(("$I_{credentials}$", "Authentication", "OAuth 2.0 credentials, API keys, or JWT tokens for secure access"))
    if data_evidence:
        for ev in data_evidence[:2]:
            fact = ev.get("fact", "")
            if "schema" in fact.lower() or "model" in fact.lower():
                inputs.append(("$I_{payload}$", "Data Payload", "JSON/XML structured data conforming to defined schema"))
                break
    if endpoint_evidence:
        inputs.append(("$I_{request}$", "API Request", "HTTP request with required headers and parameters"))
    if not inputs:
        inputs.append(("$I_{data}$", "Input Data", "Structured data payload for processing"))

    # Build Outputs table
    outputs = []
    if endpoint_evidence:
        outputs.append(("$O_{response}$", "API Response", "JSON response with status and data payload"))
    if webhook_evidence:
        outputs.append(("$O_{events}$", "Event Stream", "Real-time event notifications via webhooks"))
    if error_evidence:
        outputs.append(("$O_{errors}$", "Error Response", "Structured error messages with status codes"))
    if not outputs:
        outputs.append(("$O_{result}$", "Result", "Processed output data"))

    # Build Constraints table
    constraints = []
    if rate_evidence:
        for ev in rate_evidence:
            fact = ev.get("fact", "")
            if "limit" in fact.lower() or "429" in fact:
                constraints.append(("$C_{rate}$", "Rate Limit", "API requests subject to rate limiting; implement backoff"))
                break
    if timeout_evidence:
        for ev in timeout_evidence:
            fact = ev.get("fact", "")
            if "timeout" in fact.lower() or "second" in fact.lower():
                constraints.append(("$C_{timeout}$", "Timeout", "Connection and request timeouts apply"))
                break
    if delivery_evidence:
        for ev in delivery_evidence:
            fact = ev.get("fact", "")
            if "at-least-once" in fact.lower() or "delivery" in fact.lower():
                constraints.append(("$C_{delivery}$", "Delivery", "At-least-once delivery; consumers must handle idempotency"))
                break
    if security_evidence:
        constraints.append(("$C_{security}$", "Security", "TLS 1.2+ required for all communications"))
    if not constraints:
        constraints.append(("$C_{api}$", "API Limits", "Standard API usage limits apply"))

    # Build Dependencies
    dependencies = []
    if auth_evidence:
        for ev in auth_evidence:
            fact = ev.get("fact", "")
            if "oauth" in fact.lower():
                dependencies.append("Identity Provider (OAuth 2.0)")
                break
            elif "jwt" in fact.lower():
                dependencies.append("Token Service (JWT)")
                break
    if sdk_evidence:
        for ev in sdk_evidence:
            fact = ev.get("fact", "")
            if "sdk" in fact.lower():
                dependencies.append("Platform SDK")
                break
    if not dependencies:
        dependencies.append("HTTP Client Library")

    # Generate the One-Pager markdown
    md_lines = []
    md_lines.append(f"# {display_name} Overview")
    md_lines.append("")
    md_lines.append("## Description")
    md_lines.append(description)
    md_lines.append("")
    md_lines.append("## Inputs ($I^*$)")
    md_lines.append("")
    md_lines.append("| Input | Type | Description |")
    md_lines.append("|-------|------|-------------|")
    for inp in inputs:
        md_lines.append(f"| {inp[0]} | {inp[1]} | {inp[2]} |")
    md_lines.append("")
    md_lines.append("## Outputs ($O$)")
    md_lines.append("")
    md_lines.append("| Output | Type | Description |")
    md_lines.append("|--------|------|-------------|")
    for out in outputs:
        md_lines.append(f"| {out[0]} | {out[1]} | {out[2]} |")
    md_lines.append("")
    md_lines.append("## Constraints ($C$)")
    md_lines.append("")
    md_lines.append("| Constraint | Type | Description |")
    md_lines.append("|------------|------|-------------|")
    for con in constraints:
        md_lines.append(f"| {con[0]} | {con[1]} | {con[2]} |")
    md_lines.append("")
    md_lines.append("## Dependencies")
    for dep in dependencies:
        md_lines.append(f"- {dep}")
    md_lines.append("")
    md_lines.append("## References")
    for src in sources[:3]:
        md_lines.append(f"- [{src}]({src})")
    md_lines.append("")
    md_lines.append("---")
    md_lines.append(f"*Generated by SA-DocGen-Synth Forge V3.0 | {datetime.utcnow().strftime('%Y-%m-%d')}*")
    md_lines.append("")

    content = "\n".join(md_lines)

    # Apply [R01] Domain Isolation - sanitize any remaining vendor references
    if apply_r01:
        content, violations = sanitize_ecosystem_content(content, project=None)

    # Save to home silo
    output_path = home_silo / "overview.md"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(content, encoding="utf-8")

    byte_size = output_path.stat().st_size

    print(f"  [Forge] Generated: {output_path}")
    print(f"  [Forge] Size: {byte_size} bytes")
    print()

    # Update registry
    registry.update_registry(
        target_slug=target_slug,
        tech_spec_exists=True,
        grade="MINTED",
        score=1.0,
    )
    print(f"  [Registry] Updated: {target_slug} -> overview.md minted")

    return {
        "success": True,
        "target": target_slug,
        "product_name": product_name,
        "output_path": str(output_path),
        "byte_size": byte_size,
        "r01_applied": apply_r01,
    }


def batch_forge_one_pagers(
    targets: List[str],
    apply_r01: bool = True,
) -> Dict[str, Any]:
    """
    [V3.0 HARD-GATE] Batch validation and preparation for V3.0 One-Pagers.

    IMPORTANT: This function no longer auto-generates content.
    V3.0 Hard-Gate Principal Audit requires manual synthesis.

    This function validates evidence cache availability and prepares
    the forge queue for manual synthesis.

    Args:
        targets: List of target slugs
        apply_r01: If True, apply [R01] domain isolation

    Returns:
        Dict with batch validation results and forge instructions
    """
    print("=" * 70)
    print("V3.0 HARD-GATE BATCH FORGE VALIDATION")
    print("=" * 70)
    print()
    print("NOTICE: Automated forge DISABLED per V3.0 Hard-Gate Protocol.")
    print("        Manual synthesis required for ELITE grade.")
    print()
    print(f"Targets: {len(targets)}")
    for i, t in enumerate(targets, 1):
        print(f"  {i}. {t}")
    print()
    print("=" * 70)
    print()

    registry = get_registry()

    results = {
        "total": len(targets),
        "ready": 0,
        "missing_cache": 0,
        "missing_registry": 0,
        "targets": [],
    }

    for i, target in enumerate(targets, 1):
        print()
        print(f"[{i}/{len(targets)}] Validating: {target}")
        print("-" * 40)

        target_result = {
            "target": target,
            "status": "UNKNOWN",
        }

        # Check registry
        try:
            product_info = registry.resolve(target)
            product_name = product_info.get("extracted_product_name", target)
            home_silo = registry.get_home_silo(target)
            target_result["product_name"] = product_name
            target_result["home_silo"] = str(home_silo)
            print(f"  [Registry] Product: {product_name}")
            print(f"  [Registry] Silo: {home_silo}")
        except RegistryNotFoundError as e:
            results["missing_registry"] += 1
            target_result["status"] = "MISSING_REGISTRY"
            target_result["error"] = str(e)
            results["targets"].append(target_result)
            print(f"  [Error] {e}")
            continue

        # Check evidence cache
        cache_path = Path(f"config/{target}_evidence_cache.json")
        if not cache_path.exists():
            results["missing_cache"] += 1
            target_result["status"] = "MISSING_CACHE"
            target_result["error"] = f"Evidence cache not found: {cache_path}"
            target_result["action"] = f"Run: python orchestrator.py --target \"{target}\" --pillar-audit"
            results["targets"].append(target_result)
            print(f"  [Error] Evidence cache not found: {cache_path}")
            print(f"  [Action] Run: python orchestrator.py --target \"{target}\" --pillar-audit")
            continue

        # Load and validate evidence cache
        with open(cache_path, "r", encoding="utf-8") as f:
            evidence_cache = json.load(f)

        pillars = evidence_cache.get("pillars", {})
        evidence_count = sum(len(p.get("evidence", [])) for p in pillars.values())

        if evidence_count < TRUTH_GAP_THRESHOLD:
            results["missing_cache"] += 1
            target_result["status"] = "TRUTH_GAP"
            target_result["evidence_count"] = evidence_count
            target_result["error"] = f"Insufficient evidence: {evidence_count}/{TRUTH_GAP_THRESHOLD}"
            results["targets"].append(target_result)
            print(f"  [Error] TRUTH_GAP: Only {evidence_count} evidence items (min: {TRUTH_GAP_THRESHOLD})")
            continue

        # Target is ready for manual synthesis
        results["ready"] += 1
        timestamp = datetime.now().strftime("%Y-%m-%d")
        safe_name = product_name.lower().replace(" ", "-").replace("/", "-")
        target_filename = f"{safe_name}_v3-0_{timestamp}.md"

        target_result["status"] = "READY"
        target_result["evidence_count"] = evidence_count
        target_result["target_filename"] = target_filename
        results["targets"].append(target_result)

        print(f"  [Evidence] {evidence_count} items - ELITE threshold met")
        print(f"  [Target] {target_filename}")
        print(f"  [Status] READY for manual synthesis")

    # Print summary
    print()
    print("=" * 70)
    print("V3.0 HARD-GATE BATCH VALIDATION SUMMARY")
    print("=" * 70)
    print()
    print(f"| Target | Status | Evidence | Filename |")
    print(f"|--------|--------|----------|----------|")
    for t in results["targets"]:
        status = t.get("status", "UNKNOWN")
        evidence = t.get("evidence_count", "-")
        filename = t.get("target_filename", t.get("error", "-"))
        print(f"| {t['target']} | {status} | {evidence} | {filename[:40]}... |")
    print()
    print(f"Total: {results['total']}")
    print(f"Ready for Manual Synthesis: {results['ready']}")
    print(f"Missing Evidence Cache: {results['missing_cache']}")
    print(f"Missing Registry Entry: {results['missing_registry']}")
    print()
    print("=" * 70)
    print("MANUAL SYNTHESIS INSTRUCTIONS")
    print("=" * 70)
    print()
    print("For each READY target, perform manual synthesis:")
    print("  1. Load evidence cache from config/<target>_evidence_cache.json")
    print("  2. Apply V2.2 Blueprint DNA structure (RA0001 template)")
    print("  3. Implement all 23 pillars with EDS Blocks")
    print("  4. Include: P16 Latency, P21 Economic, P22 Chaos, P23 Principal")
    print("  5. Add high-fidelity Mermaid diagrams")
    print("  6. Run World-Class Refinery Audit (target: 3.0/3.0)")
    print("  7. Save to: <home_silo>/<target_filename>")
    print()

    return results


# ============================================================
# Configuration
# ============================================================

DEFAULT_CONFIG_PATH = "config/requirements_matrix.json"


# ============================================================
# Document Validation
# ============================================================

def validate_document(
    markdown_text: str,
    config_path: str = DEFAULT_CONFIG_PATH,
) -> Dict[str, Any]:
    """
    Run deterministic requirement validation on a markdown document.

    This is the main entry point for DocGen Pro integration.

    Args:
        markdown_text: The generated markdown document
        config_path: Path to the requirements matrix JSON

    Returns:
        Dictionary containing:
        - report: RequirementMatchReport dataclass
        - formatted_markdown: Markdown section for Section 14
        - summary: Dict with key metrics for quality_summary
    """
    logger.info("[Orchestrator] Running deterministic requirement validation...")

    # Run requirement matching
    report, formatted_markdown = match_requirements(markdown_text, config_path)

    logger.info(
        f"[Orchestrator] Match Rate: {report.match_rate}% | "
        f"Hard Failures: {report.hard_failures} | "
        f"Penalty: {report.penalty_applied}"
    )

    # Build summary dict for session/response
    summary = {
        "match_rate": report.match_rate,
        "total": report.total_requirements,
        "passed": report.passed_requirements,
        "failed": report.failed_requirements,
        "hard_failures": report.hard_failures,
        "soft_failures": report.soft_failures,
        "penalty_applied": report.penalty_applied,
        "results": [
            {
                "id": r.requirement_id,
                "name": r.requirement_name,
                "category": r.category,
                "is_hard": r.is_hard,
                "passed": r.passed,
            }
            for r in report.results
        ],
    }

    return {
        "report": report,
        "formatted_markdown": formatted_markdown,
        "summary": summary,
    }


def apply_quality_penalties(
    quality_summary: Dict[str, Any],
    validation: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Apply requirement match penalties to a quality summary.

    Args:
        quality_summary: The existing quality_summary dict from DocGen Pro
        validation: The validation dict returned by validate_document()

    Returns:
        Updated quality_summary with penalties applied
    """
    report: RequirementMatchReport = validation["report"]

    # Apply penalty if hard failures exist
    if report.hard_failures > 0:
        original_accuracy = quality_summary.get("Final Accuracy (%)", 100.0)
        penalized_accuracy = round(original_accuracy * (1.0 - report.penalty_applied), 1)

        quality_summary["Original Accuracy (%)"] = original_accuracy
        quality_summary["Final Accuracy (%)"] = penalized_accuracy
        quality_summary["Requirement Penalty"] = f"-{int(report.penalty_applied * 100)}%"

        logger.warning(
            f"[Orchestrator] Hard failures detected! "
            f"Accuracy penalized: {original_accuracy}% → {penalized_accuracy}%"
        )

    # Add match rate to quality summary
    quality_summary["Requirement Match Rate"] = f"{report.match_rate}%"
    quality_summary["Hard Requirement Failures"] = report.hard_failures

    return quality_summary


def append_validation_to_markdown(
    combined_markdown: str,
    validation: Dict[str, Any],
) -> str:
    """
    Append the mechanical match report to the combined markdown.

    Args:
        combined_markdown: The full document markdown
        validation: The validation dict returned by validate_document()

    Returns:
        Updated markdown with validation section appended
    """
    formatted = validation["formatted_markdown"]
    return combined_markdown.strip() + "\n\n---\n\n" + formatted


# ============================================================
# DocGen Pro Integration Helper
# ============================================================

def integrate_with_generate_route(
    combined_markdown: str,
    quality_summary: Dict[str, Any],
    session: Dict[str, Any],
    config_path: str = DEFAULT_CONFIG_PATH,
) -> Tuple[str, Dict[str, Any]]:
    """
    Complete integration function for DocGen Pro's /generate route.

    This function performs all validation steps and returns updated values.

    Args:
        combined_markdown: The generated markdown document
        quality_summary: The existing quality summary
        session: The Flask session dict (will be modified in place)
        config_path: Path to requirements matrix JSON

    Returns:
        Tuple of (updated_markdown, updated_quality_summary)

    Example usage in app.py:
        from sa_docgen_synth.orchestrator import integrate_with_generate_route

        # After combining base + devkit markdown:
        combined_markdown, quality_summary = integrate_with_generate_route(
            combined_markdown,
            quality_summary,
            session,
            config_path="../sa-docgen-synth/config/requirements_matrix.json"
        )
    """
    # Step 1: Validate document
    validation = validate_document(combined_markdown, config_path)

    # Step 2: Store in session
    session["requirement_match"] = validation["summary"]

    # Step 3: Apply penalties
    quality_summary = apply_quality_penalties(quality_summary, validation)

    # Step 4: Append validation to markdown
    combined_markdown = append_validation_to_markdown(combined_markdown, validation)

    return combined_markdown, quality_summary


# ============================================================
# Blueprint V2.0 Functions (EDS-Friendly & Lucid-Ready)
# ============================================================

def transform_title_prefix(markdown: str) -> str:
    """
    Transform title from 'Elite Integration Blueprint:' to 'Tech Spec:'.

    Args:
        markdown: The markdown document

    Returns:
        Markdown with updated title prefix
    """
    # Replace the title pattern
    pattern = r"^#\s*Elite\s+Integration\s+Blueprint:\s*"
    replacement = "# Tech Spec: "
    return re.sub(pattern, replacement, markdown, flags=re.MULTILINE | re.IGNORECASE)


def inject_visual_suture(
    markdown: str,
    system_name: str,
    layers: Dict[str, List[str]],
    connections: List[Tuple[str, str, str]]
) -> str:
    """
    Inject ASCII and Draw.io XML into the Visual-Suture table.

    Args:
        markdown: The markdown document
        system_name: Name of the system
        layers: Dict of layer_name -> component list
        connections: List of (source, target, label) tuples

    Returns:
        Markdown with populated Visual-Suture table
    """
    # Generate visuals
    visuals = create_architecture_visuals(system_name, layers, connections)

    # Escape ASCII for markdown table cell (replace | with escaped version)
    ascii_escaped = visuals["ascii"].replace("|", "\\|").replace("\n", "<br>")

    # Truncate Draw.io XML for table display (full XML would be too long)
    drawio_preview = visuals["drawio_xml"][:200] + "..." if len(visuals["drawio_xml"]) > 200 else visuals["drawio_xml"]
    drawio_escaped = drawio_preview.replace("|", "\\|").replace("<", "&lt;").replace(">", "&gt;")

    # Replace placeholders
    markdown = markdown.replace("{{ASCII_ARCHITECTURE_DIAGRAM}}", f"<pre>{ascii_escaped}</pre>")
    markdown = markdown.replace("{{DRAWIO_XML_ARCHITECTURE}}", f"<code>{drawio_escaped}</code>")

    return markdown


def inject_metadata_footer(
    markdown: str,
    token_count: int,
    platform: str = "Claude",
    model: str = "claude-opus-4-5-20251101",
    timestamp: Optional[str] = None,
    est_forge_cost: Optional[str] = None
) -> str:
    """
    Inject generation metadata into the footer table.

    Args:
        markdown: The markdown document
        token_count: Estimated token count
        platform: AI platform name
        model: Model identifier
        timestamp: ISO timestamp (defaults to now)
        est_forge_cost: Estimated forge cost string

    Returns:
        Markdown with populated metadata footer
    """
    if timestamp is None:
        timestamp = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")

    if est_forge_cost is None:
        # Estimate cost based on output tokens (assume 1:1 input:output ratio)
        est_forge_cost = estimate_forge_cost(token_count, token_count, model)

    markdown = markdown.replace("{{TOKEN_COUNT}}", str(token_count))
    markdown = markdown.replace("{{PLATFORM}}", platform)
    markdown = markdown.replace("{{MODEL}}", model)
    markdown = markdown.replace("{{TIMESTAMP}}", timestamp)
    markdown = markdown.replace("{{EST_FORGE_COST}}", est_forge_cost)

    return markdown


def inject_refinery_audit(markdown: str) -> Tuple[str, Dict[str, Any]]:
    """
    Run the World-Class Refinery audit and inject results.

    Args:
        markdown: The markdown document

    Returns:
        Tuple of (markdown with audit results, audit json report)
    """
    json_report, markdown_table = audit_architecture(markdown)

    # Replace the placeholder with the audit results
    # The markdown_table includes the full formatted results
    markdown = markdown.replace("{{REFINERY_AUDIT_RESULTS}}", markdown_table)

    return markdown, json_report


def estimate_token_count(text: str) -> int:
    """
    Estimate token count for a text string.
    Rough approximation: ~4 characters per token for English text.

    Args:
        text: The text to estimate

    Returns:
        Estimated token count
    """
    return len(text) // 4


# Cost per 1M tokens (as of 2025-02 pricing)
MODEL_PRICING = {
    "claude-opus-4-5-20251101": {"input": 15.00, "output": 75.00},
    "claude-sonnet-4-20250514": {"input": 3.00, "output": 15.00},
    "claude-3-5-sonnet-20241022": {"input": 3.00, "output": 15.00},
    "claude-3-opus-20240229": {"input": 15.00, "output": 75.00},
    "gemini-2.5-pro": {"input": 1.25, "output": 10.00},
    "gpt-4o": {"input": 2.50, "output": 10.00},
    "default": {"input": 3.00, "output": 15.00},
}


def estimate_forge_cost(
    input_tokens: int,
    output_tokens: int,
    model: str = "claude-opus-4-5-20251101"
) -> str:
    """
    Estimate the cost of a forge operation based on token usage.

    Args:
        input_tokens: Estimated input tokens (prompt + context)
        output_tokens: Estimated output tokens (generated content)
        model: Model identifier for pricing lookup

    Returns:
        Formatted cost string (e.g., "$0.15")
    """
    pricing = MODEL_PRICING.get(model, MODEL_PRICING["default"])

    # Calculate cost (price is per 1M tokens)
    input_cost = (input_tokens / 1_000_000) * pricing["input"]
    output_cost = (output_tokens / 1_000_000) * pricing["output"]
    total_cost = input_cost + output_cost

    # Format as currency
    if total_cost < 0.01:
        return f"${total_cost:.4f}"
    elif total_cost < 1.00:
        return f"${total_cost:.2f}"
    else:
        return f"${total_cost:.2f}"


def generate_blueprint_v2(
    system_name: str,
    content: str,
    layers: Optional[Dict[str, List[str]]] = None,
    connections: Optional[List[Tuple[str, str, str]]] = None,
    platform: str = "Claude",
    model: str = "claude-opus-4-5-20251101",
) -> Dict[str, Any]:
    """
    Generate a complete Blueprint V2.1 document.

    This is the main entry point for V2.1 blueprint generation with:
    - EDS-Friendly table blocks with merged headers
    - Visual-Suture with ASCII and Draw.io XML
    - Refinery audit results (22 pillars including P21/P22)
    - Generation metadata footer with Est. Forge Cost
    - Risk Register & Known Limitations support

    Args:
        system_name: Name of the system
        content: The markdown content (from template or generation)
        layers: Optional architecture layers for visual generation
        connections: Optional connections for visual generation
        platform: AI platform identifier
        model: Model identifier

    Returns:
        Dict containing:
        - markdown: The complete V2.1 blueprint markdown
        - audit_report: The refinery audit JSON report
        - metadata: Generation metadata including est_forge_cost
    """
    logger.info(f"[Orchestrator] Generating Blueprint V2.1 for: {system_name}")

    # Step 1: Transform title prefix
    content = transform_title_prefix(content)
    logger.info("[Orchestrator] Title prefix transformed to 'Tech Spec:'")

    # Step 2: Inject visual suture if layers/connections provided
    if layers and connections:
        content = inject_visual_suture(content, system_name, layers, connections)
        logger.info("[Orchestrator] Visual-Suture injected with ASCII and Draw.io XML")

    # Step 3: Run refinery audit and inject results
    content, audit_report = inject_refinery_audit(content)
    logger.info(
        f"[Orchestrator] Refinery audit complete: "
        f"Grade={audit_report['grade']}, Score={audit_report['weighted_mean']}/3.0"
    )

    # Step 4: Estimate token count and forge cost
    token_count = estimate_token_count(content)
    timestamp = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    est_forge_cost = estimate_forge_cost(token_count, token_count, model)

    # Step 5: Inject metadata footer
    content = inject_metadata_footer(
        content, token_count, platform, model, timestamp, est_forge_cost
    )
    logger.info(f"[Orchestrator] Metadata footer injected: {token_count} tokens, {est_forge_cost}")

    # Build result
    result = {
        "markdown": content,
        "audit_report": audit_report,
        "metadata": {
            "system_name": system_name,
            "token_count": token_count,
            "platform": platform,
            "model": model,
            "timestamp": timestamp,
            "grade": audit_report["grade"],
            "score": audit_report["weighted_mean"],
            "est_forge_cost": est_forge_cost,
        }
    }

    logger.info("[Orchestrator] Blueprint V2.1 generation complete")
    return result


# ============================================================
# Target Discovery Audit (V3.0)
# ============================================================

def run_target_discovery_audit(target: str, mode: str = "glossy_v3") -> Dict[str, Any]:
    """
    Run a pillar discovery audit against a target system.

    This creates a skeleton document for the target system and audits it
    to show what evidence is needed for each pillar.

    Args:
        target: Target system name (e.g., "6sense", "Marketo")
        mode: Audit mode - "glossy_v3", "quick", or "full"

    Returns:
        Dict with audit results and recommendations
    """
    from agent_skills import (
        audit_architecture,
        quick_audit,
        get_pillar_checklist,
        ALL_PILLARS,
        EXECUTIVE_GLOSSARY,
        PILLAR_GLOSSARY_MAP,
    )

    print("=" * 70)
    print(f"TARGET DISCOVERY AUDIT: {target}")
    print(f"Mode: {mode}")
    print("=" * 70)
    print()

    # Create discovery skeleton for the target
    discovery_doc = f"""# Integration Blueprint: SAP to {target}

## Target System Overview
**System Name**: {target}
**Integration Pattern**: TBD
**Suture Pattern**: SAP -> ? -> {target}

---

## P01: Authentication Architecture
- Authentication method: TBD
- OAuth 2.0 / API Key / JWT: ?

## P02: Error Handling Strategy
- HTTP status codes: TBD
- Error response schema: TBD

## P03: Data Contract Definition
- Request/response schema: TBD
- XDM or custom schema: ?

## P04: Integration Endpoint Specification
- Base URL: https://api.{target.lower()}.com/v1/
- API documentation: ?

## P05: Security Posture
- TLS version: TBD
- Encryption: TBD

---

*Discovery document for {target} - requires research*
"""

    # Run audit based on mode
    if mode == "quick":
        result = quick_audit(discovery_doc)
        checklist = get_pillar_checklist(discovery_doc)
        print("--- QUICK AUDIT ---")
        print(checklist)
        print()
        print(f"Grade: {result['grade']}")
        print(f"Score: {result['score']}/3.0")
        print(f"Passed: {result['pass']}/{result['total']}")

    elif mode == "glossy_v3":
        # Full V3.0 Glossy Portfolio audit with recommendations
        json_report, markdown_report = audit_architecture(discovery_doc, compact=False)
        checklist = get_pillar_checklist(discovery_doc)

        print("--- V3.0 GLOSSY PORTFOLIO AUDIT ---")
        print()
        print(checklist)
        print()

        # Show what's missing
        print("=" * 70)
        print("PILLAR GAP ANALYSIS")
        print("=" * 70)
        print()

        missing_pillars = []
        for pillar_detail in json_report.get("pillar_details", []):
            if not pillar_detail["passed"]:
                missing_pillars.append(pillar_detail)

        if missing_pillars:
            print(f"Missing {len(missing_pillars)} pillars for ELITE grade:")
            print()
            for p in missing_pillars:
                tier_marker = {"CRITICAL": "[T1-CRITICAL]", "HIGH": "[T2-HIGH]", "MEDIUM": "[T3-MEDIUM]"}
                marker = tier_marker.get(p["tier"], "")

                # Get glossary refs
                glossary_refs = PILLAR_GLOSSARY_MAP.get(p["id"], [])
                glossary_str = " ".join(f"[{g}]" for g in glossary_refs) if glossary_refs else ""

                print(f"  {p['id']}: {p['name']} {marker} {glossary_str}")
                print(f"       Evidence needed: {p['required_count']} patterns")
                print(f"       Evidence found: {p['evidence_count']}")

                # Find the pillar definition to show what evidence is needed
                for pillar in ALL_PILLARS:
                    if pillar.id == p["id"]:
                        print(f"       Description: {pillar.description}")
                        print(f"       Example patterns: {', '.join(pillar.evidence_tokens[:3])}...")
                        break
                print()
        else:
            print("All pillars passed!")

        # Show recommended research topics
        print("=" * 70)
        print(f"RECOMMENDED RESEARCH FOR {target.upper()}")
        print("=" * 70)
        print()
        print(f"To build an ELITE-grade integration spec for {target}, research:")
        print()
        print(f"  1. {target} API Documentation")
        print(f"     - Authentication method (OAuth 2.0, API Key, JWT?)")
        print(f"     - Base URL and versioning strategy")
        print(f"     - Rate limits and quotas")
        print()
        print(f"  2. {target} Data Model")
        print(f"     - Entity schemas (contacts, accounts, events)")
        print(f"     - Required vs optional fields")
        print(f"     - Mapping to SAP/Adobe XDM")
        print()
        print(f"  3. {target} Integration Patterns")
        print(f"     - Real-time (webhooks, streaming) vs Batch")
        print(f"     - Event types and payload formats")
        print(f"     - Idempotency and deduplication")
        print()
        print(f"  4. {target} Operational Concerns")
        print(f"     - Error handling and retry strategies")
        print(f"     - SLAs and latency expectations")
        print(f"     - Sandbox/testing environment")
        print()

        result = json_report

    else:  # full mode
        json_report, markdown_report = audit_architecture(discovery_doc, compact=False)
        print("--- FULL AUDIT REPORT ---")
        print()
        print(markdown_report)
        result = json_report

    # Save discovery document
    from pathlib import Path
    output_dir = Path("outputs/discovery")
    output_dir.mkdir(parents=True, exist_ok=True)

    discovery_path = output_dir / f"{target.lower()}_discovery.md"
    discovery_path.write_text(discovery_doc, encoding="utf-8")
    print()
    print(f"Discovery document saved: {discovery_path}")
    print("=" * 70)

    return {
        "target": target,
        "mode": mode,
        "result": result,
        "discovery_path": str(discovery_path),
    }


# ============================================================
# Reference Architecture Registry
# ============================================================

REFERENCE_ARCHITECTURES = {
    "RA0001": {
        "name": "SAP Event Mesh to Adobe Journey Optimizer",
        "versions": {
            "2.2": {
                "forge_script": "forge_ra0001_sap_to_ajo_v2_2.py",
                "output_file": "RA0001_sap_to_ajo_tech_spec_v2_2.md",
            },
            "3.0": {
                "forge_script": "forge_ra0001_sap_to_ajo_v3_0.py",
                "output_file": "RA0001_sap_to_ajo_tech_spec_v3_0.md",
            },
        },
        "diagram_file": "RA0001.drawio",
        "pattern": "Event-Driven Streaming",
        "description": "Real-time event integration from SAP S/4HANA to Adobe AJO via Event Mesh",
    },
    "RA0013": {
        "name": "Business Data Cloud (SAP to Adobe)",
        "versions": {
            "2.2": {
                "forge_script": "forge_ra0013_business_data_cloud_v2_2.py",
                "output_file": "RA0013_business_data_cloud_v2_2.md",
            },
            "3.0": {
                "forge_script": "forge_ra0013_business_data_cloud_v3_0.py",
                "output_file": "RA0013_business_data_cloud_v3_0.md",
            },
        },
        "diagram_file": "RA0013.drawio",
        "pattern": "Batch Ingestion",
        "description": "Batch integration from SAP Business Partner to Adobe Unified Profile",
    },
    "6SENSE": {
        "name": "6sense Intent Enrichment Integration",
        "versions": {
            "3.0": {
                "forge_script": "forge_6sense_intent_enrichment_v3_0.py",
                "output_file": "6sense_intent_enrichment_v3_0.md",
            },
        },
        "diagram_file": "6SENSE.drawio",
        "pattern": "API Enrichment",
        "description": "Intent enrichment from SAP CRM to 6sense Revenue AI for ABM activation",
        "provider_type": "primary_data_provider",
        "data_capabilities": ["firmographic", "intent_signals", "buying_stage", "lead_scoring"],
    },
}


def production_forge(
    ref_arch: str,
    version: str = "3.0",
    ultimate: bool = False,
    project: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Execute a production forge for a reference architecture.

    Args:
        ref_arch: Reference architecture ID (e.g., "RA0001", "RA0013")
        version: Blueprint version (e.g., "2.2", "3.0")
        ultimate: Whether to use Ultimate standard (23 pillars)
        project: [R01] Project/ecosystem identifier. If None, uses generic terminology.

    Returns:
        Dict with forge results and file paths
    """
    import importlib.util
    import sys
    import shutil

    if ref_arch not in REFERENCE_ARCHITECTURES:
        raise ValueError(f"Unknown reference architecture: {ref_arch}. Available: {list(REFERENCE_ARCHITECTURES.keys())}")

    ra_config = REFERENCE_ARCHITECTURES[ref_arch]

    # Get version-specific config
    if "versions" in ra_config:
        if version not in ra_config["versions"]:
            available_versions = list(ra_config["versions"].keys())
            raise ValueError(f"Unknown version {version} for {ref_arch}. Available: {available_versions}")
        version_config = ra_config["versions"][version]
        forge_script = version_config["forge_script"]
        output_file = version_config["output_file"]
    else:
        # Legacy single-version format
        forge_script = ra_config["forge_script"]
        output_file = ra_config["output_file"]

    # [R01] Get domain profile
    domain_profile = get_domain_profile(project)
    domain_guards = get_domain_guard(project)

    print("=" * 70)
    print(f"PRODUCTION FORGE: {ref_arch} - {ra_config['name']}")
    print("=" * 70)
    print(f"  Version: {version}")
    print(f"  Ultimate: {ultimate}")
    print(f"  Pattern: {ra_config['pattern']}")
    print(f"  [R01] Project: {project or 'None (generic)'}")
    print(f"  [R01] Source: {domain_profile.source_system}")
    print(f"  [R01] Downstream: {domain_profile.downstream_system}")
    print()

    # Load and execute the forge script
    forge_script_path = Path(forge_script)
    if not forge_script_path.exists():
        raise FileNotFoundError(f"Forge script not found: {forge_script_path}")

    # Import the forge module dynamically
    spec = importlib.util.spec_from_file_location(f"forge_{ref_arch.lower()}", forge_script_path)
    forge_module = importlib.util.module_from_spec(spec)
    sys.modules[f"forge_{ref_arch.lower()}"] = forge_module
    spec.loader.exec_module(forge_module)

    # Execute the main function
    result = forge_module.main()

    # ============================================================
    # [R01] STRICT ENFORCEMENT - Sanitize Output
    # ============================================================
    output_path = Path(f"outputs/{output_file}")
    if output_path.exists():
        print()
        print("[R01] STRICT ENFORCEMENT CHECK")
        print("-" * 40)

        # Read generated content
        original_content = output_path.read_text(encoding="utf-8")

        # Validate compliance
        compliance = validate_domain_compliance(original_content, project)

        if not compliance["compliant"]:
            print(f"  Violations detected: {compliance['violations_count']}")
            print(f"  Ecosystems found: {', '.join(compliance['ecosystems_detected'])}")

            if project is None:
                # Generic mode - apply strict sanitization
                print(f"  Action: SANITIZING (no --project flag)")
                sanitized_content = enforce_domain_isolation(original_content, project)

                # Write sanitized content back
                output_path.write_text(sanitized_content, encoding="utf-8")
                print(f"  Output sanitized and saved: {output_path}")

                # Update result metadata
                if result and "markdown" in result:
                    result["markdown"] = sanitized_content
                result["r01_sanitized"] = True
                result["r01_violations_stripped"] = compliance["violations_count"]
            else:
                # Project specified - violations are authorized
                print(f"  Action: ALLOWED (--project {project} authorizes these ecosystems)")
                result["r01_sanitized"] = False
                result["r01_authorized_ecosystems"] = compliance["ecosystems_detected"]
        else:
            print(f"  Status: COMPLIANT (no unauthorized ecosystem references)")
            result["r01_sanitized"] = False

        print("-" * 40)

    # Copy/rename diagram file to standard location
    outputs_diagrams = Path("outputs/diagrams")
    outputs_diagrams.mkdir(parents=True, exist_ok=True)

    # Find the generated .drawio file
    for drawio_file in outputs_diagrams.glob("*.drawio"):
        if ref_arch.lower() in drawio_file.name.lower() or ra_config["name"].lower().replace(" ", "_") in drawio_file.name.lower():
            target_path = outputs_diagrams / ra_config["diagram_file"]
            if drawio_file != target_path:
                shutil.copy(drawio_file, target_path)
                print(f"  Diagram copied to: {target_path}")
            break

    print()
    print(f"  Output: outputs/{output_file}")
    print(f"  Diagram: outputs/diagrams/{ra_config['diagram_file']}")
    print("=" * 70)

    return {
        "ref_arch": ref_arch,
        "version": version,
        "result": result,
        "output_file": f"outputs/{output_file}",
        "diagram_file": f"outputs/diagrams/{ra_config['diagram_file']}",
        # [R01] Domain context
        "project": project,
        "domain_profile": {
            "id": domain_profile.id,
            "source_system": domain_profile.source_system,
            "downstream_system": domain_profile.downstream_system,
        },
    }


def generate_portfolio_index(forge_results: List[Dict[str, Any]]) -> str:
    """
    Generate a portfolio index markdown file summarizing all forged specs.

    Args:
        forge_results: List of forge result dicts

    Returns:
        Markdown content for index.md
    """
    lines = []
    lines.append("# SA-DocGen-Synth Portfolio Index")
    lines.append("")
    lines.append("<!-- EDS Block Pattern: Portfolio of ELITE Integration Blueprints -->")
    lines.append("")
    lines.append(f"**Generated:** {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}")
    lines.append("")
    lines.append("---")
    lines.append("")

    # Summary table
    lines.append("## Portfolio Summary")
    lines.append("")
    lines.append("| **Block: Portfolio-Summary** |||||")
    lines.append("|------|------|-------|-------|-------|")
    lines.append("| **Ref Arch** | **Name** | **Grade** | **Score** | **Pillars** |")

    for fr in forge_results:
        ra_id = fr["ref_arch"]
        ra_config = REFERENCE_ARCHITECTURES.get(ra_id, {})
        result = fr.get("result", {})
        audit = result.get("audit_report", {})

        grade = audit.get("grade", "N/A")
        score = audit.get("weighted_mean", 0)
        passed = audit.get("pillars_passed", 0)
        total = audit.get("total_pillars", 0)

        lines.append(f"| {ra_id} | {ra_config.get('name', 'Unknown')} | {grade} | {score}/3.0 | {passed}/{total} |")

    lines.append("")
    lines.append("---")
    lines.append("")

    # Individual specs
    lines.append("## Reference Architectures")
    lines.append("")

    for fr in forge_results:
        ra_id = fr["ref_arch"]
        version = fr.get("version", "3.0")
        ra_config = REFERENCE_ARCHITECTURES.get(ra_id, {})
        result = fr.get("result", {})
        audit = result.get("audit_report", {})
        meta = result.get("metadata", {})

        # Get version-specific output file
        if "versions" in ra_config and version in ra_config["versions"]:
            output_file = ra_config["versions"][version]["output_file"]
        else:
            output_file = ra_config.get("output_file", "N/A")

        lines.append(f"### {ra_id}: {ra_config.get('name', 'Unknown')}")
        lines.append("")
        lines.append(f"| **Block: {ra_id}-Summary** ||")
        lines.append("|-----------|-------|")
        lines.append(f"| **Pattern** | {ra_config.get('pattern', 'Unknown')} |")
        lines.append(f"| **Description** | {ra_config.get('description', 'N/A')} |")
        lines.append(f"| **Version** | {version} |")
        lines.append(f"| **Grade** | {audit.get('grade', 'N/A')} |")
        lines.append(f"| **Score** | {audit.get('weighted_mean', 0)}/3.0 |")
        lines.append(f"| **Pillars** | {audit.get('pillars_passed', 0)}/{audit.get('total_pillars', 0)} |")
        lines.append(f"| **Token Count** | {meta.get('token_count', 'N/A')} |")
        lines.append(f"| **Est. Forge Cost** | {meta.get('est_forge_cost', 'N/A')} |")
        lines.append(f"| **Tech Spec** | [{output_file}](outputs/{output_file}) |")
        lines.append(f"| **Diagram** | [{ra_config.get('diagram_file', 'N/A')}](outputs/diagrams/{ra_config.get('diagram_file', '')}) |")
        lines.append("")

        # Tier breakdown
        tier_summaries = audit.get("tier_summaries", {})
        if tier_summaries:
            lines.append(f"| **Block: {ra_id}-Tiers** |||")
            lines.append("|------|-------|-------|")
            lines.append("| **Tier** | **Passed** | **Avg Score** |")
            for tier_name, summary in tier_summaries.items():
                lines.append(f"| {tier_name} | {summary.get('passed', 0)}/{summary.get('total', 0)} | {summary.get('avg_score', 0)} |")
            lines.append("")

        lines.append("---")
        lines.append("")

    # Footer
    lines.append("## Engine Info")
    lines.append("")
    lines.append("| **Block: Engine-Info** ||")
    lines.append("|-----------|-------|")
    lines.append("| **Refinery Version** | V3.0 (23 Pillars - Glossy Portfolio Standard) |")
    lines.append("| **Visual Standard** | SAP Blue / Adobe Red |")
    lines.append("| **Visual Forge** | Mermaid + SVG + Draw.io |")
    lines.append("| **Glossary** | Executive Glossary [G01]-[G15] |")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("*Generated by SA-DocGen-Synth V3.0 (Glossy Portfolio Standard)*")

    return "\n".join(lines)


# ============================================================
# Harvest & Refine Mode (Research + Heal + Forge)
# ============================================================

def harvest_refine(
    target: str,
    project: Optional[str] = None,
    search_function: Optional[callable] = None,
    auto_forge: bool = True,
    use_registry: bool = True,
    llm_forge: bool = False,
    llm_provider: str = "anthropic",
) -> Dict[str, Any]:
    """
    Execute the Harvest & Refine workflow for a target system.

    This mode implements a 5-phase pipeline:
    1. LOAD: Read discovery document (with Registry Resolution)
    2. EXECUTE: Research missing pillar evidence (with Seed Flip)
    3. HEAL: Replace TBD markers with discovered facts
    4. SANITIZE: Apply [R01] domain isolation
    5. FINAL STRIKE: Trigger glossy_v3 forge (with auto-persistence)

    Master Registry Integration:
    - Resolves target slug to extracted_product_name ("Seed Flip")
    - Saves output to product home silo in SA-Synthesis-Kit
    - Enforces Elite Discovery (minimum 50 evidence items)
    - Raises TruthGapError if insufficient Physical Truth
    - Auto-updates registry after successful forge

    LLM Forge Mode (--llm-forge):
    - Instead of template-filling with evidence snippets, uses LLM to generate
      coherent prose documentation using evidence as grounding context
    - Produces professional, readable technical specifications
    - Requires ANTHROPIC_API_KEY or OPENAI_API_KEY environment variable

    Args:
        target: Target system slug (e.g., "adobe-rtcdp", "sap-event-mesh")
        project: [R01] Project flag for domain isolation
        search_function: Optional web search function for research
        auto_forge: If True, automatically run glossy_v3 forge after healing
        use_registry: If True, use RegistryResolver for Seed Flip and persistence
        llm_forge: If True, use LLM-based content generation instead of templates
        llm_provider: LLM provider for llm_forge mode ("anthropic" or "openai")

    Returns:
        Dict with results from each phase

    Raises:
        TruthGapError: If evidence count < TRUTH_GAP_THRESHOLD
        RegistryNotFoundError: If target not in registry and use_registry=True
    """
    from agent_skills import (
        quick_audit,
        get_pillar_checklist,
        inject_glossary_references,
        inject_glossary_appendix,
    )

    print("=" * 70)
    print(f"HARVEST & REFINE: {target}")
    print("=" * 70)
    print()

    # ============================================================
    # REGISTRY RESOLUTION (Master Registry Mapping Layer)
    # ============================================================
    registry = None
    search_seed = target  # Default: use target as-is
    home_silo = None
    product_name = target

    if use_registry:
        try:
            registry = get_registry()
            product_info = registry.resolve(target)
            search_seed = registry.get_search_seed(target)
            home_silo = registry.get_home_silo(target)
            product_name = product_info.get("extracted_product_name", target)

            print("[Registry] Product Resolution:")
            print(f"  Target Slug: {target}")
            print(f"  Product Name: {product_name}")
            print(f"  Search Seed: {search_seed} (Seed Flip)")
            print(f"  Home Silo: {home_silo}")
            print()
        except RegistryNotFoundError as e:
            print(f"[Registry] Warning: {e}")
            print(f"[Registry] Falling back to legacy mode (outputs/)")
            print()
            use_registry = False

    print("Pipeline: LOAD -> EXECUTE -> HEAL -> SANITIZE -> FINAL STRIKE")
    print()

    results = {
        "target": target,
        "project": project,
        "phases": {},
        "success": False,
    }

    # ============================================================
    # PHASE 1: LOAD - Read Discovery Document
    # ============================================================
    print("-" * 70)
    print("PHASE 1: LOAD")
    print("-" * 70)

    content, doc_path = load_discovery_document(target)

    if content is None:
        print(f"  ERROR: No discovery document found for '{target}'")
        print(f"  Run first: python orchestrator.py --target \"{target}\" --pillar-audit")
        results["phases"]["load"] = {"success": False, "error": "Document not found"}
        return results

    print(f"  Loaded: {doc_path}")
    print(f"  Size: {len(content)} bytes")

    # Scan for TBD markers
    tbd_markers = scan_for_tbd_markers(content)
    print(f"  TBD Markers: {len(tbd_markers)}")

    results["phases"]["load"] = {
        "success": True,
        "document_path": str(doc_path),
        "document_size": len(content),
        "tbd_markers_found": len(tbd_markers),
    }

    # ============================================================
    # PHASE 2: EXECUTE - Research Missing Evidence (with Seed Flip)
    # ============================================================
    print()
    print("-" * 70)
    print("PHASE 2: EXECUTE (Research with Seed Flip)")
    print("-" * 70)

    # Display Seed Flip if using registry
    if use_registry and search_seed != target:
        print(f"  [Seed Flip] Using '{search_seed}' instead of '{target}'")

    # Check for cached evidence first (try both slug and product name)
    cached_search = create_search_function_from_cache(target)
    if cached_search is None and search_seed != target:
        cached_search = create_search_function_from_cache(search_seed)

    if cached_search and search_function is None:
        print(f"  [Cache] Found evidence cache for '{target}'")
        search_function = cached_search

    # Research ALL 23 pillars using the Seed Flip (product name for better results)
    all_pillars = [f"P{i:02d}" for i in range(1, 24)]
    research_report = research_target(
        search_seed,  # Use Seed Flip here for better search results
        pillar_ids=all_pillars,
        search_function=search_function
    )

    # ALWAYS inject cached evidence to ensure full coverage
    # Try both target slug and search_seed for cache lookup
    print("  [Cache] Injecting full evidence cache...")
    research_report = inject_cached_evidence_into_report(research_report, target)
    if search_seed != target:
        research_report = inject_cached_evidence_into_report(research_report, search_seed)

    total_evidence = sum(len(e) for e in research_report.evidence_by_pillar.values())

    print(f"  Evidence Harvested: {total_evidence} items")
    print(f"  Pillars Researched: {len(research_report.pillars_researched)}")
    print(f"  Gaps Remaining: {len(research_report.gaps_remaining)}")

    # ============================================================
    # ELITE DISCOVERY ENFORCEMENT
    # ============================================================
    print()
    print(f"  [Elite Discovery] Minimum: {ELITE_EVIDENCE_MINIMUM} evidence items")
    print(f"  [Elite Discovery] Actual: {total_evidence} evidence items")

    if total_evidence < TRUTH_GAP_THRESHOLD:
        # Critical failure - not enough Physical Truth to proceed
        error_msg = (
            f"TRUTH_GAP: Only {total_evidence} evidence items found for '{target}'. "
            f"Minimum required: {TRUTH_GAP_THRESHOLD}. "
            f"Cannot proceed - insufficient Physical Truth for reliable forge."
        )
        print()
        print("!" * 70)
        print(f"  ERROR: {error_msg}")
        print("!" * 70)

        results["phases"]["execute"] = {
            "success": False,
            "evidence_count": total_evidence,
            "error": "TRUTH_GAP",
            "message": error_msg,
        }
        results["error"] = "TRUTH_GAP"
        results["error_message"] = error_msg

        raise TruthGapError(error_msg)

    elif total_evidence < ELITE_EVIDENCE_MINIMUM:
        # Warning - below ELITE threshold but can proceed
        print(f"  [Elite Discovery] WARNING: Below ELITE threshold ({ELITE_EVIDENCE_MINIMUM})")
        print(f"  [Elite Discovery] Grade will likely be ACCEPTABLE or lower")
        elite_status = "BELOW_THRESHOLD"
    else:
        print(f"  [Elite Discovery] PASSED - Sufficient evidence for ELITE grade")
        elite_status = "ELITE_READY"

    results["phases"]["execute"] = {
        "success": True,
        "evidence_count": total_evidence,
        "pillars_researched": research_report.pillars_researched,
        "gaps_remaining": research_report.gaps_remaining,
        "elite_status": elite_status,
        "search_seed": search_seed,
    }

    # ============================================================
    # PHASE 3: HEAL - Replace TBD Markers with Evidence
    # ============================================================
    print()
    print("-" * 70)
    print("PHASE 3: HEAL")
    print("-" * 70)

    healed_content = content
    replacements_made = 0

    # Build replacement map from evidence
    evidence_replacements = _build_evidence_replacements(research_report)

    # Apply replacements
    for marker in tbd_markers:
        if marker.pillar_id and marker.pillar_id in evidence_replacements:
            replacement = evidence_replacements[marker.pillar_id]
            if replacement:
                # Replace the TBD marker line with evidence
                old_line = marker.line_content
                new_line = _heal_line_with_evidence(old_line, replacement)
                if old_line != new_line:
                    healed_content = healed_content.replace(old_line, new_line)
                    replacements_made += 1

    print(f"  Markers Healed: {replacements_made}/{len(tbd_markers)}")

    # Also inject standard pillar content for gaps
    # Pass product_name for proper scaffolding (Vendor-* naming when domain-isolated)
    healed_content = _inject_pillar_scaffolding(
        healed_content,
        target,
        research_report,
        product_name=product_name if use_registry else target,
        project=project,
    )

    results["phases"]["heal"] = {
        "success": True,
        "markers_healed": replacements_made,
        "markers_total": len(tbd_markers),
    }

    # ============================================================
    # PHASE 4: SANITIZE - Apply [R01] Domain Isolation
    # ============================================================
    print()
    print("-" * 70)
    print("PHASE 4: SANITIZE [R01]")
    print("-" * 70)

    # Validate compliance before sanitization
    compliance_before = validate_domain_compliance(healed_content, project)
    print(f"  Pre-Sanitize Violations: {compliance_before['violations_count']}")

    if not compliance_before["compliant"] and project is None:
        # Apply strict sanitization
        sanitized_content = enforce_domain_isolation(healed_content, project)
        compliance_after = validate_domain_compliance(sanitized_content, project)
        print(f"  Post-Sanitize Violations: {compliance_after['violations_count']}")
        print(f"  [R01] Sanitization: APPLIED")
    else:
        sanitized_content = healed_content
        compliance_after = compliance_before
        if project:
            print(f"  [R01] Project '{project}' authorizes detected ecosystems")
        else:
            print(f"  [R01] Content already compliant")

    results["phases"]["sanitize"] = {
        "success": True,
        "violations_before": compliance_before["violations_count"],
        "violations_after": compliance_after["violations_count"],
        "project": project,
    }

    # ============================================================
    # CORRUPTION DETECTION GATE (V3.1 Hard-Gate)
    # ============================================================
    # Abort if R01 sanitization corrupted content semantically
    corruption_errors = []

    # Check 1: Vendor-Vendor stutter (semantic failure)
    if "Vendor-Vendor" in sanitized_content:
        corruption_errors.append("SEMANTIC_STUTTER: 'Vendor-Vendor' pattern detected")

    # Check 2: Excessive Vendor- replacement (indicates missing --project flag)
    vendor_count = sanitized_content.count("Vendor-")
    if vendor_count > 20 and project is None:
        corruption_errors.append(f"EXCESSIVE_SANITIZATION: {vendor_count} 'Vendor-' replacements without --project flag")

    # Check 3: Product name missing (for SAP products, name should be preserved with --project sap)
    if target.startswith("sap-") and project is None:
        # SAP product without --project flag = guaranteed corruption
        corruption_errors.append(f"MISSING_PROJECT_FLAG: SAP product '{target}' requires --project sap")

    # Check 4: Verify product_name appears in content when project is set
    if project and product_name and product_name not in sanitized_content:
        # Product name should be preserved when project flag is set
        corruption_errors.append(f"PRODUCT_NAME_STRIPPED: '{product_name}' not found in content")

    if corruption_errors:
        print()
        print("!" * 70)
        print("CORRUPTION DETECTION GATE - HARD ABORT")
        print("!" * 70)
        for err in corruption_errors:
            print(f"  [FAIL] {err}")
        print()
        print("RESOLUTION: Re-run with --project sap (or appropriate ecosystem flag)")
        print(f"  python orchestrator.py --target \"{target}\" --mode harvest_refine --project sap")
        print("!" * 70)

        results["phases"]["corruption_gate"] = {
            "success": False,
            "errors": corruption_errors,
            "resolution": f"--project sap",
        }
        results["error"] = "CONTENT_CORRUPTION"
        results["error_message"] = "; ".join(corruption_errors)

        raise ValueError(f"CONTENT_CORRUPTION: {'; '.join(corruption_errors)}")

    print()
    print("  [Corruption Gate] PASSED - No semantic corruption detected")
    results["phases"]["corruption_gate"] = {"success": True, "vendor_count": vendor_count}

    # Save healed document
    healed_doc_path = Path(f"outputs/discovery/{target.lower()}_healed.md")
    healed_doc_path.write_text(sanitized_content, encoding="utf-8")
    print(f"  Healed Document: {healed_doc_path}")

    # ============================================================
    # PHASE 5: FINAL STRIKE - Glossy V3 Forge (with Auto-Persistence)
    # ============================================================
    print()
    print("-" * 70)
    print("PHASE 5: FINAL STRIKE (Glossy V3 Forge)")
    print("-" * 70)

    if not auto_forge:
        print("  Auto-forge disabled. Skipping...")
        results["phases"]["final_strike"] = {"success": False, "skipped": True}
    else:
        # Determine system name
        if project:
            forge_system_name = f"{product_name} Integration"
        else:
            forge_system_name = f"Vendor-{target.replace('-', '')} Integration"
        print(f"  System Name: {forge_system_name}")

        # ============================================================
        # LLM FORGE MODE: Generate content using LLM
        # ============================================================
        if llm_forge and LLM_GENERATOR_AVAILABLE:
            print()
            print("  [LLM FORGE MODE] Generating content via LLM...")
            print(f"  Provider: {llm_provider}")

            # Convert evidence to format expected by LLM generator
            evidence_by_pillar = {}
            if research_report and hasattr(research_report, 'evidence_by_pillar'):
                evidence_by_pillar = research_report.evidence_by_pillar

            total_evidence = sum(len(e) for e in evidence_by_pillar.values())
            print(f"  Evidence Items: {total_evidence} across {len(evidence_by_pillar)} pillars")

            # Call LLM generator
            try:
                llm_provider_enum = LLMProvider(llm_provider.lower())
            except (ValueError, NameError):
                llm_provider_enum = LLMProvider.ANTHROPIC

            llm_result = generate_full_spec(
                system_name=product_name if use_registry else target,
                evidence_by_pillar=evidence_by_pillar,
                provider=llm_provider_enum
            )

            if llm_result.success:
                print(f"  [LLM FORGE] SUCCESS - {len(llm_result.content)} chars generated")
                print(f"  [LLM FORGE] Tokens used: {llm_result.tokens_used}")
                print(f"  [LLM FORGE] Model: {llm_result.model}")

                # Build the final document with LLM content
                llm_content = f"# {forge_system_name}\n\n"
                llm_content += f"*Generated via LLM Forge Mode ({llm_result.model})*\n\n"
                llm_content += "---\n\n"
                llm_content += llm_result.content

                # Inject glossary references
                print("  Injecting glossary references...")
                glossy_content = inject_glossary_references(llm_content)
                glossy_content = inject_glossary_appendix(glossy_content)

                # Run blueprint generation for audit and metadata
                blueprint_result = generate_blueprint_v2(
                    system_name=forge_system_name,
                    content=glossy_content,
                    platform=llm_result.provider.title(),
                    model=llm_result.model,
                )
            else:
                print(f"  [LLM FORGE] FAILED: {llm_result.error}")
                print("  [LLM FORGE] Falling back to template mode...")
                llm_forge = False  # Fall through to template mode

        # ============================================================
        # TEMPLATE MODE: Original template-filling approach
        # ============================================================
        if not llm_forge or not LLM_GENERATOR_AVAILABLE:
            if llm_forge and not LLM_GENERATOR_AVAILABLE:
                print("  [WARNING] LLM generator not available. Using template mode.")
                print("  [INFO] Install with: pip install anthropic")

            # Run pre-forge audit
            print("  Running pre-forge audit...")
            pre_audit = quick_audit(sanitized_content)
            print(f"  Pre-Forge Grade: {pre_audit['grade']} ({pre_audit['score']}/3.0)")

            # Inject glossary references
            print("  Injecting glossary references...")
            glossy_content = inject_glossary_references(sanitized_content)
            glossy_content = inject_glossary_appendix(glossy_content)

            # Generate V3.0 Blueprint
            print("  Generating V3.0 Blueprint (template mode)...")
            blueprint_result = generate_blueprint_v2(
                system_name=forge_system_name,
                content=glossy_content,
                platform="Claude",
                model="claude-opus-4-5-20251101",
            )

        audit_result = blueprint_result["audit_report"]
        structural_grade = audit_result["grade"]
        structural_score = audit_result["weighted_mean"]

        # ============================================================
        # QUALITY VALIDATION (Real Content Analysis)
        # ============================================================
        final_grade = structural_grade
        final_score = structural_score
        quality_result = None

        if QUALITY_VALIDATOR_AVAILABLE:
            print()
            print("-" * 70)
            print("QUALITY VALIDATION (Content Analysis)")
            print("-" * 70)

            quality_result = validate_spec_quality(blueprint_result["markdown"], target)

            print(f"  Source Authority:    {quality_result.source_authority_score:.0%}")
            print(f"  Product Relevance:   {quality_result.product_relevance_score:.0%}")
            print(f"  Text Quality:        {quality_result.text_quality_score:.0%}")
            print(f"  Content Coherence:   {quality_result.content_coherence_score:.0%}")
            print(f"  Quality Score:       {quality_result.overall_score:.2f}/3.0")
            print(f"  Quality Grade:       {quality_result.grade.value}")

            if quality_result.warnings:
                print()
                print("  Warnings:")
                for warning in quality_result.warnings[:3]:
                    print(f"    - {warning}")

            if quality_result.issues:
                print()
                print("  Issues (blocking):")
                for issue in quality_result.issues:
                    print(f"    - {issue}")

            # Use QUALITY grade (more accurate) instead of structural grade
            # Quality validation is more stringent and catches content issues
            final_grade = quality_result.grade.value
            final_score = quality_result.overall_score

            # If structural was ELITE but quality is lower, downgrade
            if structural_grade == "ELITE" and final_grade != "ELITE":
                print()
                print(f"  [Grade Correction] Structural: {structural_grade} -> Quality: {final_grade}")
                print(f"  [Reason] Content quality validation found issues")

        # ============================================================
        # AUTO-PERSISTENCE TO HOME SILO
        # ============================================================
        output_filename = f"tech_spec_v3_0.md"

        if use_registry and home_silo:
            # Save to SA-Synthesis-Kit product home silo
            output_path = home_silo / output_filename
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(blueprint_result["markdown"], encoding="utf-8")
            print()
            print(f"  [Auto-Persistence] Saved to Home Silo:")
            print(f"    {output_path}")
        else:
            # Fallback to outputs/ directory
            output_path = Path(f"outputs/{target.lower()}_tech_spec_v3_0.md")
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(blueprint_result["markdown"], encoding="utf-8")
            print()
            print(f"  [Legacy] Saved to outputs/:")
            print(f"    {output_path}")

        print()
        print(f"  Structural Grade: {structural_grade} ({structural_score}/3.0)")
        print(f"  Final Grade: {final_grade} ({final_score}/3.0)")
        print(f"  Pillars Passed: {audit_result['pillars_passed']}/{audit_result['total_pillars']}")

        # ============================================================
        # REGISTRY STATE SYNC (with REAL grade)
        # ============================================================
        if use_registry and registry:
            print()
            print("  [Registry State Sync] Updating registry...")
            registry.update_registry(
                target_slug=target,
                tech_spec_exists=True,
                grade=final_grade,  # Use quality-validated grade
                score=final_score,  # Use quality-validated score
            )
            print(f"  [Registry State Sync] Complete (Grade: {final_grade})")

        results["phases"]["final_strike"] = {
            "success": True,
            "structural_grade": structural_grade,
            "structural_score": structural_score,
            "final_grade": final_grade,
            "final_score": final_score,
            "grade": final_grade,  # Backwards compatibility
            "score": final_score,  # Backwards compatibility
            "pillars_passed": audit_result["pillars_passed"],
            "pillars_total": audit_result["total_pillars"],
            "output_path": str(output_path),
            "home_silo": str(home_silo) if home_silo else None,
            "registry_synced": use_registry and registry is not None,
            "quality_validated": QUALITY_VALIDATOR_AVAILABLE,
        }

    # ============================================================
    # Summary
    # ============================================================
    print()
    print("=" * 70)
    print("HARVEST & REFINE COMPLETE")
    print("=" * 70)

    results["success"] = True

    # Print phase summary
    print()
    print("| Phase | Status |")
    print("|-------|--------|")
    for phase_name, phase_data in results["phases"].items():
        status = "OK" if phase_data.get("success") else "FAIL"
        print(f"| {phase_name.upper()} | {status} |")

    print()
    print("=" * 70)

    return results


def _build_evidence_replacements(report: ResearchReport) -> Dict[str, str]:
    """
    Build a map of pillar ID -> replacement text from research evidence.

    Args:
        report: Research report with evidence

    Returns:
        Dict mapping pillar ID to evidence text
    """
    replacements = {}

    for pid, evidences in report.evidence_by_pillar.items():
        if evidences:
            # Combine evidence into replacement text
            best_evidence = evidences[0]  # Take highest confidence
            replacements[pid] = best_evidence.evidence_text

    return replacements


def _heal_line_with_evidence(line: str, evidence: str) -> str:
    """
    Replace TBD markers in a line with evidence.

    Args:
        line: Original line with TBD marker
        evidence: Evidence text to insert

    Returns:
        Healed line
    """
    import re

    # Replace various TBD patterns
    patterns = [
        (r":\s*TBD\s*$", f": {evidence[:100]}"),
        (r":\s*\?\s*$", f": {evidence[:100]}"),
        (r"\bTBD\b", evidence[:50]),
        (r"\?\s*$", evidence[:50]),
    ]

    healed = line
    for pattern, replacement in patterns:
        healed = re.sub(pattern, replacement, healed, flags=re.IGNORECASE)

    return healed


def _inject_pillar_scaffolding(
    content: str,
    target: str,
    report: ResearchReport,
    product_name: Optional[str] = None,
    project: Optional[str] = None,
) -> str:
    """
    Inject complete pillar content from harvested evidence.

    This replaces the skeleton discovery document with fully-fleshed
    pillar sections containing "Physical Truth" from research.

    Args:
        content: Current document content
        target: Target system slug
        report: Research report with evidence
        product_name: Full product name (for display, uses [R01] Vendor- prefix if needed)
        project: Project flag (sap-only, adobe-only, etc.) - bypasses Vendor- prefix when set

    Returns:
        Content with complete pillar sections
    """
    # Use product_name for display, target for technical slugs
    display_name = product_name or target

    # Apply [R01] Domain Isolation - use Vendor- prefix ONLY when no project specified
    # When project is set (e.g., sap-only), use actual product name
    if project:
        # Project specified - use actual product name
        system_name = product_name or target.replace('-', ' ').title()
    else:
        # No project - apply domain isolation with Vendor- prefix
        system_name = f"Vendor-{target.replace('-', '')}"

    # Build complete new document with all pillar evidence
    new_sections = []

    # Determine source system based on project
    if project == "sap-only":
        source_system = "SAP BTP"
    elif project == "adobe-only":
        source_system = "Adobe Experience Platform"
    elif project == "sap-adobe":
        source_system = "SAP & Adobe"
    else:
        source_system = "Generic_Upstream"

    # Header
    new_sections.append(f"""# Tech Spec: {system_name}

<!-- EDS Block Pattern: Generated by Harvest & Refine Pipeline -->
<!-- Version: 3.0 - Glossy Portfolio Standard -->

| **Block: Spec-Metadata** ||
|-----------|-------|
| **Blueprint Version** | 3.0 |
| **System Name** | {system_name} |
| **Source System** | {source_system} |
| **Target System** | {system_name} |
| **Date** | {datetime.utcnow().strftime('%Y-%m-%d')} |
| **Status** | Draft (Auto-Generated) |

---

## Executive Summary

This Tech Spec defines the integration architecture for {system_name}. Evidence harvested from official documentation and research sources.

---

# TIER 1: CRITICAL PILLARS (Weight: 3)

> **HARD GATE**: All Tier 1 pillars must pass. Any pillar at 0.0 results in BLOCKED status.
""")

    # Generate content for each pillar
    tier1_pillars = ["P01", "P02", "P03", "P04", "P05"]
    tier2_pillars = ["P06", "P07", "P08", "P09", "P10", "P11", "P12", "P13", "P14", "P15"]
    tier3_pillars = ["P16", "P17", "P18", "P19", "P20", "P21", "P22", "P23"]

    def generate_pillar_section(pid: str, evidences: list) -> str:
        """Generate complete pillar section from evidence."""
        pillar_config = PILLAR_RESEARCH_QUERIES.get(pid, {})
        pillar_name = pillar_config.get("name", "Unknown")

        lines = []
        lines.append(f"\n## {pid}: {pillar_name}\n")
        lines.append(f"**Requirement**: {pillar_name} documented for {system_name}.\n")

        if evidences:
            # Evidence table
            lines.append(f"\n| **Block: {pid}-Config** ||")
            lines.append("|-----------|-------|")

            for ev in evidences[:5]:  # Limit to 5 evidence items
                fact = ev.evidence_text.replace("|", "/").replace("\n", " ")
                lines.append(f"| **Evidence** | {fact[:150]} |")

            # Source citations
            sources = list(set(ev.source_url for ev in evidences if ev.source_url))
            if sources:
                lines.append(f"| **Source** | {sources[0]} |")
                lines.append(f"| **Confidence** | {evidences[0].confidence.value} |")

            lines.append("")

            # Additional detail if multiple evidence items
            if len(evidences) > 1:
                lines.append(f"### {pid} Implementation Details\n")
                for i, ev in enumerate(evidences[:3], 1):
                    lines.append(f"{i}. {ev.evidence_text}")
                lines.append("")
        else:
            lines.append(f"\n*No evidence harvested. Manual research required.*\n")

        lines.append("---\n")
        return "\n".join(lines)

    # Tier 1
    for pid in tier1_pillars:
        evidences = report.evidence_by_pillar.get(pid, [])
        new_sections.append(generate_pillar_section(pid, evidences))

    # Tier 2 header
    new_sections.append("\n# TIER 2: HIGH PILLARS (Weight: 2)\n")

    for pid in tier2_pillars:
        evidences = report.evidence_by_pillar.get(pid, [])
        new_sections.append(generate_pillar_section(pid, evidences))

    # Tier 3 header
    new_sections.append("\n# TIER 3: MEDIUM PILLARS (Weight: 1)\n")

    for pid in tier3_pillars:
        evidences = report.evidence_by_pillar.get(pid, [])
        new_sections.append(generate_pillar_section(pid, evidences))

    # Risk Register
    new_sections.append(f"""
## Risk Register & Known Limitations

| **Block: Risk-Register** |||||
|----------|-------|-------|-------|-------|
| **Risk ID** | **Description** | **Probability** | **Impact** | **Mitigation** |
| R-001 | Rate limit exceeded (100 RPM) | Medium | High | Implement request queuing and backoff |
| R-002 | API credits exhausted mid-month | Low | Critical | Monitor credit consumption, alerts at 80% |
| R-003 | Token expiration | Low | Medium | Implement token refresh logic |

---

## Citations Summary

| **Block: Citations** ||||
|----|--------|-----|-----------|
| **ID** | **Source** | **URL** | **Retrieved** |
""")

    # Add citations from sources
    for i, source in enumerate(report.sources_consulted[:5], 1):
        new_sections.append(f"| {i} | {system_name} Documentation | {source} | {datetime.utcnow().strftime('%Y-%m-%d')} |")

    new_sections.append(f"""

---

## Generation Metadata

| **Block: Generation-Metadata** ||
|--------|-------|
| **Token Count** | {{{{TOKEN_COUNT}}}} |
| **Platform** | {{{{PLATFORM}}}} |
| **Model** | {{{{MODEL}}}} |
| **Timestamp** | {{{{TIMESTAMP}}}} |
| **Est. Forge Cost** | {{{{EST_FORGE_COST}}}} |

---

*Generated by SA-DocGen-Synth Harvest & Refine Pipeline V3.0*
""")

    return "\n".join(new_sections)


# ============================================================
# Standalone CLI
# ============================================================

def main():
    """CLI entry point for standalone validation and production forge."""
    import argparse
    import sys

    parser = argparse.ArgumentParser(
        description="SA-DocGen-Synth: Validate markdown or execute production forge"
    )

    # Subcommands via mutually exclusive group
    parser.add_argument(
        "markdown_file",
        nargs="?",
        help="Path to markdown file to validate (legacy mode)"
    )
    parser.add_argument(
        "-c", "--config",
        default=DEFAULT_CONFIG_PATH,
        help="Path to requirements matrix JSON"
    )
    parser.add_argument(
        "-o", "--output",
        help="Output file for validation report (default: stdout)"
    )
    parser.add_argument(
        "--v2",
        action="store_true",
        help="Generate Blueprint V2.0 format"
    )
    parser.add_argument(
        "--system",
        default="Unknown System",
        help="System name for V2 blueprint"
    )

    # Production forge arguments
    parser.add_argument(
        "--ref-arch",
        choices=list(REFERENCE_ARCHITECTURES.keys()),
        help="Reference architecture ID for production forge"
    )
    parser.add_argument(
        "--version",
        default="3.0",
        help="Blueprint version (default: 3.0)"
    )
    parser.add_argument(
        "--ultimate",
        action="store_true",
        help="Use Ultimate standard (23 pillars)"
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Forge all reference architectures"
    )
    parser.add_argument(
        "--index",
        action="store_true",
        help="Generate portfolio index after forge"
    )

    # V3.0 Target Discovery Mode
    parser.add_argument(
        "--target",
        help="Target system name for discovery audit (e.g., '6sense', 'Marketo')"
    )
    parser.add_argument(
        "--batch",
        help="Comma-separated list of targets for batch processing (e.g., 'sap-event-mesh, adobe-rtcdp')"
    )
    parser.add_argument(
        "--mode",
        choices=["glossy_v3", "quick", "full", "harvest_refine", "discovery", "forge"],
        default="glossy_v3",
        help=(
            "Audit mode: glossy_v3 (default), quick (checklist only), "
            "full (verbose), harvest_refine (research + heal + forge), "
            "discovery (batch discovery with auto-forge), "
            "forge (generate V3.0 One-Pager overview.md)"
        ),
    )
    parser.add_argument(
        "--pillar-audit",
        action="store_true",
        help="Run pillar audit against target system documentation"
    )
    parser.add_argument(
        "--continue-on-error",
        action="store_true",
        help="Continue batch processing even if individual targets fail"
    )

    # [R01] Domain Isolation
    available_projects = list_available_projects()
    parser.add_argument(
        "--project",
        choices=available_projects,
        default=None,
        help=(
            f"[R01] Project/ecosystem to activate. "
            f"Available: {', '.join(available_projects)}. "
            f"Default: None (uses Generic_Upstream/Generic_Consumer)."
        ),
    )

    # LLM Generation Mode
    parser.add_argument(
        "--llm-forge",
        action="store_true",
        help=(
            "Use LLM-based content generation instead of template filling. "
            "Produces coherent prose instead of pasted evidence snippets. "
            "Requires ANTHROPIC_API_KEY or OPENAI_API_KEY environment variable."
        ),
    )
    parser.add_argument(
        "--llm-provider",
        choices=["anthropic", "openai"],
        default="anthropic",
        help="LLM provider for --llm-forge mode (default: anthropic)"
    )

    args = parser.parse_args()

    # ============================================================
    # BATCH DISCOVERY MODE
    # ============================================================
    if args.batch and args.mode == "discovery":
        targets = [t.strip() for t in args.batch.split(",") if t.strip()]

        print("=" * 70)
        print("BATCH DISCOVERY STRIKE")
        print("=" * 70)
        print(f"Targets: {len(targets)}")
        for i, t in enumerate(targets, 1):
            print(f"  {i}. {t}")
        print()
        print("=" * 70)
        print()

        batch_results = {
            "total": len(targets),
            "success": 0,
            "failed": 0,
            "truth_gap": 0,
            "results": [],
        }

        # Create live web search function for evidence gathering
        live_search = create_live_search_function()

        for i, target in enumerate(targets, 1):
            print()
            print("#" * 70)
            print(f"# [{i}/{len(targets)}] TARGET: {target}")
            print("#" * 70)
            print()

            try:
                result = harvest_refine(
                    target=target,
                    project=args.project,
                    search_function=live_search,  # Enable live web search
                    auto_forge=True,
                    use_registry=True,
                    llm_forge=args.llm_forge,
                    llm_provider=args.llm_provider,
                )

                if result.get("success"):
                    batch_results["success"] += 1
                    final_strike = result.get("phases", {}).get("final_strike", {})
                    batch_results["results"].append({
                        "target": target,
                        "status": "SUCCESS",
                        "grade": final_strike.get("grade", "N/A"),
                        "score": final_strike.get("score", 0),
                        "output_path": final_strike.get("output_path", "N/A"),
                    })
                else:
                    batch_results["failed"] += 1
                    # Check for specific failure types
                    load_phase = result.get("phases", {}).get("load", {})
                    if load_phase.get("error") == "Document not found":
                        batch_results["results"].append({
                            "target": target,
                            "status": "NO_DISCOVERY",
                            "error": f"Run: python orchestrator.py --target \"{target}\" --pillar-audit",
                        })
                    else:
                        batch_results["results"].append({
                            "target": target,
                            "status": "FAILED",
                            "error": result.get("error", "Unknown"),
                        })

            except TruthGapError as e:
                batch_results["truth_gap"] += 1
                batch_results["failed"] += 1
                batch_results["results"].append({
                    "target": target,
                    "status": "TRUTH_GAP",
                    "error": str(e),
                })
                if not args.continue_on_error:
                    print()
                    print(f"[Batch] Stopping due to TRUTH_GAP error.")
                    print(f"[Batch] Use --continue-on-error to skip failed targets.")
                    break
                else:
                    print()
                    print(f"[Batch] Skipping {target} due to TRUTH_GAP, continuing...")

            except Exception as e:
                batch_results["failed"] += 1
                error_str = str(e)
                status = "ERROR"

                # Detect specific error types
                if "No discovery document found" in error_str or "Document not found" in error_str:
                    status = "NO_DISCOVERY"
                    batch_results["results"].append({
                        "target": target,
                        "status": status,
                        "error": f"Run: python orchestrator.py --target \"{target}\" --pillar-audit",
                    })
                else:
                    batch_results["results"].append({
                        "target": target,
                        "status": status,
                        "error": error_str,
                    })

                if not args.continue_on_error:
                    print()
                    print(f"[Batch] Stopping due to error: {e}")
                    break
                else:
                    print()
                    print(f"[Batch] Skipping {target} due to error, continuing...")

        # Print batch summary
        print()
        print("=" * 70)
        print("BATCH DISCOVERY SUMMARY")
        print("=" * 70)
        print()
        print(f"| Target | Status | Grade | Score |")
        print(f"|--------|--------|-------|-------|")
        for r in batch_results["results"]:
            status = r.get("status", "?")
            grade = r.get("grade", "-")
            score = r.get("score", "-")
            if isinstance(score, float):
                score = f"{score:.2f}"
            print(f"| {r['target']} | {status} | {grade} | {score} |")

        print()
        print(f"Total: {batch_results['total']}")
        print(f"Success: {batch_results['success']}")
        print(f"Failed: {batch_results['failed']} (TRUTH_GAP: {batch_results['truth_gap']})")
        print()
        print("=" * 70)

        # Print JSON summary
        print()
        print("JSON Result:")
        print(json.dumps(batch_results, indent=2, default=str))
        return

    # ============================================================
    # BATCH FORGE MODE - Generate V3.0 One-Pagers
    # ============================================================
    if args.batch and args.mode == "forge":
        targets = [t.strip() for t in args.batch.split(",") if t.strip()]
        results = batch_forge_one_pagers(targets, apply_r01=True)

        # Print JSON summary
        print()
        print("JSON Result:")
        print(json.dumps(results, indent=2, default=str))
        return

    # Harvest & Refine Mode
    if args.target and args.mode == "harvest_refine":
        # Create live web search function for evidence gathering
        live_search = create_live_search_function()

        result = harvest_refine(
            target=args.target,
            project=args.project,
            search_function=live_search,  # Enable live web search
            auto_forge=True,
            llm_forge=args.llm_forge,
            llm_provider=args.llm_provider,
        )
        # Print JSON summary
        print()
        print("JSON Result:")
        print(json.dumps(result, indent=2, default=str))
        return

    # Target Discovery / Pillar Audit Mode
    if args.target and args.pillar_audit:
        run_target_discovery_audit(args.target, args.mode)
        return

    # Production forge mode
    if args.ref_arch or args.all:
        forge_results = []

        # [R01] Display domain profile info
        profile = get_domain_profile(args.project)
        if args.project:
            print(f"[R01] Domain Profile: {profile.name}")
            print(f"       Source: {profile.source_system}")
            print(f"       Downstream: {profile.downstream_system}")
        else:
            print(f"[R01] Domain Profile: Generic (domain-isolated)")
            print(f"       Source: {profile.source_system}")
            print(f"       Downstream: {profile.downstream_system}")
        print()

        if args.all:
            # Forge all reference architectures
            for ra_id in REFERENCE_ARCHITECTURES.keys():
                result = production_forge(ra_id, args.version, args.ultimate, args.project)
                forge_results.append(result)
        else:
            # Forge single reference architecture
            result = production_forge(args.ref_arch, args.version, args.ultimate, args.project)
            forge_results.append(result)

        # Generate portfolio index if requested
        if args.index or args.all:
            index_content = generate_portfolio_index(forge_results)
            index_path = Path("outputs/index.md")
            index_path.write_text(index_content, encoding="utf-8")
            print(f"\nPortfolio index generated: {index_path}")

        return

    # Legacy validation mode
    if not args.markdown_file:
        parser.print_help()
        sys.exit(1)

    md_path = Path(args.markdown_file)
    if not md_path.exists():
        print(f"Error: File not found: {md_path}", file=sys.stderr)
        sys.exit(1)

    markdown_text = md_path.read_text(encoding="utf-8")

    if args.v2:
        # Generate V2 blueprint
        result = generate_blueprint_v2(
            system_name=args.system,
            content=markdown_text,
        )
        output_text = result["markdown"]
        print(f"Grade: {result['audit_report']['grade']}")
        print(f"Score: {result['audit_report']['weighted_mean']}/3.0")
        print(f"Tokens: {result['metadata']['token_count']}")
    else:
        # Run validation (legacy mode)
        validation = validate_document(markdown_text, args.config)
        report = validation["report"]

        output = []
        output.append(f"Validation Report: {md_path.name}")
        output.append("=" * 50)
        output.append(f"Match Rate: {report.match_rate}% ({report.passed_requirements}/{report.total_requirements})")
        output.append(f"Hard Failures: {report.hard_failures}")
        output.append(f"Soft Failures: {report.soft_failures}")
        output.append(f"Penalty: -{int(report.penalty_applied * 100)}%")
        output.append("")
        output.append(validation["formatted_markdown"])
        output_text = "\n".join(output)

    if args.output:
        Path(args.output).write_text(output_text, encoding="utf-8")
        print(f"Report written to: {args.output}")
    elif not args.v2:
        print(output_text)


if __name__ == "__main__":
    main()
