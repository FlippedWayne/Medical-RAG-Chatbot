"""
Medical Chatbot Evaluation Script

Run comprehensive evaluations on the Medical Chatbot RAG system using LangSmith.
"""

import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.observability.evaluation import (
    create_dataset,
    run_evaluation,
    log_evaluation_results,
    create_evaluator
)
from src.utils.logger import get_logger
from src.config.settings import settings
from langsmith import traceable

logger = get_logger(__name__)

# Configure LangSmith for evaluations
os.environ["LANGCHAIN_PROJECT"] = "medical-chatbot-evaluators"
os.environ["LANGCHAIN_TRACING_V2"] = "true"

# Get API key from environment
langsmith_api_key = os.getenv("LANGSMITH_API_KEY") or os.getenv("LANGCHAIN_API_KEY")
if langsmith_api_key:
    logger.info("✅ LangSmith API key found")
    logger.info(f"📊 Project: medical-chatbot-evaluators")
    
    # Initialize LangSmith client
    from src.observability.langsmith_config import configure_langsmith
    success = configure_langsmith(
        api_key=langsmith_api_key,
        project_name="medical-chatbot-evaluators",
        enable_tracing=True
    )
    
    if not success:
        logger.error("❌ Failed to configure LangSmith")
        logger.error("💡 Check your API key and try again")
        logger.error("💡 Get your API key from: https://smith.langchain.com/settings")
        sys.exit(1)
    
    logger.info("✅ LangSmith configured successfully")
else:
    logger.error("❌ LangSmith API key not found!")
    logger.error("💡 Set LANGSMITH_API_KEY in environment or .env file")
    logger.error("💡 Get your API key from: https://smith.langchain.com/settings")
    logger.error("")
    logger.error("Quick fix:")
    logger.error("  $env:LANGSMITH_API_KEY = 'your_api_key_here'")
    logger.error("  $env:LANGCHAIN_TRACING_V2 = 'true'")
    sys.exit(1)


# Medical Chatbot Test Examples
MEDICAL_TEST_EXAMPLES = [
    {
        "inputs": {"query": "What is diabetes?"},
        "outputs": {
            "expected_keywords": ["blood sugar", "glucose", "insulin", "chronic"],
            "category": "medical_definition"
        },
        "metadata": {"difficulty": "easy", "type": "factual"}
    },
    {
        "inputs": {"query": "What are the symptoms of diabetes?"},
        "outputs": {
            "expected_keywords": ["thirst", "urination", "hunger", "fatigue", "weight"],
            "category": "medical_symptoms"
        },
        "metadata": {"difficulty": "medium", "type": "factual"}
    },
    {
        "inputs": {"query": "How is diabetes treated?"},
        "outputs": {
            "expected_keywords": ["insulin", "medication", "diet", "exercise", "lifestyle"],
            "category": "medical_treatment"
        },
        "metadata": {"difficulty": "medium", "type": "factual"}
    },
    {
        "inputs": {"query": "Tell me about policy number 146382023"},
        "outputs": {
            "expected_keywords": ["policy", "insurance", "coverage"],
            "category": "policy_query"
        },
        "metadata": {"difficulty": "medium", "type": "document_retrieval"}
    },
    {
        "inputs": {"query": "When did Padmini Meher get vaccinated?"},
        "outputs": {
            "expected_keywords": ["Padmini Meher", "vaccination", "date"],
            "category": "personal_data_query"
        },
        "metadata": {"difficulty": "hard", "type": "specific_retrieval"}
    },
    {
        "inputs": {"query": "What is the relationship between diabetes and heart disease?"},
        "outputs": {
            "expected_keywords": ["diabetes", "heart", "cardiovascular", "risk"],
            "category": "medical_relationship"
        },
        "metadata": {"difficulty": "hard", "type": "reasoning"}
    },
    {
        "inputs": {"query": "What are the key features of Max Life Smart Secure Plus?"},
        "outputs": {
            "expected_keywords": ["Max Life", "Smart Secure Plus", "features", "benefits"],
            "category": "policy_features"
        },
        "metadata": {"difficulty": "medium", "type": "document_retrieval"}
    },
    {
        "inputs": {"query": "What are the complications of untreated diabetes?"},
        "outputs": {
            "expected_keywords": ["complications", "kidney", "nerve", "eye", "foot"],
            "category": "medical_complications"
        },
        "metadata": {"difficulty": "hard", "type": "factual"}
    },
]


# Custom Evaluators
def answer_relevance_evaluator(run, example):
    """Check if answer is relevant and not empty"""
    try:
        output = run.outputs.get("output", "") or run.outputs.get("answer", "")
        
        # Answer should be substantial
        is_relevant = len(output.strip()) > 20
        
        return {
            "key": "answer_relevance",
            "score": 1.0 if is_relevant else 0.0,
            "comment": f"Answer length: {len(output)} chars" if is_relevant else "Answer too short or empty"
        }
    except Exception as e:
        return {"key": "answer_relevance", "score": 0.0, "comment": f"Error: {e}"}


def keyword_presence_evaluator(run, example):
    """Check if expected keywords are present in the answer"""
    try:
        output = run.outputs.get("output", "") or run.outputs.get("answer", "")
        output_lower = output.lower()
        
        expected_keywords = example.outputs.get("expected_keywords", [])
        
        if not expected_keywords:
            return {"key": "keyword_presence", "score": 1.0, "comment": "No keywords to check"}
        
        # Count how many keywords are present
        present_keywords = [kw for kw in expected_keywords if kw.lower() in output_lower]
        score = len(present_keywords) / len(expected_keywords)
        
        return {
            "key": "keyword_presence",
            "score": score,
            "comment": f"{len(present_keywords)}/{len(expected_keywords)} keywords found: {present_keywords}"
        }
    except Exception as e:
        return {"key": "keyword_presence", "score": 0.0, "comment": f"Error: {e}"}


def response_length_evaluator(run, example):
    """Check if response length is appropriate"""
    try:
        output = run.outputs.get("output", "") or run.outputs.get("answer", "")
        word_count = len(output.split())
        
        # Good response: 20-500 words
        if 20 <= word_count <= 500:
            score = 1.0
            comment = f"Good length: {word_count} words"
        elif word_count < 20:
            score = 0.3
            comment = f"Too short: {word_count} words"
        else:
            score = 0.7
            comment = f"Too long: {word_count} words"
        
        return {
            "key": "response_length",
            "score": score,
            "comment": comment
        }
    except Exception as e:
        return {"key": "response_length", "score": 0.0, "comment": f"Error: {e}"}


def no_error_evaluator(run, example):
    """Check if the run completed without errors"""
    try:
        has_error = run.error is not None
        
        return {
            "key": "no_error",
            "score": 0.0 if has_error else 1.0,
            "comment": f"Error: {run.error}" if has_error else "No errors"
        }
    except Exception as e:
        return {"key": "no_error", "score": 0.0, "comment": f"Evaluation error: {e}"}


@traceable(name="create_evaluation_dataset", tags=["dataset", "setup"])
def create_medical_dataset(dataset_name: str = "medical-chatbot-test"):
    """
    Create test dataset for medical chatbot evaluation
    
    Args:
        dataset_name: Name of the dataset
        
    Returns:
        Dataset ID if successful
    """
    logger.info(f"📊 Creating dataset: {dataset_name}")
    
    dataset_id = create_dataset(
        dataset_name=dataset_name,
        examples=MEDICAL_TEST_EXAMPLES,
        description="Test dataset for Medical Chatbot RAG evaluation"
    )
    
    if dataset_id:
        logger.info(f"✅ Dataset created successfully: {dataset_id}")
        logger.info(f"📝 Total examples: {len(MEDICAL_TEST_EXAMPLES)}")
    else:
        logger.error("❌ Failed to create dataset")
    
    return dataset_id


@traceable(
    name="evaluate_chatbot_pipeline",
    metadata={"dataset": "medical-chatbot-test"},
    tags=["evaluation", "rag", "testing"]
)
def evaluate_medical_chatbot(
    rag_chain,
    dataset_name: str = "medical-chatbot-test",
    experiment_prefix: str = None
):
    """
    Run evaluation on medical chatbot
    
    Args:
        rag_chain: The RAG chain to evaluate
        dataset_name: Name of the test dataset
        experiment_prefix: Optional experiment prefix
        
    Returns:
        Evaluation results
    """
    # Generate experiment prefix if not provided
    if experiment_prefix is None:
        active_llm = settings.config.get('active_llm', 'unknown')
        experiment_prefix = f"medical_eval_{active_llm}"
    
    logger.info(f"🔬 Starting evaluation: {experiment_prefix}")
    
    # Define wrapper function for the chain
    def chain_wrapper(inputs):
        try:
            query = inputs.get("query", "")
            result = rag_chain.invoke(query)
            return {"output": result}
        except Exception as e:
            logger.error(f"Chain invocation error: {e}")
            return {"output": "", "error": str(e)}
    
    # Create evaluators
    evaluators = [
        create_evaluator("answer_relevance", answer_relevance_evaluator),
        create_evaluator("keyword_presence", keyword_presence_evaluator),
        create_evaluator("response_length", response_length_evaluator),
        create_evaluator("no_error", no_error_evaluator),
    ]
    
    # Run evaluation
    results = run_evaluation(
        dataset_name=dataset_name,
        target_function=chain_wrapper,
        evaluators=evaluators,
        experiment_prefix=experiment_prefix,
        metadata={
            "model": settings.config.get('active_llm', 'unknown'),
            "embedding_model": settings.embedding_model,
            "vectorstore_path": settings.vectorstore_path,
        }
    )
    
    if results:
        # Log results
        output_file = f"evaluation/results/eval_{experiment_prefix}_{results['experiment_name'].split('_')[-1]}.csv"
        log_evaluation_results(results, output_file=output_file)
        
        logger.info(f"✅ Evaluation completed successfully")
        logger.info(f"📊 View results at: https://smith.langchain.com/")
        
        # Log output metadata for LangSmith
        from langsmith import get_current_run_tree
        run = get_current_run_tree()
        if run:
            run.extra = run.extra or {}
            run.extra.update({
                "experiment_name": results.get('experiment_name', 'unknown'),
                "dataset_name": dataset_name,
                "num_evaluators": len(evaluators),
                "model": settings.config.get('active_llm', 'unknown'),
                "status": "success"
            })
    else:
        logger.error("❌ Evaluation failed")
        
        # Log failure metadata
        from langsmith import get_current_run_tree
        run = get_current_run_tree()
        if run:
            run.extra = run.extra or {}
            run.extra.update({
                "dataset_name": dataset_name,
                "status": "failed"
            })
    
    return results


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Evaluate Medical Chatbot")
    parser.add_argument(
        "--create-dataset",
        action="store_true",
        help="Create test dataset"
    )
    parser.add_argument(
        "--dataset-name",
        type=str,
        default="medical-chatbot-test",
        help="Name of the dataset"
    )
    parser.add_argument(
        "--run-eval",
        action="store_true",
        help="Run evaluation"
    )
    
    args = parser.parse_args()
    
    if args.create_dataset:
        create_medical_dataset(args.dataset_name)
    
    if args.run_eval:
        # Import RAG chain
        from app import get_vectorstore, initialize_llm, validate_environment, get_rag_prompt
        from langchain_core.runnables import RunnablePassthrough
        from langchain_core.output_parsers import StrOutputParser
        
        logger.info("🚀 Initializing RAG chain for evaluation...")
        
        # Initialize components
        config = validate_environment()
        vectorstore = get_vectorstore()
        llm = initialize_llm(config)
        prompt = get_rag_prompt()
        
        # Create RAG chain
        retriever = vectorstore.as_retriever(search_kwargs={"k": 3})
        
        rag_chain = (
            {"context": retriever, "input": RunnablePassthrough()}
            | prompt
            | llm
            | StrOutputParser()
        )
        
        # Run evaluation
        evaluate_medical_chatbot(rag_chain, dataset_name=args.dataset_name)
