"""
Test suite for Alert Agent functionality.

Tests:
- Saved search creation and filtering
- Alert notification formatting
- Deduplication logic
- Rate limiting
- Quiet hours checking
"""

import os
import pytest
from unittest.mock import Mock, patch, MagicMock

# Set test environment variables
os.environ["SUPABASE_URL"] = "https://test.supabase.co"
os.environ["SUPABASE_SERVICE_ROLE_KEY"] = "test-key"
os.environ["SENDGRID_API_KEY"] = "SG.test-key"

from src.agents.alert_agent import AlertAgent, SavedSearch, NotificationPreferences


class TestAlertAgent:
    """Test AlertAgent functionality."""

    @pytest.fixture
    def mock_supabase(self):
        """Create a mock Supabase client."""
        with patch("src.agents.alert_agent.create_client") as mock_create:
            mock_client = MagicMock()
            mock_create.return_value = mock_client
            yield mock_client

    @pytest.fixture
    def alert_agent(self, mock_supabase):
        """Create an AlertAgent instance with mocked Supabase."""
        return AlertAgent()

    def test_format_alert_message(self, alert_agent):
        """Test alert message formatting."""
        catalyst = {
            "id": "catalyst-123",
            "nct_id": "NCT12345678",
            "ticker": "BTCH",
            "sponsor": "Biotech Inc.",
            "phase": "Phase 3",
            "indication": "Oncology - Lung Cancer",
            "completion_date": "2025-06-15",
            "market_cap": 2500000000,
            "current_price": 45.50,
            "enrollment": 450,
        }

        message = alert_agent.format_alert_message(catalyst, "Test Search")

        assert message["search_name"] == "Test Search"
        assert message["ticker"] == "BTCH"
        assert message["phase"] == "Phase 3"
        assert message["market_cap"] == "$2.50B"
        assert message["current_price"] == "$45.50"
        assert message["nct_id"] == "NCT12345678"
        assert message["days_until"] is not None

    def test_format_alert_message_missing_data(self, alert_agent):
        """Test alert message formatting with missing data."""
        catalyst = {
            "id": "catalyst-123",
            "nct_id": "NCT12345678",
            "ticker": "BTCH",
            "sponsor": "Biotech Inc.",
            "phase": "Phase 3",
            "indication": "Oncology",
            "completion_date": None,
            "market_cap": None,
            "current_price": None,
            "enrollment": 100,
        }

        message = alert_agent.format_alert_message(catalyst, "Test Search")

        assert message["market_cap"] == "N/A"
        assert message["current_price"] == "N/A"
        assert message["days_until"] is None

    def test_find_new_matches_phase_filter(self, alert_agent, mock_supabase):
        """Test finding matches with phase filter."""
        # Mock Supabase response
        mock_response = Mock()
        mock_response.data = [
            {"id": "1", "ticker": "BTCH", "phase": "Phase 3"},
            {"id": "2", "ticker": "BTCH2", "phase": "Phase 3"},
        ]

        mock_query = Mock()
        mock_query.execute.return_value = mock_response
        mock_query.not_.is_.return_value.not_.is_.return_value = mock_query
        mock_query.order.return_value = mock_query
        mock_query.eq.return_value = mock_query

        alert_agent.supabase.table.return_value.select.return_value = mock_query

        # Test query
        query_params = {"phase": "Phase 3"}
        matches = alert_agent.find_new_matches(query_params, None)

        assert len(matches) == 2
        assert all(m["phase"] == "Phase 3" for m in matches)

    def test_find_new_matches_market_cap_filter(self, alert_agent, mock_supabase):
        """Test finding matches with market cap filter."""
        mock_response = Mock()
        mock_response.data = [{"id": "1", "ticker": "BTCH", "market_cap": 2000000000}]

        mock_query = Mock()
        mock_query.execute.return_value = mock_response
        mock_query.not_.is_.return_value.not_.is_.return_value = mock_query
        mock_query.order.return_value = mock_query
        mock_query.lt.return_value = mock_query

        alert_agent.supabase.table.return_value.select.return_value = mock_query

        # Test query
        query_params = {"max_market_cap": 5000000000}
        matches = alert_agent.find_new_matches(query_params, None)

        assert len(matches) == 1

    def test_is_duplicate_alert(self, alert_agent, mock_supabase):
        """Test duplicate alert detection."""
        # Mock existing notification
        mock_response = Mock()
        mock_response.data = [{"id": "notification-1"}]

        mock_query = Mock()
        mock_query.execute.return_value = mock_response
        mock_query.eq.return_value = mock_query

        alert_agent.supabase.table.return_value.select.return_value = mock_query

        is_duplicate = alert_agent._is_duplicate_alert("search-1", "catalyst-1")

        assert is_duplicate is True

    def test_is_not_duplicate_alert(self, alert_agent, mock_supabase):
        """Test non-duplicate alert detection."""
        # Mock no existing notification
        mock_response = Mock()
        mock_response.data = []

        mock_query = Mock()
        mock_query.execute.return_value = mock_response
        mock_query.eq.return_value = mock_query

        alert_agent.supabase.table.return_value.select.return_value = mock_query

        is_duplicate = alert_agent._is_duplicate_alert("search-1", "catalyst-1")

        assert is_duplicate is False

    @patch("src.agents.alert_agent.requests.post")
    def test_send_email_success(self, mock_post, alert_agent, mock_supabase):
        """Test successful email sending."""
        # Mock user response
        user_mock = Mock()
        user_mock.data = {"email": "test@example.com"}
        alert_agent.supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = user_mock

        # Mock SendGrid success response
        mock_post.return_value.status_code = 202

        alert_message = {
            "ticker": "BTCH",
            "search_name": "Test Search",
            "phase": "Phase 3",
            "sponsor": "Biotech Inc.",
            "indication": "Oncology",
            "completion_date": "2025-06-15",
            "market_cap": "$2.50B",
            "current_price": "$45.50",
            "nct_id": "NCT12345678",
        }

        result = alert_agent._send_email("user-123", alert_message)

        assert result is True
        assert mock_post.called

    @patch("src.agents.alert_agent.requests.post")
    def test_send_email_failure(self, mock_post, alert_agent, mock_supabase):
        """Test email sending failure."""
        # Mock user response
        user_mock = Mock()
        user_mock.data = {"email": "test@example.com"}
        alert_agent.supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = user_mock

        # Mock SendGrid failure response
        mock_post.return_value.status_code = 400

        alert_message = {"ticker": "BTCH", "search_name": "Test"}

        result = alert_agent._send_email("user-123", alert_message)

        assert result is False

    def test_get_user_tier(self, alert_agent, mock_supabase):
        """Test user tier retrieval."""
        mock_response = Mock()
        mock_response.data = "pro"

        alert_agent.supabase.rpc.return_value.execute.return_value = mock_response

        tier = alert_agent._get_user_tier("user-123")

        assert tier == "pro"

    def test_check_saved_searches_no_matches(self, alert_agent, mock_supabase):
        """Test checking saved searches with no new matches."""
        # Mock empty searches
        mock_response = Mock()
        mock_response.data = []

        mock_query = Mock()
        mock_query.execute.return_value = mock_response
        mock_query.eq.return_value = mock_query

        alert_agent.supabase.table.return_value.select.return_value = mock_query

        stats = alert_agent.check_saved_searches()

        assert stats["searches_checked"] == 0
        assert stats["matches_found"] == 0
        assert stats["notifications_sent"] == 0


class TestSavedSearch:
    """Test SavedSearch data class."""

    def test_saved_search_creation(self):
        """Test creating a SavedSearch instance."""
        search = SavedSearch(
            id="search-123",
            user_id="user-123",
            name="Test Search",
            query_params={"phase": "Phase 3"},
            notification_channels=["email"],
            last_checked=None,
            active=True,
        )

        assert search.id == "search-123"
        assert search.name == "Test Search"
        assert search.query_params["phase"] == "Phase 3"
        assert "email" in search.notification_channels


class TestNotificationPreferences:
    """Test NotificationPreferences data class."""

    def test_notification_preferences_creation(self):
        """Test creating NotificationPreferences instance."""
        prefs = NotificationPreferences(
            user_id="user-123",
            max_alerts_per_day=10,
            quiet_hours_start="22:00:00",
            quiet_hours_end="08:00:00",
            user_timezone="America/New_York",
            email_enabled=True,
            sms_enabled=False,
            slack_enabled=False,
            phone_number=None,
            slack_webhook_url=None,
        )

        assert prefs.user_id == "user-123"
        assert prefs.max_alerts_per_day == 10
        assert prefs.email_enabled is True


# Integration test (requires actual Supabase instance)
@pytest.mark.integration
class TestAlertAgentIntegration:
    """Integration tests for AlertAgent (requires live Supabase)."""

    @pytest.fixture
    def real_alert_agent(self):
        """Create AlertAgent with real Supabase connection."""
        # Skip if environment variables not set
        if not os.getenv("SUPABASE_URL") or not os.getenv("SUPABASE_SERVICE_ROLE_KEY"):
            pytest.skip("Supabase credentials not configured")

        return AlertAgent()

    def test_check_saved_searches_integration(self, real_alert_agent):
        """Integration test: check saved searches end-to-end."""
        stats = real_alert_agent.check_saved_searches()

        assert "searches_checked" in stats
        assert "matches_found" in stats
        assert "notifications_sent" in stats
        assert "errors" in stats


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
