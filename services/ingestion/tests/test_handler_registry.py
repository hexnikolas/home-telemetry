"""
Tests for handler registry and model lookup
"""
import pytest
from app.handlers import get_handler, MODEL_HANDLERS


class TestHandlerRegistry:
    """Test handler registry and lookup"""

    def test_model_handlers_exists(self):
        """Test that MODEL_HANDLERS registry exists"""
        assert MODEL_HANDLERS is not None
        assert isinstance(MODEL_HANDLERS, dict)

    def test_sht40_handler_registered(self):
        """Test that SHT40 handler is registered"""
        assert "SHT40" in MODEL_HANDLERS
        assert MODEL_HANDLERS["SHT40"] is not None

    def test_a1t_handler_registered(self):
        """Test that A1T handler is registered"""
        assert "A1T" in MODEL_HANDLERS
        assert MODEL_HANDLERS["A1T"] is not None

    def test_get_handler_returns_sht40(self):
        """Test get_handler returns SHT40 handler"""
        handler = get_handler("SHT40")
        assert handler is not None
        assert callable(handler)

    def test_get_handler_returns_a1t(self):
        """Test get_handler returns A1T handler"""
        handler = get_handler("A1T")
        assert handler is not None
        assert callable(handler)

    def test_get_handler_returns_none_for_unknown_model(self):
        """Test get_handler returns None for unknown model"""
        handler = get_handler("UNKNOWN_MODEL")
        assert handler is None

    def test_get_handler_case_sensitive(self):
        """Test that get_handler is case-sensitive"""
        handler1 = get_handler("SHT40")
        handler2 = get_handler("sht40")  # lowercase
        
        assert handler1 is not None
        assert handler2 is None  # Case mismatch

    def test_handlers_are_callable(self):
        """Test that all registered handlers are callable"""
        for model_name, handler in MODEL_HANDLERS.items():
            assert callable(handler), f"Handler for {model_name} is not callable"
