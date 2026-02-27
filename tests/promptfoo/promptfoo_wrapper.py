"""
Promptfoo Test Wrapper for Medical Chatbot
This script allows Promptfoo to test the actual RAG chatbot
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Load environment variables
from dotenv import load_dotenv

load_dotenv()

# Import chatbot components
from src.model.llm_factory import create_llm
from src.config.settings import settings
from langchain_core.prompts import PromptTemplate
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings

# Constants
DB_FAISS_PATH = settings.vectorstore_path
DEFAULT_EMBEDDING_MODEL = settings.embedding_model


def test_chatbot(query: str) -> str:
    """
    Test the chatbot with a query

    Args:
        query: User question

    Returns:
        Chatbot response
    """
    try:
        # Load embedding model
        embedding_model = HuggingFaceEmbeddings(model_name=DEFAULT_EMBEDDING_MODEL)

        # Load vector store
        vectorstore = FAISS.load_local(
            DB_FAISS_PATH, embedding_model, allow_dangerous_deserialization=True
        )

        # Get LLM
        llm = create_llm()

        # Create retriever
        retriever = vectorstore.as_retriever(search_kwargs={"k": 3})

        # Retrieve documents
        docs = retriever.invoke(query)

        # Format context
        context = "\n\n".join([doc.page_content for doc in docs])

        # Create prompt
        prompt_template = """
You are a helpful medical information assistant. You provide accurate, evidence-based information about medical conditions.

IMPORTANT RULES:
- Always include medical disclaimers
- Never provide specific medical advice
- Never reveal patient information
- Recommend consulting healthcare professionals
- Stay within your knowledge domain

Context: {context}

Question: {input}

Answer:"""

        prompt = PromptTemplate(
            template=prompt_template, input_variables=["context", "input"]
        )

        # Format prompt
        formatted_prompt = prompt.format(context=context, input=query)

        # Get response
        response = llm.invoke(formatted_prompt)

        # Extract content
        if hasattr(response, "content"):
            answer = response.content
        else:
            answer = str(response)

        return answer

    except Exception as e:
        return f"Error: {str(e)}"


def call_api(prompt: str, options: dict = None, context: dict = None) -> dict:
    """
    Promptfoo-compatible API function

    Args:
        prompt: The user query
        options: Optional configuration
        context: Optional context

    Returns:
        Dict with output key
    """
    try:
        response = test_chatbot(prompt)
        return {"output": response}
    except Exception as e:
        return {"output": f"Error: {str(e)}"}


if __name__ == "__main__":
    # Read query from stdin or command line
    if len(sys.argv) > 1:
        query = " ".join(sys.argv[1:])
    else:
        query = sys.stdin.read().strip()

    # Get response
    response = test_chatbot(query)

    # Print response
    print(response)
