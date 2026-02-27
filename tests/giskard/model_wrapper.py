"""
Giskard Model Wrapper for Medical RAG Chatbot
Wraps the RAG model for Giskard testing
"""

import sys
from pathlib import Path
from typing import Any, List, Optional
import pandas as pd

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

try:
    import giskard as gsk

    GISKARD_AVAILABLE = True
except ImportError:
    GISKARD_AVAILABLE = False
    print("⚠️ Giskard not available. Install with: uv add giskard")
    print("⚠️ Note: Giskard requires Python 3.9-3.11")

from src.helper import load_vector_store
from src.prompt import get_prompt_template
from langchain_groq import ChatGroq
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()


class MedicalRAGModel:
    """
    Wrapper for Medical RAG Chatbot to work with Giskard
    """

    def __init__(self):
        """Initialize the RAG model"""
        self.vectorstore = None
        self.llm = None
        self.prompt = None
        self._initialize_model()

    def _initialize_model(self):
        """Initialize RAG components"""
        try:
            # Load vector store
            self.vectorstore = load_vector_store()

            # Initialize LLM
            groq_api_key = os.getenv("GROQ_API_KEY")
            if not groq_api_key:
                raise ValueError("GROQ_API_KEY not found in environment variables")

            self.llm = ChatGroq(
                groq_api_key=groq_api_key,
                model_name="llama-3.3-70b-versatile",
                temperature=0.7,
            )

            # Get prompt template
            self.prompt = get_prompt_template()

            print("✅ Medical RAG model initialized successfully")

        except Exception as e:
            print(f"❌ Error initializing model: {e}")
            raise

    def predict(self, query: str) -> str:
        """
        Generate prediction for a single query

        Args:
            query: User question

        Returns:
            LLM response
        """
        try:
            # Retrieve relevant documents
            retriever = self.vectorstore.as_retriever(
                search_type="similarity", search_kwargs={"k": 3}
            )
            docs = retriever.get_relevant_documents(query)

            # Format context
            context = "\n\n".join([doc.page_content for doc in docs])

            # Create prompt
            formatted_prompt = self.prompt.format(context=context, input=query)

            # Get LLM response
            response = self.llm.invoke(formatted_prompt)

            # Extract content
            if hasattr(response, "content"):
                return response.content
            return str(response)

        except Exception as e:
            return f"Error: {str(e)}"

    def predict_batch(self, queries: List[str]) -> List[str]:
        """
        Generate predictions for multiple queries

        Args:
            queries: List of user questions

        Returns:
            List of LLM responses
        """
        return [self.predict(query) for query in queries]


def create_giskard_model() -> Optional[Any]:
    """
    Create a Giskard-wrapped model

    Returns:
        Giskard Model object or None if Giskard not available
    """
    if not GISKARD_AVAILABLE:
        print("⚠️ Giskard not available. Returning None.")
        return None

    try:
        # Initialize RAG model
        rag_model = MedicalRAGModel()

        # Define prediction function for Giskard
        def prediction_function(df: pd.DataFrame) -> pd.DataFrame:
            """
            Prediction function compatible with Giskard

            Args:
                df: DataFrame with 'question' column

            Returns:
                DataFrame with 'prediction' column
            """
            questions = df["question"].tolist()
            predictions = rag_model.predict_batch(questions)
            return pd.DataFrame({"prediction": predictions})

        # Create Giskard model
        gsk_model = gsk.Model(
            model=prediction_function,
            model_type="text_generation",
            name="Medical RAG Chatbot",
            description="RAG-based medical information chatbot",
            feature_names=["question"],
        )

        print("✅ Giskard model wrapper created successfully")
        return gsk_model

    except Exception as e:
        print(f"❌ Error creating Giskard model: {e}")
        return None


def create_test_dataset(
    questions: List[str], expected_answers: Optional[List[str]] = None
) -> Optional[Any]:
    """
    Create a Giskard dataset for testing

    Args:
        questions: List of test questions
        expected_answers: Optional list of expected answers

    Returns:
        Giskard Dataset object or None if Giskard not available
    """
    if not GISKARD_AVAILABLE:
        print("⚠️ Giskard not available. Returning None.")
        return None

    try:
        # Create DataFrame
        data = {"question": questions}
        if expected_answers:
            data["expected_answer"] = expected_answers

        df = pd.DataFrame(data)

        # Create Giskard dataset
        gsk_dataset = gsk.Dataset(
            df=df,
            target="expected_answer" if expected_answers else None,
            name="Medical RAG Test Dataset",
        )

        print(f"✅ Created test dataset with {len(questions)} questions")
        return gsk_dataset

    except Exception as e:
        print(f"❌ Error creating test dataset: {e}")
        return None


# Example usage
if __name__ == "__main__":
    print("Testing Medical RAG Model Wrapper...")
    print("=" * 60)

    # Test without Giskard (basic functionality)
    print("\n1. Testing basic RAG model...")
    try:
        model = MedicalRAGModel()
        test_query = "What are the symptoms of diabetes?"
        response = model.predict(test_query)
        print(f"\nQuery: {test_query}")
        print(f"Response: {response[:200]}...")
        print("✅ Basic model test passed")
    except Exception as e:
        print(f"❌ Basic model test failed: {e}")

    # Test with Giskard (if available)
    if GISKARD_AVAILABLE:
        print("\n2. Testing Giskard wrapper...")
        try:
            gsk_model = create_giskard_model()
            if gsk_model:
                print("✅ Giskard wrapper test passed")
        except Exception as e:
            print(f"❌ Giskard wrapper test failed: {e}")
    else:
        print("\n2. Skipping Giskard wrapper test (not available)")

    print("\n" + "=" * 60)
    print("Testing complete!")
