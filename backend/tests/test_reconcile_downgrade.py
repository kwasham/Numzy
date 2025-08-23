import pytest

from app.core.tasks import reconcile_pending_subscription_downgrades

def test_reconcile_task_importable():
    # Ensure actor is defined and has send method
    assert callable(reconcile_pending_subscription_downgrades)
    assert hasattr(reconcile_pending_subscription_downgrades, 'send')
