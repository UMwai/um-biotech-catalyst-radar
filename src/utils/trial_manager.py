"""Trial management and access control."""

from datetime import datetime, timedelta, timezone

from .db import get_user_by_email as get_user
from .db import get_user_subscription, update_user


class TrialManager:
    """Manage free trial lifecycle."""

    TRIAL_DURATION_DAYS = 7

    def __init__(self, user_email: str):
        """Initialize trial manager for a user.

        Args:
            user_email: User's email address
        """
        self.user_email = user_email
        self.user = get_user(user_email)

    def is_trial_active(self) -> bool:
        """Check if user's trial is still active.

        Returns:
            True if trial is active, False otherwise
        """
        if not self.user or not self.user.get("trial_end_date"):
            return False

        trial_end = self.user["trial_end_date"]
        # Ensure both datetimes are timezone-aware or naive
        now = datetime.now(timezone.utc)
        if trial_end.tzinfo is None:
            trial_end = trial_end.replace(tzinfo=timezone.utc)

        return now < trial_end

    def is_trial_expired(self) -> bool:
        """Check if trial has expired.

        Returns:
            True if trial expired, False otherwise
        """
        if not self.user or not self.user.get("trial_end_date"):
            return False

        trial_end = self.user["trial_end_date"]
        # Ensure both datetimes are timezone-aware or naive
        now = datetime.now(timezone.utc)
        if trial_end.tzinfo is None:
            trial_end = trial_end.replace(tzinfo=timezone.utc)

        return now >= trial_end

    def has_active_subscription(self) -> bool:
        """Check if user has paid subscription.

        Returns:
            True if user has active subscription, False otherwise
        """
        if not self.user:
            return False

        # Check if trial was converted (backward compatibility)
        if self.user.get("trial_converted"):
            return True

        # Check subscriptions table
        subscription = get_user_subscription(self.user["id"])
        return subscription and subscription["status"] == "active"

    def get_days_remaining(self) -> int:
        """Get days remaining in trial.

        Returns:
            Number of days remaining (0 if expired or no trial)
        """
        if not self.user or not self.user.get("trial_end_date"):
            return 0

        trial_end = self.user["trial_end_date"]
        now = datetime.now(timezone.utc)
        if trial_end.tzinfo is None:
            trial_end = trial_end.replace(tzinfo=timezone.utc)

        diff = trial_end - now
        return max(0, diff.days)

    def get_hours_remaining(self) -> int:
        """Get hours remaining in trial.

        Returns:
            Number of hours remaining (0 if expired or no trial)
        """
        if not self.user or not self.user.get("trial_end_date"):
            return 0

        trial_end = self.user["trial_end_date"]
        now = datetime.now(timezone.utc)
        if trial_end.tzinfo is None:
            trial_end = trial_end.replace(tzinfo=timezone.utc)

        diff = trial_end - now
        return max(0, int(diff.total_seconds() / 3600))

    def start_trial(self) -> None:
        """Start trial for new user.

        Raises:
            ValueError: If user not found or trial already started
        """
        if not self.user:
            raise ValueError("User not found")

        if self.user.get("trial_start_date"):
            raise ValueError("Trial already started for this user")

        trial_start = datetime.now(timezone.utc)
        trial_end = trial_start + timedelta(days=self.TRIAL_DURATION_DAYS)

        update_user(
            self.user["id"],
            {"trial_start_date": trial_start, "trial_end_date": trial_end},
        )

        # Refresh user data
        self.user = get_user(self.user_email)

        # Trigger welcome email workflow
        from .n8n import trigger_workflow

        trigger_workflow("new_trial_user", {"user_id": self.user["id"]})

    def mark_converted(self) -> None:
        """Mark trial as converted to paid.

        Raises:
            ValueError: If user not found
        """
        if not self.user:
            raise ValueError("User not found")

        update_user(self.user["id"], {"trial_converted": True})

        # Refresh user data
        self.user = get_user(self.user_email)

    def should_show_paywall(self) -> bool:
        """Determine if paywall should be shown.

        Returns:
            True if paywall should be shown, False otherwise
        """
        # Show paywall if:
        # 1. Trial expired AND
        # 2. No active subscription
        return self.is_trial_expired() and not self.has_active_subscription()

    def get_access_level(self) -> str:
        """Get user's access level.

        Returns:
            'full' - Full access (active trial or paid)
            'preview' - Limited preview (expired trial, no payment)
            'none' - No access (not logged in)
        """
        if not self.user:
            return "none"

        if self.has_active_subscription() or self.is_trial_active():
            return "full"

        return "preview"

    def get_trial_status(self) -> dict:
        """Get complete trial status information.

        Returns:
            Dict with trial status details
        """
        return {
            "is_active": self.is_trial_active(),
            "is_expired": self.is_trial_expired(),
            "has_subscription": self.has_active_subscription(),
            "days_remaining": self.get_days_remaining(),
            "hours_remaining": self.get_hours_remaining(),
            "access_level": self.get_access_level(),
            "should_show_paywall": self.should_show_paywall(),
        }
