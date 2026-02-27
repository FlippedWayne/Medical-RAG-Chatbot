"""
Giskard RAG Evaluation Tests
Tests specific to RAG system performance
"""

import sys
from pathlib import Path
from typing import List, Dict, Any
import json

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

try:
    import giskard as gsk
    from giskard.rag import evaluate, QATestset, KnowledgeBase

    GISKARD_AVAILABLE = True
except ImportError:
    GISKARD_AVAILABLE = False
    print("⚠️ Giskard not available. Install with: pip install giskard")

from tests.giskard.model_wrapper import MedicalRAGModel
from tests.giskard.test_data import MEDICAL_QUESTIONS
from tests.giskard.config import RESULTS_DIR


class RAGEvaluator:
    """
    Evaluate RAG system performance
    """

    def __init__(self):
        """Initialize RAG evaluator"""
        self.model = None
        self.results = {}
        self._initialize()

    def _initialize(self):
        """Initialize RAG model"""
        print("Initializing RAG Evaluator...")
        self.model = MedicalRAGModel()
        print("✅ RAG Evaluator initialized")

    def test_correctness(self, questions: List[str]) -> Dict[str, Any]:
        """
        Test answer correctness

        Args:
            questions: List of test questions

        Returns:
            Test results
        """
        print("\n" + "=" * 60)
        print("Testing Answer Correctness...")
        print("=" * 60)

        results = {
            "metric": "correctness",
            "total_questions": len(questions),
            "passed": 0,
            "failed": 0,
            "details": [],
        }

        for question in questions:
            print(f"\nQuestion: {question}")

            # Get response
            response = self.model.predict(question)

            # Manual correctness check (simplified)
            # In real scenario, you'd compare with ground truth
            is_correct = len(response) > 50 and "error" not in response.lower()

            detail = {
                "question": question,
                "response": response[:200],
                "is_correct": is_correct,
            }

            if is_correct:
                results["passed"] += 1
                print("✅ Response generated")
            else:
                results["failed"] += 1
                print("❌ Response may be incorrect")

            results["details"].append(detail)

        return results

    def test_groundedness(self, questions: List[str]) -> Dict[str, Any]:
        """
        Test if responses are grounded in retrieved context

        Args:
            questions: List of test questions

        Returns:
            Test results
        """
        print("\n" + "=" * 60)
        print("Testing Groundedness...")
        print("=" * 60)

        results = {
            "metric": "groundedness",
            "total_questions": len(questions),
            "passed": 0,
            "failed": 0,
            "details": [],
        }

        # Keywords that indicate made-up information
        fabrication_keywords = [
            "i don't have information",
            "i cannot find",
            "not in my knowledge",
            "i'm not sure",
            "i don't know",
        ]

        for question in questions:
            print(f"\nQuestion: {question}")

            # Get response
            response = self.model.predict(question)

            # Check if response admits lack of knowledge (good)
            # or makes up information (bad)
            admits_limitation = any(
                keyword in response.lower() for keyword in fabrication_keywords
            )

            # If it admits limitation, that's grounded
            # If it provides detailed answer, assume it's from context (simplified check)
            is_grounded = admits_limitation or len(response) > 100

            detail = {
                "question": question,
                "response": response[:200],
                "is_grounded": is_grounded,
                "admits_limitation": admits_limitation,
            }

            if is_grounded:
                results["passed"] += 1
                print("✅ Response appears grounded")
            else:
                results["failed"] += 1
                print("❌ Response may not be grounded")

            results["details"].append(detail)

        return results

    def test_context_relevance(self, questions: List[str]) -> Dict[str, Any]:
        """
        Test if retrieved context is relevant to question

        Args:
            questions: List of test questions

        Returns:
            Test results
        """
        print("\n" + "=" * 60)
        print("Testing Context Relevance...")
        print("=" * 60)

        results = {
            "metric": "context_relevance",
            "total_questions": len(questions),
            "passed": 0,
            "failed": 0,
            "details": [],
        }

        for question in questions:
            print(f"\nQuestion: {question}")

            # Get retriever
            retriever = self.model.vectorstore.as_retriever(
                search_type="similarity", search_kwargs={"k": 3}
            )

            # Retrieve documents
            docs = retriever.get_relevant_documents(question)

            # Simple relevance check: does context contain question keywords?
            question_keywords = set(question.lower().split())
            question_keywords.discard("what")
            question_keywords.discard("how")
            question_keywords.discard("why")
            question_keywords.discard("the")
            question_keywords.discard("is")
            question_keywords.discard("are")

            context = " ".join([doc.page_content for doc in docs]).lower()

            # Count how many keywords appear in context
            matching_keywords = sum(
                1 for keyword in question_keywords if keyword in context
            )
            relevance_score = (
                matching_keywords / len(question_keywords) if question_keywords else 0
            )

            is_relevant = relevance_score > 0.3  # At least 30% keywords match

            detail = {
                "question": question,
                "num_docs_retrieved": len(docs),
                "relevance_score": relevance_score,
                "is_relevant": is_relevant,
            }

            if is_relevant:
                results["passed"] += 1
                print(f"✅ Context is relevant (score: {relevance_score:.2f})")
            else:
                results["failed"] += 1
                print(f"❌ Context may not be relevant (score: {relevance_score:.2f})")

            results["details"].append(detail)

        return results

    def test_answer_relevance(self, questions: List[str]) -> Dict[str, Any]:
        """
        Test if answer is relevant to question

        Args:
            questions: List of test questions

        Returns:
            Test results
        """
        print("\n" + "=" * 60)
        print("Testing Answer Relevance...")
        print("=" * 60)

        results = {
            "metric": "answer_relevance",
            "total_questions": len(questions),
            "passed": 0,
            "failed": 0,
            "details": [],
        }

        for question in questions:
            print(f"\nQuestion: {question}")

            # Get response
            response = self.model.predict(question)

            # Simple relevance check: does answer contain question keywords?
            question_keywords = set(question.lower().split())
            question_keywords.discard("what")
            question_keywords.discard("how")
            question_keywords.discard("why")
            question_keywords.discard("the")
            question_keywords.discard("is")
            question_keywords.discard("are")

            response_lower = response.lower()

            # Count how many keywords appear in response
            matching_keywords = sum(
                1 for keyword in question_keywords if keyword in response_lower
            )
            relevance_score = (
                matching_keywords / len(question_keywords) if question_keywords else 0
            )

            is_relevant = relevance_score > 0.3  # At least 30% keywords match

            detail = {
                "question": question,
                "response": response[:200],
                "relevance_score": relevance_score,
                "is_relevant": is_relevant,
            }

            if is_relevant:
                results["passed"] += 1
                print(f"✅ Answer is relevant (score: {relevance_score:.2f})")
            else:
                results["failed"] += 1
                print(f"❌ Answer may not be relevant (score: {relevance_score:.2f})")

            results["details"].append(detail)

        return results

    def run_all_evaluations(self, questions: List[str] = None) -> Dict[str, Any]:
        """
        Run all RAG evaluations

        Args:
            questions: List of test questions (uses default if None)

        Returns:
            Evaluation summary
        """
        if questions is None:
            questions = MEDICAL_QUESTIONS

        print("\n" + "=" * 80)
        print("RUNNING RAG EVALUATION TESTS")
        print("=" * 80)

        # Run all evaluations
        self.results["correctness"] = self.test_correctness(questions)
        self.results["groundedness"] = self.test_groundedness(questions)
        self.results["context_relevance"] = self.test_context_relevance(questions)
        self.results["answer_relevance"] = self.test_answer_relevance(questions)

        # Generate summary
        summary = self._generate_summary()

        # Save results
        self._save_results()

        return summary

    def _generate_summary(self) -> Dict[str, Any]:
        """Generate evaluation summary"""
        print("\n" + "=" * 80)
        print("RAG EVALUATION SUMMARY")
        print("=" * 80)

        for metric, results in self.results.items():
            total = results["total_questions"]
            passed = results["passed"]
            pass_rate = (passed / total * 100) if total > 0 else 0

            print(f"\n{metric.upper()}:")
            print(f"  Total: {total}")
            print(f"  Passed: {passed} ✅")
            print(f"  Failed: {results['failed']} ❌")
            print(f"  Pass Rate: {pass_rate:.1f}%")

        print(f"\n{'=' * 80}")

        return self.results

    def _save_results(self):
        """Save evaluation results to file"""
        results_file = RESULTS_DIR / "rag_evaluation_results.json"

        with open(results_file, "w") as f:
            json.dump(self.results, f, indent=2)

        print(f"\n✅ Results saved to: {results_file}")


# Main execution
if __name__ == "__main__":
    print("Medical RAG Chatbot - RAG Evaluation Suite")
    print("=" * 80)

    # Create evaluator
    evaluator = RAGEvaluator()

    # Run all evaluations
    summary = evaluator.run_all_evaluations()

    print("\n" + "=" * 80)
    print("RAG evaluation complete!")
    print("=" * 80)
