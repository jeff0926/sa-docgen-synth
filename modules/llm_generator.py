"""
llm_generator.py
----------------
LLM-based content generation using evidence as grounding context.
Follows DocGen Pro's architecture: evidence informs LLM, LLM writes document.

Author: Claude Code Prototype
Date: 2026-03-26
"""

import os
import json
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum

# Import text normalizer
from .text_normalizer import normalize_evidence_text, extract_key_facts


class LLMProvider(Enum):
    """Supported LLM providers."""
    ANTHROPIC = "anthropic"
    OPENAI = "openai"
    GEMINI = "gemini"


@dataclass
class GenerationResult:
    """Result of LLM generation."""
    content: str
    provider: str
    model: str
    tokens_used: int
    success: bool
    error: Optional[str] = None


# ============================================================
# PROMPT TEMPLATES
# ============================================================

PILLAR_GENERATION_PROMPT = """You are a Principal Solutions Architect writing technical documentation.

Your task: Write a clear, accurate, professional documentation section for **{pillar_name}**
regarding the system **{system_name}**.

## Evidence Context
The following evidence was gathered from official documentation and trusted sources:

{evidence_context}

## Requirements
1. Write 2-4 paragraphs of clear, professional prose
2. Include specific technical details from the evidence
3. Use proper terminology (OAuth 2.0, REST API, etc.)
4. Note any gaps or unknowns explicitly
5. Do NOT make up information not supported by evidence
6. Use confidence markers: 🟢 (verified), 🟡 (inferred), 🔴 (gap)

## Output Format
Write in Markdown. Include:
- A brief overview paragraph
- Technical specifics (endpoints, methods, formats)
- Configuration or implementation notes
- Any limitations or considerations

Begin your response with the content directly (no preamble)."""


FULL_SPEC_GENERATION_PROMPT = """You are a Principal Solutions Architect creating a technical integration specification.

Your task: Generate a comprehensive **Integration Technical Specification** for **{system_name}**.

## Evidence Summary
The following evidence was gathered across {pillar_count} technical pillars:

{evidence_summary}

## Document Structure
Generate a complete technical specification with these sections:

1. **Executive Summary** - 2-3 sentences on what this system does
2. **Authentication & Authorization** - How to authenticate (OAuth, API keys, etc.)
3. **API Endpoints & Methods** - Key endpoints, HTTP methods, base URLs
4. **Data Contracts** - Request/response formats, schemas
5. **Rate Limiting & Quotas** - Limits, throttling, backoff strategies
6. **Error Handling** - Error codes, response formats, retry logic
7. **Security Considerations** - TLS, encryption, data handling
8. **Webhook & Event Architecture** - If applicable
9. **Pagination & Bulk Operations** - How to handle large datasets
10. **Integration Examples** - curl and Python code samples
11. **Known Limitations** - Gaps, unknowns, caveats
12. **References** - Source URLs

## CRITICAL CITATION REQUIREMENTS
- EVERY factual claim MUST include the source URL in markdown link format: [text](URL)
- When describing technical details (endpoints, auth methods, error codes), cite the source immediately
- Example: "The API uses OAuth 2.0 with client credentials flow ([SAP Help](https://help.sap.com/...))"
- Example: "Rate limit is 100 requests/minute ([API Docs](https://api.sap.com/...))"
- The References section must list ALL source URLs used in the document
- If a fact has no source URL in the evidence, mark it with 🔴 and note the gap

## Guidelines
- Write professional, clear prose (not bullet fragments)
- Include code examples where evidence supports them
- Use tables for structured data (rate limits, error codes)
- Mark confidence: 🟢 verified, 🟡 inferred, 🔴 gap/unknown
- Do NOT fabricate details not in evidence
- Note explicitly when information is missing
- ALWAYS cite sources inline - this is non-negotiable for quality validation

Begin with the Executive Summary."""


# ============================================================
# EVIDENCE FORMATTING
# ============================================================

def format_evidence_for_prompt(evidence_items: List[Any], max_items: int = 10) -> str:
    """
    Format evidence items into a clean context block for LLM prompting.

    Args:
        evidence_items: List of ResearchEvidence objects
        max_items: Maximum evidence items to include

    Returns:
        Formatted evidence string for prompt injection
    """
    if not evidence_items:
        return "*No evidence available. Generate based on general knowledge with 🔴 markers.*"

    lines = []
    for i, ev in enumerate(evidence_items[:max_items], 1):
        # Normalize the text
        text = normalize_evidence_text(ev.evidence_text)

        # Extract key facts
        facts = extract_key_facts(text)

        # Get source info
        source = getattr(ev, 'source_url', 'Unknown source')
        confidence = getattr(ev, 'confidence', 'MEDIUM')
        if hasattr(confidence, 'value'):
            confidence = confidence.value

        lines.append(f"**Evidence {i}** (Confidence: {confidence})")
        if facts:
            for fact in facts:
                lines.append(f"  - {fact}")
        else:
            lines.append(f"  - {text[:200]}")
        lines.append(f"  - Source: {source}")
        lines.append("")

    return "\n".join(lines)


def build_evidence_summary(evidence_by_pillar: Dict[str, List[Any]]) -> str:
    """
    Build a summary of all evidence across pillars WITH SOURCE CITATIONS.

    Args:
        evidence_by_pillar: Dict mapping pillar IDs to evidence lists

    Returns:
        Formatted summary string with source URLs
    """
    lines = []

    pillar_names = {
        "P01": "Authentication & Identity",
        "P02": "Error Handling",
        "P03": "Data Contracts",
        "P04": "API Endpoints",
        "P05": "Security",
        "P06": "Rate Limiting",
        "P07": "Retry & Backoff",
        "P08": "Idempotency",
        "P09": "Pagination",
        "P10": "Webhooks",
        "P11": "Observability",
        "P12": "Data Privacy",
        "P13": "Timeouts",
        "P14": "Versioning",
        "P15": "SDKs",
        "P16": "SLAs",
        "P17": "Disaster Recovery",
        "P18": "Testing",
        "P19": "Change Management",
        "P20": "Architecture",
        "P21": "Pricing",
        "P22": "Chaos Testing",
        "P23": "Best Practices",
    }

    for pid, evidences in evidence_by_pillar.items():
        pillar_name = pillar_names.get(pid, pid)
        evidence_count = len(evidences)

        if evidence_count > 0:
            # Get top facts AND source URLs from first few evidence items
            top_facts_with_sources = []
            for ev in evidences[:3]:
                text = normalize_evidence_text(ev.evidence_text)
                facts = extract_key_facts(text, max_facts=1)
                source = getattr(ev, 'source_url', 'Unknown source')

                for fact in facts:
                    top_facts_with_sources.append((fact, source))

            lines.append(f"### {pid}: {pillar_name} ({evidence_count} sources)")
            for fact, source in top_facts_with_sources[:3]:
                lines.append(f"- {fact}")
                lines.append(f"  - Source: {source}")
            lines.append("")
        else:
            lines.append(f"### {pid}: {pillar_name} (⚠️ NO EVIDENCE)")
            lines.append("- *Manual research required*")
            lines.append("")

    return "\n".join(lines)


# ============================================================
# LLM CALLING (Anthropic/Claude)
# ============================================================

def call_anthropic(prompt: str, model: str = "claude-sonnet-4-20250514") -> GenerationResult:
    """
    Call Anthropic's Claude API.

    Args:
        prompt: The full prompt to send
        model: Model ID to use

    Returns:
        GenerationResult with content or error
    """
    try:
        import anthropic
    except ImportError:
        return GenerationResult(
            content="",
            provider="anthropic",
            model=model,
            tokens_used=0,
            success=False,
            error="anthropic package not installed. Run: pip install anthropic"
        )

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return GenerationResult(
            content="",
            provider="anthropic",
            model=model,
            tokens_used=0,
            success=False,
            error="ANTHROPIC_API_KEY environment variable not set"
        )

    try:
        client = anthropic.Anthropic(api_key=api_key)

        response = client.messages.create(
            model=model,
            max_tokens=8000,
            temperature=0.3,  # Lower temperature for factual content
            messages=[
                {"role": "user", "content": prompt}
            ]
        )

        content = response.content[0].text
        tokens = response.usage.input_tokens + response.usage.output_tokens

        return GenerationResult(
            content=content,
            provider="anthropic",
            model=model,
            tokens_used=tokens,
            success=True
        )

    except Exception as e:
        return GenerationResult(
            content="",
            provider="anthropic",
            model=model,
            tokens_used=0,
            success=False,
            error=str(e)
        )


def call_openai(prompt: str, model: str = "gpt-4o") -> GenerationResult:
    """
    Call OpenAI's API.

    Args:
        prompt: The full prompt to send
        model: Model ID to use

    Returns:
        GenerationResult with content or error
    """
    try:
        import openai
    except ImportError:
        return GenerationResult(
            content="",
            provider="openai",
            model=model,
            tokens_used=0,
            success=False,
            error="openai package not installed. Run: pip install openai"
        )

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        return GenerationResult(
            content="",
            provider="openai",
            model=model,
            tokens_used=0,
            success=False,
            error="OPENAI_API_KEY environment variable not set"
        )

    try:
        client = openai.OpenAI(api_key=api_key)

        response = client.chat.completions.create(
            model=model,
            max_tokens=8000,
            temperature=0.3,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )

        content = response.choices[0].message.content
        tokens = response.usage.total_tokens

        return GenerationResult(
            content=content,
            provider="openai",
            model=model,
            tokens_used=tokens,
            success=True
        )

    except Exception as e:
        return GenerationResult(
            content="",
            provider="openai",
            model=model,
            tokens_used=0,
            success=False,
            error=str(e)
        )


# ============================================================
# MAIN GENERATION FUNCTIONS
# ============================================================

def generate_pillar_content(
    pillar_id: str,
    pillar_name: str,
    system_name: str,
    evidence_items: List[Any],
    provider: LLMProvider = LLMProvider.ANTHROPIC
) -> GenerationResult:
    """
    Generate content for a single pillar using LLM.

    Args:
        pillar_id: Pillar ID (e.g., "P01")
        pillar_name: Human-readable pillar name
        system_name: Name of the system being documented
        evidence_items: List of evidence for this pillar
        provider: LLM provider to use

    Returns:
        GenerationResult with generated content
    """
    # Format evidence for prompt
    evidence_context = format_evidence_for_prompt(evidence_items)

    # Build prompt
    prompt = PILLAR_GENERATION_PROMPT.format(
        pillar_name=pillar_name,
        system_name=system_name,
        evidence_context=evidence_context
    )

    # Call appropriate provider
    if provider == LLMProvider.ANTHROPIC:
        return call_anthropic(prompt)
    elif provider == LLMProvider.OPENAI:
        return call_openai(prompt)
    else:
        return GenerationResult(
            content="",
            provider=provider.value,
            model="",
            tokens_used=0,
            success=False,
            error=f"Unsupported provider: {provider}"
        )


def generate_full_spec(
    system_name: str,
    evidence_by_pillar: Dict[str, List[Any]],
    provider: LLMProvider = LLMProvider.ANTHROPIC
) -> GenerationResult:
    """
    Generate a complete technical specification using LLM.

    Args:
        system_name: Name of the system being documented
        evidence_by_pillar: Dict mapping pillar IDs to evidence lists
        provider: LLM provider to use

    Returns:
        GenerationResult with full specification
    """
    # Build evidence summary
    evidence_summary = build_evidence_summary(evidence_by_pillar)
    pillar_count = len([p for p, e in evidence_by_pillar.items() if e])

    # Build prompt
    prompt = FULL_SPEC_GENERATION_PROMPT.format(
        system_name=system_name,
        pillar_count=pillar_count,
        evidence_summary=evidence_summary
    )

    # Call appropriate provider
    if provider == LLMProvider.ANTHROPIC:
        return call_anthropic(prompt, model="claude-sonnet-4-20250514")
    elif provider == LLMProvider.OPENAI:
        return call_openai(prompt, model="gpt-4o")
    else:
        return GenerationResult(
            content="",
            provider=provider.value,
            model="",
            tokens_used=0,
            success=False,
            error=f"Unsupported provider: {provider}"
        )


# ============================================================
# INTEGRATION HELPER
# ============================================================

def generate_spec_from_research_report(
    research_report: Any,
    system_name: str,
    provider: str = "anthropic"
) -> Dict[str, Any]:
    """
    Generate a complete spec from a ResearchReport object.
    This is the main integration point for orchestrator.py.

    Args:
        research_report: ResearchReport from researcher.py
        system_name: Name of the system
        provider: LLM provider name ("anthropic", "openai")

    Returns:
        Dict with 'content', 'success', 'error', 'metadata'
    """
    # Convert provider string to enum
    try:
        llm_provider = LLMProvider(provider.lower())
    except ValueError:
        llm_provider = LLMProvider.ANTHROPIC

    # Get evidence by pillar from report
    evidence_by_pillar = getattr(research_report, 'evidence_by_pillar', {})

    # Generate full spec
    result = generate_full_spec(
        system_name=system_name,
        evidence_by_pillar=evidence_by_pillar,
        provider=llm_provider
    )

    return {
        "content": result.content,
        "success": result.success,
        "error": result.error,
        "metadata": {
            "provider": result.provider,
            "model": result.model,
            "tokens_used": result.tokens_used,
            "pillar_count": len(evidence_by_pillar),
            "evidence_count": sum(len(e) for e in evidence_by_pillar.values())
        }
    }


# Quick test
if __name__ == "__main__":
    # Test evidence formatting
    class MockEvidence:
        def __init__(self, text, url, conf):
            self.evidence_text = text
            self.source_url = url
            self.confidence = conf

    mock_evidence = [
        MockEvidence(
            "OAuth2.0allows a user to grant a client access to protected resources",
            "https://help.sap.com/docs/auth",
            "HIGH"
        ),
        MockEvidence(
            "SAP BTP uses OAuth 2.0 with JWT tokens for API authentication",
            "https://help.sap.com/docs/btp",
            "HIGH"
        ),
    ]

    print("Evidence Formatting Test:")
    print("=" * 60)
    print(format_evidence_for_prompt(mock_evidence))
