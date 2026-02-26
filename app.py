import os
import sys
from typing import Optional, Any
from datetime import datetime
import streamlit as st

from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser

from dotenv import load_dotenv

# Import from src structure
from src.utils.logger import get_logger
from src.utils.exceptions import VectorStoreError, LLMError, ConfigurationError
from src.config.settings import settings
from src.model.llm_factory import create_llm
from src.content_analyzer.output_guardrails import OutputGuardrails

# Import observability modules
from src.observability import (
    configure_langsmith,
    is_langsmith_enabled,
    trace_chain,
    create_feedback,
    get_current_run_id
)
from src.observability.tracing import add_run_metadata

# Initialize logger
logger = get_logger(__name__, log_to_file=True)

# Load environment variables
load_dotenv()

# Configure LangSmith observability (optional - gracefully handles missing API key)
try:
    langsmith_configured = configure_langsmith(
        project_name="medical-chatbot",
        enable_tracing=True
    )
    if langsmith_configured:
        logger.info("✅ LangSmith observability enabled")
    else:
        logger.info("ℹ️ LangSmith observability disabled (API key not configured)")
except Exception as e:
    logger.warning(f"LangSmith configuration failed: {str(e)}. Continuing without observability.")

# Configuration from settings
DB_FAISS_PATH = settings.vectorstore_path if settings else "vectorstore/db_faiss"
DEFAULT_MODEL = settings.default_llm_model if settings else "llama-3.1-8b-instant"
DEFAULT_EMBEDDING_MODEL = settings.embedding_model if settings else "sentence-transformers/all-MiniLM-L6-v2"
MAX_RETRIES = settings.max_retries if settings else 3

# Initialize Output Guardrails
guardrails = OutputGuardrails(
    enable_pii_check=True,
    enable_toxic_check=True,
    enable_hallucination_check=True,
    require_medical_disclaimer=True,
    enable_ner_check=False,  # Disabled: spaCy model not installed (run: python -m spacy download en_core_web_sm)
    enable_presidio_check=True,  # Enable Presidio ML-based PII detection
    block_on_pii=True,
    block_on_toxic=True
)
logger.info("✅ Output guardrails initialized")


@st.cache_resource
def get_vectorstore() -> Optional[FAISS]:
    """
    Load the FAISS vector store with error handling.
    
    Returns:
        FAISS: The loaded vector store
        
    Raises:
        VectorStoreError: If vector store cannot be loaded
    """
    try:
        logger.info(f"Loading vector store from {DB_FAISS_PATH}")
        
        # Check if vector store path exists
        if not os.path.exists(DB_FAISS_PATH):
            error_msg = f"Vector store not found at {DB_FAISS_PATH}. Please run create_memory_for_llm.py first to generate Embedding vector for Documents."
            logger.error(error_msg)
            raise VectorStoreError(error_msg)
        
        # Load embedding model
        try:
            embedding_model = HuggingFaceEmbeddings(
                model_name=DEFAULT_EMBEDDING_MODEL
            )
            logger.info(f"Loaded embedding model: {DEFAULT_EMBEDDING_MODEL}")
        except Exception as e:
            error_msg = f"Failed to load embedding model: {str(e)}"
            logger.error(error_msg)
            raise VectorStoreError(error_msg)
        
        # Load FAISS database
        try:
            db = FAISS.load_local(
                DB_FAISS_PATH, 
                embedding_model, 
                allow_dangerous_deserialization=True
            )
            logger.info("Successfully loaded FAISS vector store")
            return db
        except Exception as e:
            error_msg = f"Failed to load FAISS database: {str(e)}"
            logger.error(error_msg)
            raise VectorStoreError(error_msg)
            
    except VectorStoreError:
        raise
    except Exception as e:
        error_msg = f"Unexpected error loading vector store: {str(e)}"
        logger.error(error_msg)
        raise VectorStoreError(error_msg)


def validate_environment() -> dict:
    """
    Validate required environment variables based on active LLM.
    
    Returns:
        dict: Configuration dictionary
        
    Raises:
        ConfigurationError: If required variables are missing
    """
    if not settings or not settings.config:
        error_msg = "Configuration not loaded. Please check src/config/config.yaml"
        logger.error(error_msg)
        raise ConfigurationError(error_msg)
    
    # Get active LLM configuration
    active_llm = settings.config.get('active_llm', 'groq')
    llm_config = settings.config.get('llms', {}).get(active_llm, {})
    
    if not llm_config:
        error_msg = f"LLM '{active_llm}' not found in config.yaml"
        logger.error(error_msg)
        raise ConfigurationError(error_msg)
    
    # Check API key if required
    api_key_env = llm_config.get('api_key_env')
    if api_key_env:
        api_key = os.environ.get(api_key_env)
        if not api_key:
            error_msg = f"{api_key_env} not found in environment variables. Please set it in .env file."
            logger.error(error_msg)
            raise ConfigurationError(error_msg)
    
    logger.info("Environment validation successful")
    return {
        "active_llm": active_llm,
        "model_name": llm_config.get('model'),
        "provider": llm_config.get('provider')
    }


def initialize_llm(config: dict):
    """
    Initialize LLM using the factory pattern (supports all providers).
    
    Args:
        config: Configuration dictionary
        
    Returns:
        LLM instance (ChatGroq, ChatGoogleGenerativeAI, ChatOpenAI, etc.)
        
    Raises:
        LLMError: If LLM initialization fails
    """
    try:
        active_llm = config.get('active_llm', 'groq')
        logger.info(f"Initializing LLM: {active_llm} (model: {config['model_name']})")
        
        # Use LLM factory to create the appropriate LLM instance
        llm = create_llm(llm_name=active_llm)
        
        logger.info(f"✅ LLM initialized successfully: {active_llm}")
        return llm
    except Exception as e:
        error_msg = f"Failed to initialize LLM: {str(e)}"
        logger.error(error_msg)
        raise LLMError(error_msg)


def get_rag_prompt():
    """
    Create a RAG prompt template for question answering.
    Loads from src/prompts/medical_assistant.txt for better maintainability.
    
    Returns:
        ChatPromptTemplate: Prompt template for RAG
        
    Raises:
        LLMError: If prompt creation fails
    """
    try:
        logger.info("Loading RAG prompt template from file...")
        
        from langchain_core.prompts import ChatPromptTemplate
        from pathlib import Path
        
        # Load prompt from file
        prompt_path = Path("src/prompts/medical_assistant.txt")
        
        if not prompt_path.exists():
            logger.warning(f"Prompt file not found: {prompt_path}, using fallback")
            return create_fallback_prompt()
        
        with open(prompt_path, 'r', encoding='utf-8') as f:
            template = f.read()
        
        prompt = ChatPromptTemplate.from_template(template)
        logger.info(f"✅ Successfully loaded prompt from {prompt_path}")
        logger.info("📋 Prompt includes: 9 medical rules + 5 security rules")
        return prompt
        
    except Exception as e:
        error_msg = f"Failed to load prompt from file: {str(e)}"
        logger.error(error_msg)
        logger.info("Using fallback prompt instead")
        return create_fallback_prompt()


def create_fallback_prompt():
    """
    Create a fallback prompt if file loading fails.
    
    Returns:
        ChatPromptTemplate: Basic fallback prompt
    """
    from langchain_core.prompts import ChatPromptTemplate
    
    template = """You are a helpful medical assistant. Use the following context to answer the user's question.
If you don't know the answer based on the context, say so - don't make up information.

Context:
{context}

Question: {input}

Answer:"""
    
    logger.info("Using fallback prompt (basic version)")
    return ChatPromptTemplate.from_template(template)


@trace_chain(
    name="medical_rag_query",
    metadata={"model": DEFAULT_MODEL, "retriever_k": 3},
    tags=["rag", "medical", "chatbot"]
)
def process_query(query: str, vectorstore: FAISS, llm: Any, prompt) -> str:
    """
    Process user query through the RAG chain with error handling.
    
    Args:
        query: User's question
        vectorstore: FAISS vector store
        llm: Language model
        prompt: RAG prompt template
        
    Returns:
        str: Generated answer
        
    Raises:
        LLMError: If query processing fails
    """
    try:
        logger.info(f"Processing query: {query[:50]}...")
        
        # Validate input
        if not query or not query.strip():
            raise ValueError("Query cannot be empty")
        
        if len(query) > 1000:
            logger.warning(f"Query length ({len(query)}) exceeds recommended limit")
        
        # Add metadata to LangSmith trace (if enabled)
        if is_langsmith_enabled():
            add_run_metadata({
                "query_length": len(query),
                "query_preview": query[:100],
                "timestamp": str(datetime.now()),
            })
        
        # Create retriever with tracing
        retriever = vectorstore.as_retriever(search_kwargs={'k': 3})
        
        # Trace retrieval step
        logger.info("🔍 Starting document retrieval...")
        retrieved_docs = retriever.invoke(query)
        
        # Log retrieval details
        if is_langsmith_enabled():
            add_run_metadata({
                "num_docs_retrieved": len(retrieved_docs),
                "doc_sources": [doc.metadata.get('source', 'unknown') for doc in retrieved_docs],
                "retrieval_k": 3,
            })
        
        logger.info(f"✅ Retrieved {len(retrieved_docs)} relevant documents")
        for i, doc in enumerate(retrieved_docs):
            logger.debug(f"Doc {i+1}: {doc.page_content[:100]}... (source: {doc.metadata.get('source', 'unknown')})")
        
        # Helper function to format documents
        def format_docs(docs):
            formatted = "\n\n".join(doc.page_content for doc in docs)
            logger.debug(f"📝 Formatted context length: {len(formatted)} chars")
            return formatted
        
        # Format retrieved documents
        context = format_docs(retrieved_docs)
        
        # Create prompt with context
        logger.info("🤖 Generating answer with LLM...")
        formatted_prompt = prompt.format(context=context, input=query)
        
        # Log prompt details
        if is_langsmith_enabled():
            add_run_metadata({
                "prompt_length": len(formatted_prompt),
                "context_length": len(context),
            })
        
        # Invoke LLM
        response = llm.invoke(formatted_prompt)
        
        # Extract content from AIMessage object
        if hasattr(response, 'content'):
            answer = response.content
        else:
            answer = str(response)
        
        if not answer:
            raise LLMError("Empty response from RAG chain")
        
        logger.info(f"Successfully generated answer (length: {len(answer)})")
        
        # ✅ VALIDATE OUTPUT WITH GUARDRAILS
        logger.info("🛡️ Validating output with guardrails...")
        is_safe, issues, safe_output = guardrails.validate_output(
            llm_output=answer,
            original_query=query,
            retrieved_context=[doc.page_content for doc in retrieved_docs]
        )
        
        # Log validation results
        if issues:
            logger.warning(f"⚠️ Guardrails found {len(issues)} issue(s)")
            for issue in issues:
                logger.warning(f"  - {issue.issue_type}: {issue.description}")
        
        # Add validation metadata to LangSmith
        if is_langsmith_enabled():
            add_run_metadata({
                "guardrails_safe": is_safe,
                "guardrails_issues_count": len(issues),
                "guardrails_issue_types": [issue.issue_type for issue in issues],
            })
        
        # Block unsafe output
        if not is_safe:
            logger.error("❌ Output blocked by guardrails")
            # Determine block reason
            if any(issue.issue_type.startswith("PII_") for issue in issues):
                fallback = guardrails.get_fallback_response("pii")
            elif any(issue.issue_type.startswith("TOXIC_") for issue in issues):
                fallback = guardrails.get_fallback_response("toxic")
            else:
                fallback = guardrails.get_fallback_response("safety")
            
            return fallback
        
        # Return safe output (may have been modified, e.g., disclaimer added)
        logger.info("✅ Output validated and safe")
        return safe_output
        
    except ValueError as e:
        logger.error(f"Validation error: {str(e)}")
        raise LLMError(f"Invalid input: {str(e)}")
    except Exception as e:
        error_msg = f"Failed to process query: {str(e)}"
        logger.error(error_msg)
        raise LLMError(error_msg)


def display_error_message(error: Exception, error_type: str):
    """
    Display user-friendly error messages in Streamlit.
    
    Args:
        error: The exception that occurred
        error_type: Type of error for user display
    """
    error_messages = {
        "VectorStoreError": {
            "title": "📚 Vector Store Error",
            "suggestion": "Please ensure the vector database is created by running `create_memory_for_llm.py`"
        },
        "ConfigurationError": {
            "title": "⚙️ Configuration Error",
            "suggestion": "Please check your `.env` file and ensure all required API keys are set"
        },
        "LLMError": {
            "title": "🤖 AI Model Error",
            "suggestion": "There was an issue with the AI model. Please try again or check your API key"
        },
        "default": {
            "title": "❌ Unexpected Error",
            "suggestion": "An unexpected error occurred. Please try again"
        }
    }
    
    error_info = error_messages.get(error_type, error_messages["default"])
    
    st.error(f"**{error_info['title']}**")
    st.error(f"Error: {str(error)}")
    st.info(f"💡 {error_info['suggestion']}")
    
    # Log the error
    logger.error(f"{error_type}: {str(error)}", exc_info=True)


def main():
    """Main application function with comprehensive error handling"""
    
    # Page configuration
    st.set_page_config(
        page_title="Medical Chatbot",
        page_icon="🏥",
        layout="centered"
    )
    
    st.title("🏥 Medical Chatbot")
    st.markdown("*Ask me anything about medical topics from the knowledge base*")
    
    # Initialize session state
    if 'messages' not in st.session_state:
        st.session_state.messages = []
        logger.info("Initialized new chat session")
    
    if 'initialized' not in st.session_state:
        st.session_state.initialized = False
    
    # Initialize components (only once)
    if not st.session_state.initialized:
        try:
            with st.spinner("🔄 Initializing chatbot..."):
                # Validate environment
                config = validate_environment()
                st.session_state.config = config
                
                # Load vector store
                vectorstore = get_vectorstore()
                st.session_state.vectorstore = vectorstore
                
                # Initialize LLM
                llm = initialize_llm(config)
                st.session_state.llm = llm
                
                # Get RAG prompt
                prompt = get_rag_prompt()
                st.session_state.prompt = prompt
                
                st.session_state.initialized = True
                logger.info("Chatbot initialization complete")
                st.success("✅ Chatbot ready!")
                
        except (VectorStoreError, ConfigurationError, LLMError) as e:
            display_error_message(e, type(e).__name__)
            st.stop()
        except Exception as e:
            display_error_message(e, "default")
            st.stop()
    
    # Display chat history
    for message in st.session_state.messages:
        with st.chat_message(message['role']):
            st.markdown(message['content'])
    
    # Chat input
    if user_query := st.chat_input("💬 Ask your medical question here..."):
        
        # Display user message
        with st.chat_message('user'):
            st.markdown(user_query)
        st.session_state.messages.append({'role': 'user', 'content': user_query})
        
        # Process query and generate response
        try:
            with st.chat_message('assistant'):
                with st.spinner("🤔 Thinking..."):
                    answer = process_query(
                        user_query,
                        st.session_state.vectorstore,
                        st.session_state.llm,
                        st.session_state.prompt
                    )
                    st.markdown(answer)
                    
                    # Add feedback buttons (if LangSmith is enabled)
                    if is_langsmith_enabled():
                        st.markdown("---")
                        st.markdown("**Was this answer helpful?**")
                        col1, col2, col3 = st.columns([1, 1, 4])
                        
                        # Get current run ID for feedback
                        run_id = get_current_run_id()
                        
                        with col1:
                            if st.button("👍 Yes", key=f"thumbs_up_{len(st.session_state.messages)}"):
                                if run_id:
                                    create_feedback(
                                        run_id=run_id,
                                        key="user_rating",
                                        score=1.0,
                                        comment="Helpful answer"
                                    )
                                    st.success("Thanks for your feedback!")
                                    logger.info(f"Positive feedback recorded for run {run_id}")
                        
                        with col2:
                            if st.button("👎 No", key=f"thumbs_down_{len(st.session_state.messages)}"):
                                if run_id:
                                    create_feedback(
                                        run_id=run_id,
                                        key="user_rating",
                                        score=0.0,
                                        comment="Not helpful"
                                    )
                                    st.warning("Thanks for your feedback. We'll work to improve!")
                                    logger.info(f"Negative feedback recorded for run {run_id}")
            
            st.session_state.messages.append({'role': 'assistant', 'content': answer})
            logger.info("Query processed successfully")
            
        except LLMError as e:
            display_error_message(e, "LLMError")
        except Exception as e:
            display_error_message(e, "default")
    
    # Sidebar with info
    with st.sidebar:
        st.header("ℹ️ About")

        # Dynamically show active LLM info from settings
        active_llm_name = "Unknown"
        active_provider = "Unknown"
        if settings and settings.config:
            _active = settings.config.get("active_llm", "groq")
            _llm_cfg = settings.config.get("llms", {}).get(_active, {})
            active_llm_name = _active.upper()
            active_provider = _llm_cfg.get("provider", _active).capitalize()

        st.markdown(f"""
        This chatbot uses:
        - 🧠 RAG (Retrieval-Augmented Generation)
        - 📚 FAISS Vector Database
        - 🤖 **{active_llm_name}** ({active_provider} API)
        - 🔍 Semantic Search
        """)
        
        # Show observability status
        if is_langsmith_enabled():
            st.success("📊 LangSmith Observability: **Enabled**")
            st.caption("All interactions are being traced for quality monitoring")
        else:
            st.info("📊 LangSmith Observability: **Disabled**")
            st.caption("Set LANGSMITH_API_KEY to enable tracing")
        
        st.header("📊 Stats")
        st.metric("Messages", len(st.session_state.messages))
        
        if st.button("🗑️ Clear Chat"):
            st.session_state.messages = []
            logger.info("Chat history cleared")
            st.rerun()


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logger.critical(f"Critical error in main: {str(e)}", exc_info=True)
        st.error("A critical error occurred. Please check the logs.")