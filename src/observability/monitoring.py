"""
LangSmith monitoring and analytics utilities.

This module provides tools for monitoring application performance
and analyzing traces in LangSmith.
"""

from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta
import pandas as pd

from .langsmith_config import is_langsmith_enabled, get_langsmith_client

# Use centralized logger
try:
    from ..utils.logger import get_logger

    logger = get_logger(__name__)
except ImportError:
    import logging

    logger = logging.getLogger(__name__)


def get_project_runs(
    project_name: Optional[str] = None,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    limit: int = 100,
) -> Optional[List[Dict[str, Any]]]:
    """
    Retrieve runs from a LangSmith project.

    Args:
        project_name: Project name (defaults to current project)
        start_time: Start time for filtering runs
        end_time: End time for filtering runs
        limit: Maximum number of runs to retrieve

    Returns:
        Optional[List]: List of run dictionaries
    """
    if not is_langsmith_enabled():
        logger.warning("LangSmith not enabled")
        return None

    try:
        client = get_langsmith_client()
        if not client:
            return None

        import os

        project_name = project_name or os.environ.get("LANGCHAIN_PROJECT", "default")

        runs = []
        for run in client.list_runs(
            project_name=project_name,
            start_time=start_time,
            end_time=end_time,
        ):
            if len(runs) >= limit:
                break

            runs.append(
                {
                    "id": str(run.id),
                    "name": run.name,
                    "start_time": run.start_time,
                    "end_time": run.end_time,
                    "status": run.status,
                    "error": run.error,
                    "inputs": run.inputs,
                    "outputs": run.outputs,
                    "metadata": run.extra.get("metadata", {}) if run.extra else {},
                }
            )

        logger.info(f"Retrieved {len(runs)} runs from project {project_name}")
        return runs

    except Exception as e:
        logger.error(f"Failed to get project runs: {str(e)}")
        return None


def analyze_performance(
    project_name: Optional[str] = None,
    hours: int = 24,
) -> Optional[Dict[str, Any]]:
    """
    Analyze performance metrics for recent runs.

    Args:
        project_name: Project name to analyze
        hours: Number of hours to look back

    Returns:
        Optional[Dict]: Performance metrics
    """
    if not is_langsmith_enabled():
        logger.warning("LangSmith not enabled")
        return None

    try:
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=hours)

        runs = get_project_runs(
            project_name=project_name,
            start_time=start_time,
            end_time=end_time,
            limit=1000,
        )

        if not runs:
            return None

        # Calculate metrics
        total_runs = len(runs)
        successful_runs = sum(1 for r in runs if r["status"] == "success")
        failed_runs = sum(1 for r in runs if r["status"] == "error")

        # Calculate latencies
        latencies = []
        for run in runs:
            if run["start_time"] and run["end_time"]:
                latency = (run["end_time"] - run["start_time"]).total_seconds()
                latencies.append(latency)

        metrics = {
            "total_runs": total_runs,
            "successful_runs": successful_runs,
            "failed_runs": failed_runs,
            "success_rate": successful_runs / total_runs if total_runs > 0 else 0,
            "avg_latency": sum(latencies) / len(latencies) if latencies else 0,
            "min_latency": min(latencies) if latencies else 0,
            "max_latency": max(latencies) if latencies else 0,
            "time_period_hours": hours,
        }

        logger.info(f"Performance Analysis ({hours}h):")
        logger.info(f"  Total Runs: {metrics['total_runs']}")
        logger.info(f"  Success Rate: {metrics['success_rate']:.2%}")
        logger.info(f"  Avg Latency: {metrics['avg_latency']:.2f}s")

        return metrics

    except Exception as e:
        logger.error(f"Failed to analyze performance: {str(e)}")
        return None


def get_feedback_stats(
    project_name: Optional[str] = None,
    hours: int = 24,
) -> Optional[Dict[str, Any]]:
    """
    Get feedback statistics for recent runs.

    Args:
        project_name: Project name
        hours: Number of hours to look back

    Returns:
        Optional[Dict]: Feedback statistics
    """
    if not is_langsmith_enabled():
        logger.warning("LangSmith not enabled")
        return None

    try:
        client = get_langsmith_client()
        if not client:
            return None

        import os

        project_name = project_name or os.environ.get("LANGCHAIN_PROJECT", "default")

        end_time = datetime.now()
        start_time = end_time - timedelta(hours=hours)

        # Get feedback
        feedback_list = []
        for feedback in client.list_feedback(
            project_name=project_name,
            start_time=start_time,
            end_time=end_time,
        ):
            feedback_list.append(
                {
                    "key": feedback.key,
                    "score": feedback.score,
                    "value": feedback.value,
                    "comment": feedback.comment,
                }
            )

        if not feedback_list:
            return {
                "total_feedback": 0,
                "feedback_by_key": {},
            }

        # Aggregate by key
        feedback_by_key = {}
        for fb in feedback_list:
            key = fb["key"]
            if key not in feedback_by_key:
                feedback_by_key[key] = {
                    "count": 0,
                    "scores": [],
                    "avg_score": 0,
                }

            feedback_by_key[key]["count"] += 1
            if fb["score"] is not None:
                feedback_by_key[key]["scores"].append(fb["score"])

        # Calculate averages
        for key in feedback_by_key:
            scores = feedback_by_key[key]["scores"]
            if scores:
                feedback_by_key[key]["avg_score"] = sum(scores) / len(scores)

        stats = {
            "total_feedback": len(feedback_list),
            "feedback_by_key": feedback_by_key,
            "time_period_hours": hours,
        }

        logger.info(f"Feedback Stats ({hours}h):")
        logger.info(f"  Total Feedback: {stats['total_feedback']}")
        for key, data in feedback_by_key.items():
            logger.info(
                f"  {key}: {data['count']} items, avg score: {data['avg_score']:.2f}"
            )

        return stats

    except Exception as e:
        logger.error(f"Failed to get feedback stats: {str(e)}")
        return None


def export_runs_to_csv(
    output_file: str,
    project_name: Optional[str] = None,
    hours: int = 24,
) -> bool:
    """
    Export runs to a CSV file for analysis.

    Args:
        output_file: Path to output CSV file
        project_name: Project name
        hours: Number of hours to look back

    Returns:
        bool: True if export was successful
    """
    try:
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=hours)

        runs = get_project_runs(
            project_name=project_name,
            start_time=start_time,
            end_time=end_time,
            limit=10000,
        )

        if not runs:
            logger.warning("No runs to export")
            return False

        # Convert to DataFrame
        df = pd.DataFrame(runs)

        # Calculate latency
        df["latency_seconds"] = (
            pd.to_datetime(df["end_time"]) - pd.to_datetime(df["start_time"])
        ).dt.total_seconds()

        # Save to CSV
        df.to_csv(output_file, index=False)
        logger.info(f"💾 Exported {len(runs)} runs to {output_file}")

        return True

    except Exception as e:
        logger.error(f"Failed to export runs: {str(e)}")
        return False


def get_error_summary(
    project_name: Optional[str] = None,
    hours: int = 24,
) -> Optional[Dict[str, Any]]:
    """
    Get a summary of errors from recent runs.

    Args:
        project_name: Project name
        hours: Number of hours to look back

    Returns:
        Optional[Dict]: Error summary
    """
    try:
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=hours)

        runs = get_project_runs(
            project_name=project_name,
            start_time=start_time,
            end_time=end_time,
            limit=1000,
        )

        if not runs:
            return None

        # Collect errors
        errors = {}
        for run in runs:
            if run["error"]:
                error_msg = str(run["error"])
                if error_msg not in errors:
                    errors[error_msg] = {
                        "count": 0,
                        "first_seen": run["start_time"],
                        "last_seen": run["start_time"],
                    }

                errors[error_msg]["count"] += 1
                errors[error_msg]["last_seen"] = max(
                    errors[error_msg]["last_seen"], run["start_time"]
                )

        summary = {
            "total_errors": sum(e["count"] for e in errors.values()),
            "unique_errors": len(errors),
            "errors": errors,
            "time_period_hours": hours,
        }

        logger.info(f"Error Summary ({hours}h):")
        logger.info(f"  Total Errors: {summary['total_errors']}")
        logger.info(f"  Unique Errors: {summary['unique_errors']}")

        return summary

    except Exception as e:
        logger.error(f"Failed to get error summary: {str(e)}")
        return None
