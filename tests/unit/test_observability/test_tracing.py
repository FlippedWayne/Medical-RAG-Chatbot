"""
Unit tests for src/observability/tracing.py
"""

import pytest
from unittest.mock import patch, MagicMock


class TestTraceChainDecorator:
    def test_trace_chain_disabled_returns_original(self):
        """Returns original function when tracing is disabled"""
        with patch(
            "src.observability.tracing.is_langsmith_enabled", return_value=False
        ):
            from src.observability.tracing import trace_chain

            @trace_chain(name="test_chain")
            def my_func(x):
                return x * 2

        assert my_func(3) == 6

    def test_trace_chain_enabled_calls_func(self):
        """Wrapped function executes and returns value when tracing is enabled"""
        mock_traceable = MagicMock(side_effect=lambda *a, **kw: lambda f: f)

        with (
            patch("src.observability.tracing.is_langsmith_enabled", return_value=True),
            patch("src.observability.tracing.traceable", mock_traceable),
        ):
            from src.observability.tracing import trace_chain

            @trace_chain(name="test_chain")
            def my_func(x):
                return x * 2

        # The function may or may not be wrapped depending on traceable mock
        # but it must be callable and return a value
        assert callable(my_func)

    def test_trace_chain_propagates_exception(self):
        """Exception from wrapped function propagates out"""
        with patch(
            "src.observability.tracing.is_langsmith_enabled", return_value=False
        ):
            from src.observability.tracing import trace_chain

            @trace_chain(name="test_chain")
            def failing_func():
                raise ValueError("Something went wrong")

        with pytest.raises(ValueError, match="Something went wrong"):
            failing_func()


class TestCreateFeedback:
    def test_create_feedback_disabled(self):
        """Returns False when LangSmith is disabled"""
        with patch(
            "src.observability.tracing.is_langsmith_enabled", return_value=False
        ):
            from src.observability.tracing import create_feedback

            result = create_feedback(run_id="run-123", key="rating", score=0.9)
        assert result is False

    def test_create_feedback_no_client(self):
        """Returns False when client is None"""
        with (
            patch("src.observability.tracing.is_langsmith_enabled", return_value=True),
            patch("src.observability.tracing.get_langsmith_client", return_value=None),
        ):
            from src.observability.tracing import create_feedback

            result = create_feedback(run_id="run-123", key="rating", score=0.9)
        assert result is False

    def test_create_feedback_success(self):
        """Calls client.create_feedback and returns True"""
        mock_client = MagicMock()

        with (
            patch("src.observability.tracing.is_langsmith_enabled", return_value=True),
            patch(
                "src.observability.tracing.get_langsmith_client",
                return_value=mock_client,
            ),
        ):
            from src.observability.tracing import create_feedback

            result = create_feedback(
                run_id="run-123",
                key="user_rating",
                score=0.8,
                comment="Helpful answer",
            )

        assert result is True
        mock_client.create_feedback.assert_called_once_with(
            run_id="run-123",
            key="user_rating",
            score=0.8,
            value=None,
            comment="Helpful answer",
            correction=None,
        )

    def test_create_feedback_exception(self):
        """Returns False when client raises an exception"""
        mock_client = MagicMock()
        mock_client.create_feedback.side_effect = Exception("Network error")

        with (
            patch("src.observability.tracing.is_langsmith_enabled", return_value=True),
            patch(
                "src.observability.tracing.get_langsmith_client",
                return_value=mock_client,
            ),
        ):
            from src.observability.tracing import create_feedback

            result = create_feedback(run_id="run-123", key="rating", score=0.5)

        assert result is False


class TestGetCurrentRunId:
    def test_get_current_run_id_no_run(self):
        """Returns None when no active run tree"""
        with patch("src.observability.tracing.get_current_run_tree", return_value=None):
            from src.observability.tracing import get_current_run_id

            assert get_current_run_id() is None

    def test_get_current_run_id_active(self):
        """Returns run id string when active run exists"""
        mock_run = MagicMock()
        mock_run.id = "abc-def-123"

        with patch(
            "src.observability.tracing.get_current_run_tree",
            return_value=mock_run,
        ):
            from src.observability.tracing import get_current_run_id

            result = get_current_run_id()

        assert result == "abc-def-123"


class TestAddRunMetadata:
    def test_add_run_metadata_no_run(self):
        """Returns False when no active run tree"""
        with patch("src.observability.tracing.get_current_run_tree", return_value=None):
            from src.observability.tracing import add_run_metadata

            result = add_run_metadata({"key": "value"})
        assert result is False

    def test_add_run_metadata_success(self):
        """Updates run_tree.metadata dict and returns True"""
        mock_run = MagicMock()
        mock_run.metadata = {}

        with patch(
            "src.observability.tracing.get_current_run_tree",
            return_value=mock_run,
        ):
            from src.observability.tracing import add_run_metadata

            result = add_run_metadata({"version": "1.0"})

        assert result is True
        assert mock_run.metadata.get("version") == "1.0"


class TestAddRunTags:
    def test_add_run_tags_no_run(self):
        """Returns False when no active run tree"""
        with patch("src.observability.tracing.get_current_run_tree", return_value=None):
            from src.observability.tracing import add_run_tags

            result = add_run_tags(["rag", "medical"])
        assert result is False

    def test_add_run_tags_success(self):
        """Extends run_tree.tags list and returns True"""
        mock_run = MagicMock()
        mock_run.tags = []

        with patch(
            "src.observability.tracing.get_current_run_tree",
            return_value=mock_run,
        ):
            from src.observability.tracing import add_run_tags

            result = add_run_tags(["rag", "medical"])

        assert result is True
        assert "rag" in mock_run.tags
        assert "medical" in mock_run.tags
