"""
LangSmith evaluation utilities.

This module provides tools for creating datasets and running evaluations
using LangSmith.
"""

from typing import Any, Dict, List, Optional, Callable
from datetime import datetime

from langsmith.schemas import Example, Run

from .langsmith_config import is_langsmith_enabled, get_langsmith_client

# Use centralized logger
try:
    from ..utils.logger import get_logger

    logger = get_logger(__name__)
except ImportError:
    import logging

    logger = logging.getLogger(__name__)


def create_dataset(
    dataset_name: str,
    examples: List[Dict[str, Any]],
    description: Optional[str] = None,
) -> Optional[str]:
    """
    Create a dataset in LangSmith for evaluation.

    Args:
        dataset_name: Name of the dataset
        examples: List of example dictionaries with 'inputs' and 'outputs' keys
        description: Optional description of the dataset

    Returns:
        Optional[str]: Dataset ID if created successfully

    Example:
        examples = [
            {
                "inputs": {"query": "What is diabetes?"},
                "outputs": {"answer": "Diabetes is a chronic disease..."}
            },
            ...
        ]
        dataset_id = create_dataset("medical_qa_test", examples)
    """
    if not is_langsmith_enabled():
        logger.warning("LangSmith not enabled, cannot create dataset")
        return None

    try:
        client = get_langsmith_client()
        if not client:
            return None

        # Create dataset
        dataset = client.create_dataset(
            dataset_name=dataset_name,
            description=description or f"Created on {datetime.now().isoformat()}",
        )

        logger.info(f"📊 Created dataset: {dataset_name}")

        # Add examples to dataset
        for example in examples:
            client.create_example(
                inputs=example.get("inputs", {}),
                outputs=example.get("outputs", {}),
                dataset_id=dataset.id,
                metadata=example.get("metadata", {}),
            )

        logger.info(f"✅ Added {len(examples)} examples to dataset {dataset_name}")
        return str(dataset.id)

    except Exception as e:
        logger.error(f"Failed to create dataset: {str(e)}")
        return None


def run_evaluation(
    dataset_name: str,
    target_function: Callable,
    evaluators: Optional[List[Callable]] = None,
    experiment_prefix: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> Optional[Dict[str, Any]]:
    """
    Run an evaluation on a dataset.

    Args:
        dataset_name: Name of the dataset to evaluate on
        target_function: Function to evaluate (takes inputs, returns outputs)
        evaluators: List of evaluator functions
        experiment_prefix: Prefix for the experiment name
        metadata: Additional metadata for the experiment

    Returns:
        Optional[Dict]: Evaluation results

    Example:
        def my_chain(inputs):
            return {"answer": chain.invoke(inputs["query"])}

        results = run_evaluation(
            dataset_name="medical_qa_test",
            target_function=my_chain,
            evaluators=[correctness_evaluator],
        )
    """
    if not is_langsmith_enabled():
        logger.warning("LangSmith not enabled, cannot run evaluation")
        return None

    try:
        from langsmith.evaluation import evaluate

        client = get_langsmith_client()
        if not client:
            return None

        # Generate experiment name
        experiment_name = (
            f"{experiment_prefix or 'eval'}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        )

        logger.info(f"🔬 Starting evaluation: {experiment_name}")
        logger.info(f"📊 Dataset: {dataset_name}")

        # Run evaluation
        results = evaluate(
            target_function,
            data=dataset_name,
            evaluators=evaluators or [],
            experiment_prefix=experiment_prefix,
            metadata=metadata or {},
        )

        logger.info(f"✅ Evaluation complete: {experiment_name}")

        return {
            "experiment_name": experiment_name,
            "results": results,
        }

    except Exception as e:
        logger.error(f"Failed to run evaluation: {str(e)}")
        return None


def log_evaluation_results(
    results: Dict[str, Any],
    output_file: Optional[str] = None,
) -> bool:
    """
    Log and optionally save evaluation results.

    Args:
        results: Evaluation results dictionary
        output_file: Optional file path to save results

    Returns:
        bool: True if logging was successful
    """
    try:
        logger.info("=" * 60)
        logger.info("EVALUATION RESULTS")
        logger.info("=" * 60)

        experiment_name = results.get("experiment_name", "Unknown")
        logger.info(f"Experiment: {experiment_name}")

        # Log summary statistics if available
        eval_results = results.get("results", {})
        if hasattr(eval_results, "to_pandas"):
            df = eval_results.to_pandas()
            logger.info(f"\nTotal examples: {len(df)}")

            # Log metric summaries
            numeric_cols = df.select_dtypes(include=["number"]).columns
            if len(numeric_cols) > 0:
                logger.info("\nMetric Summaries:")
                for col in numeric_cols:
                    mean_val = df[col].mean()
                    logger.info(f"  {col}: {mean_val:.3f}")

            # Save to file if requested
            if output_file:
                df.to_csv(output_file, index=False)
                logger.info(f"\n💾 Results saved to: {output_file}")

        logger.info("=" * 60)
        return True

    except Exception as e:
        logger.error(f"Failed to log evaluation results: {str(e)}")
        return False


def create_evaluator(
    name: str,
    evaluator_func: Callable[[Run, Example], Dict[str, Any]],
) -> Callable:
    """
    Create a custom evaluator for LangSmith.

    Args:
        name: Name of the evaluator
        evaluator_func: Function that takes (run, example) and returns evaluation dict

    Returns:
        Callable: Evaluator function

    Example:
        def check_length(run, example):
            prediction = run.outputs.get("answer", "")
            return {
                "key": "answer_length",
                "score": 1.0 if len(prediction) > 50 else 0.0,
            }

        length_evaluator = create_evaluator("length_check", check_length)
    """

    def evaluator(run: Run, example: Example) -> Dict[str, Any]:
        try:
            result = evaluator_func(run, example)
            return result
        except Exception as e:
            logger.error(f"Evaluator {name} failed: {str(e)}")
            return {"key": name, "score": 0.0, "comment": f"Error: {str(e)}"}

    evaluator.__name__ = name
    return evaluator


def get_dataset_examples(dataset_name: str) -> Optional[List[Dict[str, Any]]]:
    """
    Retrieve examples from a dataset.

    Args:
        dataset_name: Name of the dataset

    Returns:
        Optional[List]: List of examples if successful
    """
    if not is_langsmith_enabled():
        logger.warning("LangSmith not enabled")
        return None

    try:
        client = get_langsmith_client()
        if not client:
            return None

        examples = []
        for example in client.list_examples(dataset_name=dataset_name):
            examples.append(
                {
                    "inputs": example.inputs,
                    "outputs": example.outputs,
                    "metadata": example.metadata,
                }
            )

        logger.info(f"Retrieved {len(examples)} examples from {dataset_name}")
        return examples

    except Exception as e:
        logger.error(f"Failed to get dataset examples: {str(e)}")
        return None


def delete_dataset(dataset_name: str) -> bool:
    """
    Delete a dataset from LangSmith.

    Args:
        dataset_name: Name of the dataset to delete

    Returns:
        bool: True if deletion was successful
    """
    if not is_langsmith_enabled():
        logger.warning("LangSmith not enabled")
        return False

    try:
        client = get_langsmith_client()
        if not client:
            return False

        client.delete_dataset(dataset_name=dataset_name)
        logger.info(f"🗑️ Deleted dataset: {dataset_name}")
        return True

    except Exception as e:
        logger.error(f"Failed to delete dataset: {str(e)}")
        return False


def list_datasets() -> Optional[List[str]]:
    """
    List all datasets in LangSmith.

    Returns:
        Optional[List[str]]: List of dataset names
    """
    if not is_langsmith_enabled():
        logger.warning("LangSmith not enabled")
        return None

    try:
        client = get_langsmith_client()
        if not client:
            return None

        datasets = [dataset.name for dataset in client.list_datasets()]
        logger.info(f"Found {len(datasets)} datasets")
        return datasets

    except Exception as e:
        logger.error(f"Failed to list datasets: {str(e)}")
        return None
