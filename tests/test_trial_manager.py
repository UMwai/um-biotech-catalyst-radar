"""Tests for trial management system."""

import sys
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest

# Mock psycopg2 before importing trial_manager
sys.modules["psycopg2"] = MagicMock()
sys.modules["psycopg2.pool"] = MagicMock()
sys.modules["psycopg2.extras"] = MagicMock()

# Set environment variable to prevent database init on import
import os

os.environ["LAZY_DB_INIT"] = "true"

from src.utils.trial_manager import TrialManager


@pytest.fixture
def mock_user_trial_active():
    """Mock user with active trial."""
    trial_start = datetime.now(timezone.utc) - timedelta(days=3)
    trial_end = trial_start + timedelta(days=7)
    return {
        "id": "test-user-id-1",
        "email": "test@example.com",
        "created_at": trial_start,
        "trial_start_date": trial_start,
        "trial_end_date": trial_end,
        "trial_converted": False,
        "stripe_customer_id": None,
        "onboarding_completed": False,
    }


@pytest.fixture
def mock_user_trial_expired():
    """Mock user with expired trial."""
    trial_start = datetime.now(timezone.utc) - timedelta(days=8)
    trial_end = trial_start + timedelta(days=7)
    return {
        "id": "test-user-id-2",
        "email": "expired@example.com",
        "created_at": trial_start,
        "trial_start_date": trial_start,
        "trial_end_date": trial_end,
        "trial_converted": False,
        "stripe_customer_id": None,
        "onboarding_completed": False,
    }


@pytest.fixture
def mock_subscription_active():
    """Mock active subscription."""
    return {
        "id": "sub-123",
        "user_id": "test-user-id-2",
        "stripe_subscription_id": "sub_test123",
        "status": "active",
        "plan_id": "monthly",
        "current_period_end": datetime.now(timezone.utc) + timedelta(days=30),
    }


def test_trial_active_day_3(mock_user_trial_active):
    """Test trial is active on day 3."""
    with patch("src.utils.trial_manager.get_user", return_value=mock_user_trial_active):
        with patch("src.utils.trial_manager.get_user_subscription", return_value=None):
            trial_mgr = TrialManager("test@example.com")

            # Assertions
            assert trial_mgr.is_trial_active() is True
            assert trial_mgr.is_trial_expired() is False
            # Allow for 3-4 days due to timing precision
            assert trial_mgr.get_days_remaining() in [3, 4]
            assert trial_mgr.get_access_level() == "full"
            assert trial_mgr.should_show_paywall() is False


def test_trial_expired_day_8(mock_user_trial_expired):
    """Test trial is expired on day 8."""
    with patch("src.utils.trial_manager.get_user", return_value=mock_user_trial_expired):
        with patch("src.utils.trial_manager.get_user_subscription", return_value=None):
            trial_mgr = TrialManager("expired@example.com")

            # Assertions
            assert trial_mgr.is_trial_active() is False
            assert trial_mgr.is_trial_expired() is True
            assert trial_mgr.get_days_remaining() == 0
            assert trial_mgr.get_access_level() == "preview"
            assert trial_mgr.should_show_paywall() is True


def test_converted_trial_no_paywall(mock_user_trial_expired, mock_subscription_active):
    """Test converted trial doesn't show paywall."""
    # User with expired trial but has active subscription
    with patch("src.utils.trial_manager.get_user", return_value=mock_user_trial_expired):
        with patch(
            "src.utils.trial_manager.get_user_subscription",
            return_value=mock_subscription_active,
        ):
            trial_mgr = TrialManager("expired@example.com")

            # Assertions
            assert trial_mgr.is_trial_expired() is True
            assert trial_mgr.has_active_subscription() is True
            assert trial_mgr.should_show_paywall() is False
            assert trial_mgr.get_access_level() == "full"


def test_trial_last_day():
    """Test trial on last day (showing hours)."""
    trial_start = datetime.now(timezone.utc) - timedelta(days=6, hours=12)
    trial_end = trial_start + timedelta(days=7)
    mock_user = {
        "id": "test-user-id-3",
        "email": "lastday@example.com",
        "trial_start_date": trial_start,
        "trial_end_date": trial_end,
        "trial_converted": False,
    }

    with patch("src.utils.trial_manager.get_user", return_value=mock_user):
        with patch("src.utils.trial_manager.get_user_subscription", return_value=None):
            trial_mgr = TrialManager("lastday@example.com")

            # Assertions
            assert trial_mgr.is_trial_active() is True
            assert trial_mgr.get_days_remaining() == 0  # Less than 1 day
            # Allow for 11-12 hours due to timing precision
            assert trial_mgr.get_hours_remaining() in [11, 12]
            assert trial_mgr.should_show_paywall() is False


def test_start_trial():
    """Test starting a trial for a new user."""
    mock_user = {
        "id": "test-user-id-4",
        "email": "newuser@example.com",
        "trial_start_date": None,
        "trial_end_date": None,
        "trial_converted": False,
    }

    with patch("src.utils.trial_manager.get_user", return_value=mock_user):
        with patch("src.utils.trial_manager.update_user") as mock_update:
            with patch("src.utils.trial_manager.get_user_subscription", return_value=None):
                trial_mgr = TrialManager("newuser@example.com")
                trial_mgr.start_trial()

                # Verify update_user was called
                assert mock_update.called
                call_args = mock_update.call_args
                assert call_args[0][0] == "test-user-id-4"  # user_id
                assert "trial_start_date" in call_args[0][1]
                assert "trial_end_date" in call_args[0][1]


def test_start_trial_already_started():
    """Test that starting a trial twice raises an error."""
    trial_start = datetime.now(timezone.utc)
    trial_end = trial_start + timedelta(days=7)
    mock_user = {
        "id": "test-user-id-5",
        "email": "existing@example.com",
        "trial_start_date": trial_start,
        "trial_end_date": trial_end,
        "trial_converted": False,
    }

    with patch("src.utils.trial_manager.get_user", return_value=mock_user):
        trial_mgr = TrialManager("existing@example.com")

        # Try to start trial again - should raise error
        with pytest.raises(ValueError, match="Trial already started"):
            trial_mgr.start_trial()


def test_no_user():
    """Test trial manager with non-existent user."""
    with patch("src.utils.trial_manager.get_user", return_value=None):
        trial_mgr = TrialManager("nonexistent@example.com")

        # All checks should return False/0/none for non-existent user
        assert trial_mgr.is_trial_active() is False
        assert trial_mgr.is_trial_expired() is False
        assert trial_mgr.has_active_subscription() is False
        assert trial_mgr.get_days_remaining() == 0
        assert trial_mgr.get_hours_remaining() == 0
        assert trial_mgr.get_access_level() == "none"
        assert trial_mgr.should_show_paywall() is False


def test_trial_status_summary(mock_user_trial_active):
    """Test get_trial_status returns complete information."""
    with patch("src.utils.trial_manager.get_user", return_value=mock_user_trial_active):
        with patch("src.utils.trial_manager.get_user_subscription", return_value=None):
            trial_mgr = TrialManager("test@example.com")
            status = trial_mgr.get_trial_status()

            # Verify all fields are present
            assert "is_active" in status
            assert "is_expired" in status
            assert "has_subscription" in status
            assert "days_remaining" in status
            assert "hours_remaining" in status
            assert "access_level" in status
            assert "should_show_paywall" in status

            # Verify values (day 3 of trial)
            assert status["is_active"] is True
            assert status["is_expired"] is False
            # Allow for 3-4 days due to timing precision
            assert status["days_remaining"] in [3, 4]
            assert status["access_level"] == "full"


def test_mark_converted():
    """Test marking trial as converted."""
    mock_user = {
        "id": "test-user-id-6",
        "email": "convert@example.com",
        "trial_converted": False,
    }

    with patch("src.utils.trial_manager.get_user", return_value=mock_user):
        with patch("src.utils.trial_manager.update_user") as mock_update:
            trial_mgr = TrialManager("convert@example.com")
            trial_mgr.mark_converted()

            # Verify update_user was called with trial_converted=True
            assert mock_update.called
            call_args = mock_update.call_args
            assert call_args[0][0] == "test-user-id-6"
            assert call_args[0][1]["trial_converted"] is True
