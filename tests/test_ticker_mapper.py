"""Tests for ticker mapping functionality."""

import pytest

from src.data.ticker_mapper import TickerMapper


class TestTickerMapper:
    """Test TickerMapper class."""

    @pytest.fixture
    def mapper(self):
        """Create a TickerMapper instance."""
        return TickerMapper()

    def test_manual_mappings_exact(self, mapper):
        """Test exact matches from manual mappings."""
        ticker, score = mapper.map_sponsor_to_ticker("Pfizer")
        assert ticker == "PFE"
        assert score == 100

    def test_manual_mappings_partial(self, mapper):
        """Test partial matches from manual mappings."""
        ticker, score = mapper.map_sponsor_to_ticker("Eli Lilly and Company, Inc.")
        assert ticker == "LLY"
        assert score == 100

    def test_manual_mappings_case_insensitive(self, mapper):
        """Test case insensitivity in manual mappings."""
        ticker, score = mapper.map_sponsor_to_ticker("MODERNA")
        assert ticker == "MRNA"
        assert score == 100

    def test_empty_sponsor(self, mapper):
        """Test handling of empty sponsor name."""
        ticker, score = mapper.map_sponsor_to_ticker("")
        assert ticker is None
        assert score == 0

    def test_none_sponsor(self, mapper):
        """Test handling of None sponsor name."""
        ticker, score = mapper.map_sponsor_to_ticker(None)
        assert ticker is None
        assert score == 0

    def test_unknown_sponsor(self, mapper):
        """Test handling of unknown sponsor."""
        ticker, score = mapper.map_sponsor_to_ticker("Random Unknown Company XYZ123")
        # Should return None or low-confidence match
        if ticker is None:
            assert score == 0
        else:
            assert score >= 80  # If matched, should meet threshold

    def test_map_all_dataframe(self, mapper):
        """Test batch mapping of DataFrame."""
        import pandas as pd

        df = pd.DataFrame(
            {
                "sponsor": ["Pfizer", "Moderna", "Unknown Corp"],
                "trial_id": ["NCT001", "NCT002", "NCT003"],
            }
        )

        result = mapper.map_all(df)

        assert "ticker" in result.columns
        assert "match_score" in result.columns
        assert result.iloc[0]["ticker"] == "PFE"
        assert result.iloc[1]["ticker"] == "MRNA"
