"""
LangSmith tracing utilities.

This module provides decorators and utilities for tracing LangChain
operations with LangSmith.
"""

from typing import Any, Dict, List, Optional, Callable
from functools import wraps
from datetime import datetime
from langsmith import traceable
from langsmith.run_helpers import get_current_run_tree

from .langsmith_config import is_langsmith_enabled, get_langsmith_client

# Use centralized logger
try:
    from ..utils.logger import get_logger

    logger = get_logger(__name__)
except ImportError:
    import logging

    logger = logging.getLogger(__name__)


def trace_chain(
    name: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
    tags: Optional[List[str]] = None,
):
    """
    Decorator to trace a LangChain chain execution.

    Args:
        name: Custom name for the trace (defaults to function name)
        metadata: Additional metadata to attach to the trace
        tags: Tags for categorizing the trace

    Example:
        @trace_chain(name="medical_rag_chain", tags=["rag", "medical"])
        def run_medical_chain(query: str):
            return chain.invoke(query)
    """

    def decorator(func: Callable):
        if not is_langsmith_enabled():
            # Return original function if tracing is disabled
            return func

        @traceable(
            name=name or func.__name__,
            metadata=metadata or {},
            tags=tags or [],
        )
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                result = func(*args, **kwargs)
                return result
            except Exception as e:
                logger.error(f"Error in traced function {func.__name__}: {str(e)}")
                raise

        return wrapper

    return decorator


def trace_retrieval(
    name: str = "retrieval",
    metadata: Optional[Dict[str, Any]] = None,
):
    """
    Decorator specifically for tracing retrieval operations.

    Args:
        name: Name for the retrieval trace
        metadata: Additional metadata

    Example:
        @trace_retrieval(name="medical_doc_retrieval")
        def retrieve_documents(query: str):
            return retriever.get_relevant_documents(query)
    """

    def decorator(func: Callable):
        if not is_langsmith_enabled():
            return func

        @traceable(
            name=name,
            metadata={**(metadata or {}), "operation_type": "retrieval"},
            tags=["retrieval"],
        )
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = datetime.now()

            try:
                result = func(*args, **kwargs)

                # Log retrieval metrics
                if hasattr(result, "__len__"):
                    logger.info(f"Retrieved {len(result)} documents")

                return result

            except Exception as e:
                logger.error(f"Retrieval error: {str(e)}")
                raise
            finally:
                duration = (datetime.now() - start_time).total_seconds()
                logger.debug(f"Retrieval took {duration:.2f}s")

        return wrapper

    return decorator


def trace_llm_call(
    name: str = "llm_call",
    metadata: Optional[Dict[str, Any]] = None,
):
    """
    Decorator for tracing LLM API calls.

    Args:
        name: Name for the LLM call trace
        metadata: Additional metadata

    Example:
        @trace_llm_call(name="medical_answer_generation")
        def generate_answer(prompt: str):
            return llm.invoke(prompt)
    """

    def decorator(func: Callable):
        if not is_langsmith_enabled():
            return func

        @traceable(
            name=name,
            metadata={**(metadata or {}), "operation_type": "llm_call"},
            tags=["llm"],
        )
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = datetime.now()

            try:
                result = func(*args, **kwargs)

                # Log token usage if available
                if hasattr(result, "usage_metadata"):
                    usage = result.usage_metadata
                    logger.info(
                        f"Token usage - Input: {usage.get('input_tokens', 0)}, "
                        f"Output: {usage.get('output_tokens', 0)}"
                    )

                return result

            except Exception as e:
                logger.error(f"LLM call error: {str(e)}")
                raise
            finally:
                duration = (datetime.now() - start_time).total_seconds()
                logger.debug(f"LLM call took {duration:.2f}s")

        return wrapper

    return decorator


def create_feedback(
    run_id: str,
    key: str,
    score: Optional[float] = None,
    value: Optional[Any] = None,
    comment: Optional[str] = None,
    correction: Optional[Dict[str, Any]] = None,
) -> bool:
    """
    Create feedback for a specific run in LangSmith.

    Args:
        run_id: The run ID to attach feedback to
        key: Feedback key (e.g., "user_rating", "correctness")
        score: Numerical score (0.0 to 1.0)
        value: Any value associated with the feedback
        comment: Text comment
        correction: Correction data

    Returns:
        bool: True if feedback was created successfully

    Example:
        create_feedback(
            run_id=run_id,
            key="user_rating",
            score=0.8,
            comment="Helpful answer"
        )
    """
    if not is_langsmith_enabled():
        logger.debug("LangSmith not enabled, skipping feedback creation")
        return False

    try:
        client = get_langsmith_client()
        if not client:
            return False

        client.create_feedback(
            run_id=run_id,
            key=key,
            score=score,
            value=value,
            comment=comment,
            correction=correction,
        )

        logger.info(f"✅ Feedback created for run {run_id}: {key}={score or value}")
        return True

    except Exception as e:
        logger.error(f"Failed to create feedback: {str(e)}")
        return False


def get_current_run_id() -> Optional[str]:
    """
    Get the current run ID from the active trace.

    Returns:
        Optional[str]: Current run ID if available
    """
    try:
        run_tree = get_current_run_tree()
        if run_tree:
            return str(run_tree.id)
    except Exception as e:
        logger.debug(f"Could not get current run ID: {str(e)}")

    return None


def add_run_metadata(metadata: Dict[str, Any]) -> bool:
    """
    Add metadata to the current run.

    Args:
        metadata: Dictionary of metadata to add

    Returns:
        bool: True if metadata was added successfully
    """
    try:
        run_tree = get_current_run_tree()
        if run_tree:
            run_tree.metadata.update(metadata)
            logger.debug(f"Added metadata to run: {metadata}")
            return True
    except Exception as e:
        logger.debug(f"Could not add run metadata: {str(e)}")

    return False


def add_run_tags(tags: List[str]) -> bool:
    """
    Add tags to the current run.

    Args:
        tags: List of tags to add

    Returns:
        bool: True if tags were added successfully
    """
    try:
        run_tree = get_current_run_tree()
        if run_tree:
            run_tree.tags.extend(tags)
            logger.debug(f"Added tags to run: {tags}")
            return True
    except Exception as e:
        logger.debug(f"Could not add run tags: {str(e)}")

    return False
