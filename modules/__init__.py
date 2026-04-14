"""
modules/__init__.py
-------------------
SA-DocGen-Synth Modules Package

Contains:
- quality_validator: Real content quality validation
- text_normalizer: Fix text concatenation artifacts
- llm_generator: LLM-based content generation
"""

from .quality_validator import (
    validate_spec_quality,
    quick_quality_check,
    get_quality_grade,
    QualityGrade,
    QualityResult,
)

__all__ = [
    "validate_spec_quality",
    "quick_quality_check",
    "get_quality_grade",
    "QualityGrade",
    "QualityResult",
]
