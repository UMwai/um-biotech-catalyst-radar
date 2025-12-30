"""Agent module for Biotech Catalyst Radar."""

# Import agents with try-except to handle missing dependencies gracefully
__all__ = []

try:
    from .explainer_agent import ExplainerAgent

    __all__.append("ExplainerAgent")
except ImportError as e:
    print(f"Warning: Could not import ExplainerAgent: {e}")

try:
    from .catalyst_agent import CatalystAgent

    __all__.append("CatalystAgent")
except ImportError as e:
    print(f"Warning: Could not import CatalystAgent: {e}")

try:
    from .alert_agent import AlertAgent

    __all__.append("AlertAgent")
except ImportError as e:
    print(f"Warning: Could not import AlertAgent: {e}")
