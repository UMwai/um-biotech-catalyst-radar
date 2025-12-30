"""Tests for ClinicalTrials.gov scraper."""

import pytest
from unittest.mock import patch

from src.data.scraper import ClinicalTrialsScraper


class TestClinicalTrialsScraper:
    """Test ClinicalTrialsScraper class."""

    @pytest.fixture
    def scraper(self):
        """Create a scraper instance."""
        return ClinicalTrialsScraper(months_ahead=3)

    def test_extract_phase_phase3(self, scraper):
        """Test phase extraction for Phase 3."""
        result = scraper._extract_phase(["PHASE3"])
        assert result == "Phase 3"

    def test_extract_phase_phase2(self, scraper):
        """Test phase extraction for Phase 2."""
        result = scraper._extract_phase(["PHASE2"])
        assert result == "Phase 2"

    def test_extract_phase_both(self, scraper):
        """Test phase extraction with both phases (should return highest)."""
        result = scraper._extract_phase(["PHASE2", "PHASE3"])
        assert result == "Phase 3"

    def test_extract_phase_unknown(self, scraper):
        """Test phase extraction with unknown phase."""
        result = scraper._extract_phase(["PHASE1"])
        assert result == "Unknown"

    def test_extract_phase_empty(self, scraper):
        """Test phase extraction with empty list."""
        result = scraper._extract_phase([])
        assert result == "Unknown"

    @patch("src.data.scraper.requests.get")
    def test_parse_response_empty(self, mock_get, scraper):
        """Test parsing empty API response."""
        result = scraper._parse_response({"studies": []})
        assert result.empty

    @patch("src.data.scraper.requests.get")
    def test_parse_response_with_data(self, mock_get, scraper):
        """Test parsing API response with study data."""
        mock_response = {
            "studies": [
                {
                    "protocolSection": {
                        "identificationModule": {
                            "nctId": "NCT12345678",
                            "briefTitle": "Test Study",
                        },
                        "sponsorCollaboratorsModule": {"leadSponsor": {"name": "Test Pharma Inc"}},
                        "designModule": {"phases": ["PHASE3"]},
                        "statusModule": {"primaryCompletionDateStruct": {"date": "2025-03-15"}},
                        "conditionsModule": {"conditions": ["Cancer", "Tumor"]},
                    }
                }
            ]
        }

        result = scraper._parse_response(mock_response)

        assert len(result) == 1
        assert result.iloc[0]["nct_id"] == "NCT12345678"
        assert result.iloc[0]["sponsor"] == "Test Pharma Inc"
        assert result.iloc[0]["phase"] == "Phase 3"
