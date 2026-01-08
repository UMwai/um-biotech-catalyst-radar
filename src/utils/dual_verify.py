"""Dual-Model Verification for Extraction Trust.

Per spec Phase 3 Section 2.4:
- Cross-verify LLM extractions between Claude and Gemini
- Flag disagreements for manual review
- Track verification confidence scores
"""

from __future__ import annotations

import json
import logging
import os
import re
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


# Extraction prompts (shared between models)
SEC_EXTRACTION_PROMPT = """
Extract financial data from this SEC filing text.

Text:
{text}

Return JSON with these fields:
{{
    "cash_position_usd": number or null,
    "cash_runway_months": number or null,
    "monthly_burn_rate_usd": number or null,
    "going_concern_warning": boolean,
    "debt_total_usd": number or null
}}

Be conservative - only extract values you are confident about.
Return ONLY valid JSON, no explanation.
"""

TRIAL_SCORE_PROMPT = """
Score this clinical trial design on a 0-100 scale.

Trial Details:
{trial_details}

Consider:
- Endpoint clarity (primary/secondary well-defined)
- Control group design (placebo, active comparator)
- Randomization and blinding
- Sample size adequacy
- Duration appropriateness

Return JSON:
{{
    "trial_design_score": number (0-100),
    "score_rationale": "brief explanation"
}}

Return ONLY valid JSON.
"""


class DualModelVerifier:
    """Cross-verify extractions between Claude and Gemini."""

    def __init__(self, db=None):
        """Initialize verifier with optional database.

        Args:
            db: SQLiteDB instance for storing verification results
        """
        self.db = db
        self._init_db()
        self._init_clients()

    def _init_db(self):
        """Lazy load database."""
        if self.db is None:
            try:
                from utils.sqlite_db import get_db
                self.db = get_db()
            except Exception as e:
                logger.warning(f"Could not initialize database: {e}")
                self.db = None

    def _init_clients(self):
        """Initialize LLM clients."""
        self.anthropic_client = None
        self.gemini_model = None

        # Claude (primary)
        if os.getenv("ANTHROPIC_API_KEY"):
            try:
                import anthropic
                self.anthropic_client = anthropic.Anthropic()
            except Exception as e:
                logger.warning(f"Could not init Anthropic client: {e}")

        # Gemini (secondary)
        if os.getenv("GOOGLE_API_KEY"):
            try:
                import google.generativeai as genai
                genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
                self.gemini_model = genai.GenerativeModel("gemini-1.5-flash")
            except Exception as e:
                logger.warning(f"Could not init Gemini client: {e}")

    def extract_and_verify(
        self,
        document: str,
        extraction_type: str,
        source_type: str,
        source_id: int,
    ) -> Dict[str, Any]:
        """Extract with primary model, verify with secondary.

        Args:
            document: Text to extract from
            extraction_type: Type of extraction (sec_financial, trial_score)
            source_type: Source table (sec_filing, trial)
            source_id: Source record ID

        Returns:
            Dict with primary result, secondary result, and verification info
        """
        # Get appropriate prompt
        if extraction_type == "sec_financial":
            prompt_template = SEC_EXTRACTION_PROMPT
        elif extraction_type == "trial_score":
            prompt_template = TRIAL_SCORE_PROMPT
        else:
            raise ValueError(f"Unknown extraction type: {extraction_type}")

        prompt = prompt_template.format(text=document[:8000], trial_details=document[:8000])

        # Primary extraction (Claude Haiku)
        primary_result = self._extract_with_claude(prompt)
        primary_model = "claude-3-5-haiku"

        # Secondary verification (Gemini Flash)
        secondary_result = self._extract_with_gemini(prompt)
        secondary_model = "gemini-1.5-flash"

        # Compare results
        comparison = self._compare_results(primary_result, secondary_result)

        # Store verification if db available
        if self.db and primary_result:
            for field, value in primary_result.items():
                secondary_value = secondary_result.get(field) if secondary_result else None
                is_match = self._values_match(value, secondary_value)

                self.db.save_verification(
                    source_type=source_type,
                    source_id=source_id,
                    field_name=field,
                    primary_model=primary_model,
                    primary_value=str(value) if value is not None else None,
                    secondary_model=secondary_model,
                    secondary_value=str(secondary_value) if secondary_value is not None else None,
                    is_match=is_match,
                    confidence_score=comparison["confidence"],
                    needs_review=not is_match and value is not None,
                )

        return {
            "primary": primary_result,
            "secondary": secondary_result,
            "match": comparison["is_match"],
            "confidence": comparison["confidence"],
            "disagreements": comparison["disagreements"],
        }

    def _extract_with_claude(self, prompt: str) -> Optional[Dict]:
        """Extract using Claude."""
        if not self.anthropic_client:
            logger.warning("Claude client not available")
            return None

        try:
            response = self.anthropic_client.messages.create(
                model="claude-3-5-haiku-20241022",
                max_tokens=500,
                messages=[{"role": "user", "content": prompt}],
            )
            return self._parse_json_response(response.content[0].text)
        except Exception as e:
            logger.error(f"Claude extraction failed: {e}")
            return None

    def _extract_with_gemini(self, prompt: str) -> Optional[Dict]:
        """Extract using Gemini."""
        if not self.gemini_model:
            logger.warning("Gemini model not available")
            return None

        try:
            response = self.gemini_model.generate_content(prompt)
            return self._parse_json_response(response.text)
        except Exception as e:
            logger.error(f"Gemini extraction failed: {e}")
            return None

    def _parse_json_response(self, text: str) -> Optional[Dict]:
        """Parse JSON from LLM response."""
        text = text.strip()

        # Handle markdown code blocks
        if "```" in text:
            match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
            if match:
                text = match.group(1)

        try:
            return json.loads(text)
        except json.JSONDecodeError as e:
            logger.warning(f"Could not parse JSON: {e}")
            return None

    def _compare_results(
        self,
        primary: Optional[Dict],
        secondary: Optional[Dict],
    ) -> Dict[str, Any]:
        """Compare two extraction results.

        Args:
            primary: Primary model result
            secondary: Secondary model result

        Returns:
            Comparison dict with is_match, confidence, disagreements
        """
        if primary is None and secondary is None:
            return {"is_match": True, "confidence": 0.0, "disagreements": []}

        if primary is None or secondary is None:
            return {
                "is_match": False,
                "confidence": 0.0,
                "disagreements": [{"field": "all", "reason": "one model failed"}],
            }

        disagreements = []

        for field in primary.keys():
            if field not in secondary:
                continue

            primary_val = primary[field]
            secondary_val = secondary[field]

            if not self._values_match(primary_val, secondary_val):
                disagreements.append({
                    "field": field,
                    "primary_value": primary_val,
                    "secondary_value": secondary_val,
                })

        # Calculate confidence based on agreement
        total_fields = len(primary)
        agreeing_fields = total_fields - len(disagreements)
        confidence = agreeing_fields / max(total_fields, 1)

        return {
            "is_match": len(disagreements) == 0,
            "confidence": confidence,
            "disagreements": disagreements,
        }

    def _values_match(self, val1: Any, val2: Any) -> bool:
        """Check if two values match (with tolerance for numbers).

        Args:
            val1: First value
            val2: Second value

        Returns:
            True if values match
        """
        if val1 is None and val2 is None:
            return True

        if val1 is None or val2 is None:
            return False

        if isinstance(val1, bool) and isinstance(val2, bool):
            return val1 == val2

        if isinstance(val1, (int, float)) and isinstance(val2, (int, float)):
            # Allow 10% tolerance for numeric values
            if val1 == 0 and val2 == 0:
                return True
            avg = (abs(val1) + abs(val2)) / 2
            if avg == 0:
                return True
            diff_pct = abs(val1 - val2) / avg
            return diff_pct < 0.10

        return str(val1).lower() == str(val2).lower()

    def verify_batch(
        self,
        extractions: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Verify a batch of extractions.

        Args:
            extractions: List of extraction dicts with document, source_type, source_id

        Returns:
            Summary of verification results
        """
        results = {
            "total": len(extractions),
            "verified": 0,
            "disagreements": 0,
            "errors": 0,
        }

        for extraction in extractions:
            try:
                result = self.extract_and_verify(
                    document=extraction.get("document", ""),
                    extraction_type=extraction.get("extraction_type", "sec_financial"),
                    source_type=extraction.get("source_type", ""),
                    source_id=extraction.get("source_id", 0),
                )

                results["verified"] += 1
                if not result["match"]:
                    results["disagreements"] += 1

            except Exception as e:
                logger.error(f"Verification error: {e}")
                results["errors"] += 1

        return results


# Singleton instance
_verifier_instance: Optional[DualModelVerifier] = None


def get_dual_verifier() -> DualModelVerifier:
    """Get singleton verifier instance."""
    global _verifier_instance
    if _verifier_instance is None:
        _verifier_instance = DualModelVerifier()
    return _verifier_instance


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    # Test verification
    verifier = get_dual_verifier()

    test_text = """
    As of December 31, 2025, we had cash and cash equivalents of $150 million.
    Based on our current burn rate of approximately $12 million per month,
    we expect our cash runway to extend through Q2 2027.
    """

    result = verifier.extract_and_verify(
        document=test_text,
        extraction_type="sec_financial",
        source_type="sec_filing",
        source_id=1,
    )

    print(f"Primary: {result['primary']}")
    print(f"Secondary: {result['secondary']}")
    print(f"Match: {result['match']}")
    print(f"Confidence: {result['confidence']}")
    print(f"Disagreements: {result['disagreements']}")
