"""Backtesting Pipeline for Extraction Accuracy.

Per spec Phase 3 Section 2.5:
- Automatically sample and re-verify extractions
- Track accuracy over time
- Alert if accuracy drops below threshold
"""

from __future__ import annotations

import logging
import random
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class BacktestPipeline:
    """Automated accuracy verification via sampling."""

    SAMPLE_RATE = 0.10  # 10% of extractions
    ACCURACY_THRESHOLD = 0.95  # 95% accuracy target

    def __init__(self, db=None):
        """Initialize backtest pipeline.

        Args:
            db: SQLiteDB instance
        """
        self.db = db
        self._init_db()

    def _init_db(self):
        """Lazy load database."""
        if self.db is None:
            try:
                from utils.sqlite_db import get_db
                self.db = get_db()
            except Exception as e:
                logger.warning(f"Could not initialize database: {e}")
                self.db = None

    def run_weekly_backtest(self) -> Dict[str, Any]:
        """Sample 10% of recent extractions and re-verify.

        Returns:
            Metrics dict with accuracy breakdown
        """
        if self.db is None:
            return {"error": "Database not available"}

        try:
            # Get extractions from past 7 days
            recent_extractions = self.db.get_recent_extractions(days=7)

            if not recent_extractions:
                logger.info("No recent extractions to backtest")
                return {"sample_size": 0, "overall_accuracy": 1.0}

            # Sample 10%
            sample_size = max(1, int(len(recent_extractions) * self.SAMPLE_RATE))
            sample = random.sample(recent_extractions, min(sample_size, len(recent_extractions)))

            results = []
            for extraction in sample:
                # Re-extract from source document
                reextracted = self._reextract(extraction)

                # Compare with stored value
                comparison = self._compare(extraction, reextracted)
                results.append(comparison)

            # Calculate accuracy metrics
            metrics = self._calculate_metrics(results)

            # Save backtest run
            run_id = self.db.save_backtest_run(
                sample_size=len(sample),
                overall_accuracy=metrics["overall_accuracy"],
                sec_accuracy=metrics.get("sec_accuracy"),
                trial_accuracy=metrics.get("trial_accuracy"),
                fda_accuracy=metrics.get("fda_accuracy"),
                alert_sent=metrics["overall_accuracy"] < self.ACCURACY_THRESHOLD,
            )

            # Save individual results
            for result in results:
                self.db.save_backtest_result(
                    run_id=run_id,
                    source_type=result.get("source_type", ""),
                    source_id=result.get("source_id", 0),
                    field_name=result.get("field_name", ""),
                    original_value=str(result.get("original_value", "")),
                    reextracted_value=str(result.get("reextracted_value", "")),
                    is_match=result.get("is_match", False),
                )

            # Alert if below threshold
            if metrics["overall_accuracy"] < self.ACCURACY_THRESHOLD:
                self._send_accuracy_alert(metrics)

            logger.info(
                f"Backtest complete: {len(sample)} samples, "
                f"{metrics['overall_accuracy']:.1%} accuracy"
            )

            return metrics

        except Exception as e:
            logger.error(f"Backtest failed: {e}")
            return {"error": str(e)}

    def _reextract(self, extraction: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Re-extract values from source document.

        Args:
            extraction: Original extraction record

        Returns:
            Re-extracted values or None
        """
        source_type = extraction.get("source_type")
        raw_text = extraction.get("raw_text")

        if not raw_text:
            logger.warning(f"No raw text for extraction {extraction.get('id')}")
            return None

        try:
            from utils.dual_verify import get_dual_verifier

            verifier = get_dual_verifier()

            if source_type == "sec_filing":
                result = verifier.extract_and_verify(
                    document=raw_text[:8000],
                    extraction_type="sec_financial",
                    source_type=source_type,
                    source_id=extraction.get("id", 0),
                )
                return result.get("primary")

            elif source_type == "trial":
                result = verifier.extract_and_verify(
                    document=raw_text[:8000],
                    extraction_type="trial_score",
                    source_type=source_type,
                    source_id=extraction.get("id", 0),
                )
                return result.get("primary")

        except Exception as e:
            logger.error(f"Re-extraction failed: {e}")

        return None

    def _compare(
        self,
        original: Dict[str, Any],
        reextracted: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Compare original and re-extracted values.

        Args:
            original: Original extraction
            reextracted: Re-extracted values

        Returns:
            Comparison result
        """
        result = {
            "source_type": original.get("source_type"),
            "source_id": original.get("id"),
            "comparisons": [],
        }

        if reextracted is None:
            result["error"] = "re-extraction failed"
            result["is_match"] = False
            return result

        # Compare relevant fields based on source type
        source_type = original.get("source_type")

        if source_type == "sec_filing":
            fields_to_compare = [
                ("cash_runway_months", "cash_runway_months"),
                ("cash_position_usd", "cash_position_usd"),
                ("monthly_burn_rate_usd", "monthly_burn_rate_usd"),
            ]
        elif source_type == "trial":
            fields_to_compare = [
                ("trial_design_score", "trial_design_score"),
            ]
        else:
            fields_to_compare = []

        matches = 0
        total = 0

        for orig_field, reext_field in fields_to_compare:
            orig_val = original.get(orig_field)
            reext_val = reextracted.get(reext_field)

            if orig_val is None:
                continue

            total += 1
            is_match = self._values_match(orig_val, reext_val)

            if is_match:
                matches += 1

            result["comparisons"].append({
                "field_name": orig_field,
                "original_value": orig_val,
                "reextracted_value": reext_val,
                "is_match": is_match,
            })

        result["is_match"] = matches == total if total > 0 else True
        result["match_rate"] = matches / total if total > 0 else 1.0

        return result

    def _values_match(self, val1: Any, val2: Any) -> bool:
        """Check if values match with tolerance."""
        if val1 is None and val2 is None:
            return True

        if val1 is None or val2 is None:
            return False

        if isinstance(val1, (int, float)) and isinstance(val2, (int, float)):
            # 10% tolerance
            if val1 == 0 and val2 == 0:
                return True
            avg = (abs(val1) + abs(val2)) / 2
            if avg == 0:
                return True
            diff_pct = abs(val1 - val2) / avg
            return diff_pct < 0.10

        return str(val1) == str(val2)

    def _calculate_metrics(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate accuracy metrics from results.

        Args:
            results: List of comparison results

        Returns:
            Metrics dict
        """
        metrics = {
            "sample_size": len(results),
            "overall_accuracy": 0.0,
            "sec_accuracy": None,
            "trial_accuracy": None,
            "fda_accuracy": None,
            "error_count": 0,
        }

        if not results:
            return metrics

        # Overall accuracy
        successful = [r for r in results if "error" not in r]
        if successful:
            matching = sum(1 for r in successful if r.get("is_match", False))
            metrics["overall_accuracy"] = matching / len(successful)

        # By source type
        sec_results = [r for r in successful if r.get("source_type") == "sec_filing"]
        if sec_results:
            matching = sum(1 for r in sec_results if r.get("is_match", False))
            metrics["sec_accuracy"] = matching / len(sec_results)

        trial_results = [r for r in successful if r.get("source_type") == "trial"]
        if trial_results:
            matching = sum(1 for r in trial_results if r.get("is_match", False))
            metrics["trial_accuracy"] = matching / len(trial_results)

        # Error count
        metrics["error_count"] = len([r for r in results if "error" in r])

        return metrics

    def _send_accuracy_alert(self, metrics: Dict[str, Any]) -> None:
        """Send alert when accuracy drops below threshold.

        Args:
            metrics: Accuracy metrics
        """
        logger.warning(
            f"ACCURACY ALERT: Overall accuracy {metrics['overall_accuracy']:.1%} "
            f"is below threshold {self.ACCURACY_THRESHOLD:.1%}"
        )

        # TODO: Send email notification
        # For now, just log it

    def get_accuracy_trend(self, days: int = 30) -> List[Dict[str, Any]]:
        """Get accuracy trend over time.

        Args:
            days: Number of days to look back

        Returns:
            List of daily accuracy metrics
        """
        if self.db is None:
            return []

        return self.db.get_backtest_accuracy_trend(days=days)

    def get_recent_runs(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent backtest runs.

        Args:
            limit: Max number of runs to return

        Returns:
            List of backtest run dicts
        """
        if self.db is None:
            return []

        return self.db.get_recent_backtest_runs(limit=limit)


# Singleton instance
_pipeline_instance: Optional[BacktestPipeline] = None


def get_backtest_pipeline() -> BacktestPipeline:
    """Get singleton pipeline instance."""
    global _pipeline_instance
    if _pipeline_instance is None:
        _pipeline_instance = BacktestPipeline()
    return _pipeline_instance


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    # Test backtest
    pipeline = get_backtest_pipeline()
    metrics = pipeline.run_weekly_backtest()
    print(f"Backtest results: {metrics}")
