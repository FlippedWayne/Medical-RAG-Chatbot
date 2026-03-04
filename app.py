import os
from typing import Optional, Any
from datetime import datetime
from pathlib import Path
import streamlit as st

from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader

from dotenv import load_dotenv

# Import from src structure
from src.utils.logger import get_logger
from src.utils.exceptions import VectorStoreError, LLMError, ConfigurationError
from src.config.settings import settings
from src.model.llm_factory import create_llm
from src.content_analyzer.output_guardrails import OutputGuardrails
from src.storage.gcs_handler import GCSHandler

# Import observability modules
from src.observability import (
    configure_langsmith,
    is_langsmith_enabled,
    create_feedback,
    get_current_run_id,
)
from src.observability.tracing import add_run_metadata

try:
    from langsmith import traceable as ls_traceable
except ImportError:
    # Fallback: no-op decorator if langsmith not installed
    def ls_traceable(**kwargs):
        def decorator(func):
            return func
        return decorator

# Initialize logger
logger = get_logger(__name__, log_to_file=True)

# Load environment variables
load_dotenv()

# Configure LangSmith observability (optional - gracefully handles missing API key)
try:
    langsmith_configured = configure_langsmith(
        project_name="medical-chatbot", enable_tracing=True
    )
    if langsmith_configured:
        logger.info("✅ LangSmith observability enabled")
    else:
        logger.info("ℹ️ LangSmith observability disabled (API key not configured)")
except Exception as e:
    logger.warning(
        f"LangSmith configuration failed: {str(e)}. Continuing without observability."
    )

# Configuration from settings
DB_FAISS_PATH = settings.vectorstore_path if settings else "vectorstore/db_faiss"
DEFAULT_MODEL = settings.default_llm_model if settings else "llama-3.1-8b-instant"
DEFAULT_EMBEDDING_MODEL = (
    settings.embedding_model if settings else "sentence-transformers/all-MiniLM-L6-v2"
)
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
    block_on_toxic=True,
)
logger.info("✅ Output guardrails initialized")

# Initialize GCS handler (no-op if GCS_BUCKET_NAME not set)
gcs_handler = GCSHandler(
    bucket_name=settings.gcs_bucket_name if settings else None,
    index_prefix=settings.gcs_index_prefix if settings else "faiss-index",
)
if gcs_handler.gcs_enabled:
    logger.info(f"☁️  GCS storage enabled — bucket: {gcs_handler.bucket_name}")
else:
    logger.info("📂 GCS not configured — using local vectorstore only")


@st.cache_resource
def get_vectorstore() -> Optional[FAISS]:
    """
    Load the FAISS vector store.

    Priority:
      1. Download from GCS (if GCS_BUCKET_NAME is configured)
      2. Fallback to local vectorstore/ directory

    Returns:
        FAISS: The loaded vector store

    Raises:
        VectorStoreError: If vector store cannot be loaded from either source
    """
    try:
        # --- Load embedding model (needed by both paths) ---
        try:
            embedding_model = HuggingFaceEmbeddings(model_name=DEFAULT_EMBEDDING_MODEL)
            logger.info(f"Loaded embedding model: {DEFAULT_EMBEDDING_MODEL}")
        except Exception as e:
            raise VectorStoreError(f"Failed to load embedding model: {str(e)}")

        # --- Path 1: Try GCS ---
        if gcs_handler.gcs_enabled:
            logger.info("☁️  Trying to load FAISS index from GCS...")
            tmp_path = gcs_handler.download_to_temp()
            if tmp_path:
                try:
                    db = FAISS.load_local(
                        tmp_path, embedding_model, allow_dangerous_deserialization=True
                    )
                    logger.info("✅ FAISS index loaded from GCS")
                    return db
                except Exception as e:
                    logger.warning(
                        f"GCS index found but failed to load: {e}. Trying local fallback."
                    )
            else:
                logger.info("GCS index not found yet — checking local fallback")

        # --- Path 2: Local filesystem ---
        logger.info(f"📂 Loading FAISS index from local path: {DB_FAISS_PATH}")
        if not os.path.exists(DB_FAISS_PATH):
            error_msg = (
                f"Vector store not found at {DB_FAISS_PATH} and GCS has no index either. "
                "Please run create_vectorstore.py first, or upload PDFs via the sidebar."
            )
            logger.error(error_msg)
            raise VectorStoreError(error_msg)

        try:
            db = FAISS.load_local(
                DB_FAISS_PATH, embedding_model, allow_dangerous_deserialization=True
            )
            logger.info("✅ FAISS index loaded from local filesystem")
            return db
        except Exception as e:
            raise VectorStoreError(f"Failed to load FAISS database: {str(e)}")

    except VectorStoreError:
        raise
    except Exception as e:
        raise VectorStoreError(f"Unexpected error loading vector store: {str(e)}")


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
    active_llm = settings.config.get("active_llm", "groq")
    llm_config = settings.config.get("llms", {}).get(active_llm, {})

    if not llm_config:
        error_msg = f"LLM '{active_llm}' not found in config.yaml"
        logger.error(error_msg)
        raise ConfigurationError(error_msg)

    # Check API key if required
    api_key_env = llm_config.get("api_key_env")
    if api_key_env:
        api_key = os.environ.get(api_key_env)
        if not api_key:
            error_msg = f"{api_key_env} not found in environment variables. Please set it in .env file."
            logger.error(error_msg)
            raise ConfigurationError(error_msg)

    logger.info("Environment validation successful")
    return {
        "active_llm": active_llm,
        "model_name": llm_config.get("model"),
        "provider": llm_config.get("provider"),
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
        active_llm = config.get("active_llm", "groq")
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

        # Load prompt from file
        prompt_path = Path("src/prompts/medical_assistant.txt")

        if not prompt_path.exists():
            logger.warning(f"Prompt file not found: {prompt_path}, using fallback")
            return create_fallback_prompt()

        with open(prompt_path, "r", encoding="utf-8") as f:
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

Previous Conversation:
{chat_history}

Context:
{context}

Question: {input}

Answer:"""

    logger.info("Using fallback prompt (basic version)")
    return ChatPromptTemplate.from_template(template)


def prepare_rag_context(
    query: str, vectorstore: FAISS, prompt, chat_history: str = ""
) -> tuple:
    """
    Retrieve relevant documents and build the formatted prompt.

    This is the first half of the RAG pipeline — separated from LLM
    generation so the UI can stream tokens directly.

    Args:
        query: User's question
        vectorstore: FAISS vector store
        prompt: RAG prompt template
        chat_history: Formatted string of previous conversation turns

    Returns:
        tuple: (formatted_prompt, retrieved_docs)

    Raises:
        LLMError: If retrieval or prompt formatting fails
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
            add_run_metadata(
                {
                    "query_length": len(query),
                    "query_preview": query[:100],
                    "timestamp": str(datetime.now()),
                }
            )

        # Create retriever with tracing
        retriever = vectorstore.as_retriever(search_kwargs={"k": 3})

        # Trace retrieval step
        logger.info("🔍 Starting document retrieval...")
        retrieved_docs = retriever.invoke(query)

        # Log retrieval details
        if is_langsmith_enabled():
            add_run_metadata(
                {
                    "num_docs_retrieved": len(retrieved_docs),
                    "doc_sources": [
                        doc.metadata.get("source", "unknown") for doc in retrieved_docs
                    ],
                    "retrieval_k": 3,
                }
            )

        logger.info(f"✅ Retrieved {len(retrieved_docs)} relevant documents")
        for i, doc in enumerate(retrieved_docs):
            logger.debug(
                f"Doc {i + 1}: {doc.page_content[:100]}... (source: {doc.metadata.get('source', 'unknown')})"
            )

        # Format retrieved documents
        context = "\n\n".join(doc.page_content for doc in retrieved_docs)
        logger.debug(f"📝 Formatted context length: {len(context)} chars")

        # Create prompt with context and chat history
        logger.info("🤖 Preparing prompt for LLM...")
        formatted_prompt = prompt.format(
            context=context, input=query, chat_history=chat_history
        )

        # Log prompt details
        if is_langsmith_enabled():
            add_run_metadata(
                {
                    "prompt_length": len(formatted_prompt),
                    "context_length": len(context),
                }
            )

        return formatted_prompt, retrieved_docs

    except ValueError as e:
        logger.error(f"Validation error: {str(e)}")
        raise LLMError(f"Invalid input: {str(e)}")
    except Exception as e:
        error_msg = f"Failed to prepare RAG context: {str(e)}"
        logger.error(error_msg)
        raise LLMError(error_msg)


def stream_llm_tokens(llm: Any, formatted_prompt: str):
    """
    Generator that yields string tokens from the LLM for streaming display.

    Works with st.write_stream() — yields plain strings, not AIMessage objects.

    Args:
        llm: Language model instance
        formatted_prompt: The fully formatted prompt string

    Yields:
        str: Individual text tokens
    """
    for chunk in llm.stream(formatted_prompt):
        # LangChain chat models yield AIMessageChunk objects
        if hasattr(chunk, "content"):
            yield chunk.content
        else:
            yield str(chunk)


def validate_response(answer: str, query: str, retrieved_docs: list) -> tuple:
    """
    Run guardrails validation on the complete LLM response.

    Called after streaming completes to check safety of the full answer.

    Args:
        answer: Complete LLM response text
        query: Original user query
        retrieved_docs: Documents used for context

    Returns:
        tuple: (is_safe, final_output) — final_output is the guardrails-approved
               text (may include disclaimers) or a fallback if blocked.
    """
    if not answer:
        return False, "I wasn't able to generate a response. Please try again."

    logger.info(f"Successfully generated answer (length: {len(answer)})")

    # ✅ VALIDATE OUTPUT WITH GUARDRAILS
    logger.info("🛡️ Validating output with guardrails...")
    is_safe, issues, safe_output = guardrails.validate_output(
        llm_output=answer,
        original_query=query,
        retrieved_context=[doc.page_content for doc in retrieved_docs],
    )

    # Log validation results
    if issues:
        logger.warning(f"⚠️ Guardrails found {len(issues)} issue(s)")
        for issue in issues:
            logger.warning(f"  - {issue.issue_type}: {issue.description}")

    # Add validation metadata to LangSmith
    if is_langsmith_enabled():
        add_run_metadata(
            {
                "guardrails_safe": is_safe,
                "guardrails_issues_count": len(issues),
                "guardrails_issue_types": [issue.issue_type for issue in issues],
            }
        )

    # Block unsafe output
    if not is_safe:
        logger.error("❌ Output blocked by guardrails")
        if any(issue.issue_type.startswith("PII_") for issue in issues):
            fallback = guardrails.get_fallback_response("pii")
        elif any(issue.issue_type.startswith("TOXIC_") for issue in issues):
            fallback = guardrails.get_fallback_response("toxic")
        else:
            fallback = guardrails.get_fallback_response("safety")
        return False, fallback

    logger.info("✅ Output validated and safe")
    return True, safe_output


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
            "suggestion": "Please ensure the vector database is created by running `create_memory_for_llm.py`",
        },
        "ConfigurationError": {
            "title": "⚙️ Configuration Error",
            "suggestion": "Please check your `.env` file and ensure all required API keys are set",
        },
        "LLMError": {
            "title": "🤖 AI Model Error",
            "suggestion": "There was an issue with the AI model. Please try again or check your API key",
        },
        "default": {
            "title": "❌ Unexpected Error",
            "suggestion": "An unexpected error occurred. Please try again",
        },
    }

    error_info = error_messages.get(error_type, error_messages["default"])

    st.error(f"**{error_info['title']}**")
    st.error(f"Error: {str(error)}")
    st.info(f"💡 {error_info['suggestion']}")

    # Log the error
    logger.error(f"{error_type}: {str(error)}", exc_info=True)


def rebuild_vectorstore_from_pdfs(pdf_files: list, mode: str = "add") -> tuple:
    """
    Build or update the FAISS index from uploaded PDF files.

    Args:
        pdf_files: List of dicts with 'name' (str) and 'bytes' (bytes) keys.
                   Pre-cached from st.file_uploader to survive Streamlit reruns.
        mode: "add" to merge with existing index, "rebuild" to start fresh.

    Returns:
        Tuple[bool, str]: (success, message)
    """
    import tempfile

    if not pdf_files:
        return False, "No files uploaded."

    try:
        # Load embedding model upfront — needed by both merge and rebuild paths
        embedding_model = HuggingFaceEmbeddings(model_name=DEFAULT_EMBEDDING_MODEL)

        # Save uploaded files to a temp directory and extract chunks
        all_chunks = []
        splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)

        with tempfile.TemporaryDirectory() as tmp_dir:
            for pdf in pdf_files:
                tmp_file_path = os.path.join(tmp_dir, pdf["name"])
                with open(tmp_file_path, "wb") as f:
                    f.write(pdf["bytes"])

                try:
                    loader = PyPDFLoader(tmp_file_path)
                    docs = loader.load()
                    chunks = splitter.split_documents(docs)
                    all_chunks.extend(chunks)
                    logger.info(
                        f"Processed '{pdf['name']}': "
                        f"{len(docs)} pages, {len(chunks)} chunks"
                    )
                except Exception as e:
                    logger.warning(f"Failed to load '{pdf['name']}': {e}")
                    return False, f"Failed to read '{pdf['name']}': {e}"

        if not all_chunks:
            return False, "No content could be extracted from the uploaded PDFs."

        # Build or merge the index in batches to limit peak memory.
        # Processing all chunks at once can OOM on Cloud Run (2-4 Gi).
        BATCH_SIZE = 500
        logger.info(
            f"Building FAISS index from {len(all_chunks)} chunks "
            f"(batch size={BATCH_SIZE})"
        )

        if mode == "add":
            final_db = st.session_state.get("vectorstore")
        else:
            final_db = None

        for i in range(0, len(all_chunks), BATCH_SIZE):
            batch = all_chunks[i : i + BATCH_SIZE]
            batch_db = FAISS.from_documents(batch, embedding_model)
            if final_db is None:
                final_db = batch_db
            else:
                final_db.merge_from(batch_db)
            logger.info(
                f"  Batch {i // BATCH_SIZE + 1}: "
                f"indexed chunks {i + 1}–{min(i + BATCH_SIZE, len(all_chunks))}"
            )

        # Save to a temp directory and upload to GCS.
        # Cloud Run's /app directory may be read-only, so we always save to
        # a temp dir first, then upload from there.
        import tempfile as _tf

        gcs_ok = False
        save_dir = _tf.mkdtemp(prefix="faiss_upload_")
        try:
            final_db.save_local(save_dir)
            logger.info(f"Saved FAISS index to temp dir: {save_dir}")

            if gcs_handler.gcs_enabled:
                gcs_ok = gcs_handler.upload_faiss_index(save_dir)
                if gcs_ok:
                    logger.info("✅ Uploaded updated FAISS index to GCS")
                else:
                    logger.warning("GCS upload returned False — check logs above")
        except Exception as save_err:
            logger.error(
                f"Failed to save/upload FAISS index: {save_err}", exc_info=True
            )

        # Update session state so queries immediately use the new index
        st.session_state.vectorstore = final_db
        # Also clear the cache so a fresh page load re-downloads from GCS
        get_vectorstore.clear()

        n_files = len(pdf_files)
        n_chunks = len(all_chunks)
        gcs_note = " and uploaded to GCS ☁️" if gcs_ok else " (local only)"
        msg = (
            f"✅ Successfully indexed {n_files} PDF(s) into "
            f"{n_chunks} chunks{gcs_note}."
        )
        return True, msg

    except Exception as e:
        logger.error(f"rebuild_vectorstore_from_pdfs failed: {e}", exc_info=True)
        return False, f"Failed to build index: {e}"


def main():
    """Main application function with comprehensive error handling"""

    # Page configuration
    st.set_page_config(page_title="Medical Chatbot", page_icon="🏥", layout="centered")

    st.title("🏥 Medical Chatbot")
    st.markdown("*Ask me anything about medical topics from the knowledge base*")

    # Initialize session state
    if "messages" not in st.session_state:
        st.session_state.messages = []
        logger.info("Initialized new chat session")

    if "initialized" not in st.session_state:
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
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Chat input
    if user_query := st.chat_input("💬 Ask your medical question here..."):
        # Display user message
        with st.chat_message("user"):
            st.markdown(user_query)
        st.session_state.messages.append({"role": "user", "content": user_query})

        # Process query and generate response
        try:
            with st.chat_message("assistant"):
                # Build chat history from last 5 exchanges (10 messages)
                MAX_HISTORY = 10  # 5 user + 5 assistant messages
                recent = st.session_state.messages[-MAX_HISTORY:]
                chat_history = "\n".join(
                    f"{'User' if m['role'] == 'user' else 'Assistant'}: {m['content'][:200]}"
                    for m in recent
                ) if recent else "(No previous conversation)"

                # Wrap entire RAG flow in a single LangSmith trace
                @ls_traceable(
                    name="medical_rag_query",
                    metadata={"model": DEFAULT_MODEL, "retriever_k": 3},
                    tags=["rag", "medical", "chatbot"],
                )
                def _run_rag_pipeline(
                    query, vectorstore, prompt_template, llm, history
                ):
                    """Single traced function covering retrieval → LLM → guardrails."""
                    fp, docs = prepare_rag_context(
                        query, vectorstore, prompt_template, history
                    )
                    return fp, docs

                # Phase 1: Retrieve context (brief spinner)
                with st.spinner("🔍 Searching knowledge base..."):
                    formatted_prompt, retrieved_docs = _run_rag_pipeline(
                        user_query,
                        st.session_state.vectorstore,
                        st.session_state.prompt,
                        st.session_state.llm,
                        chat_history,
                    )

                # Phase 2: Stream LLM response token by token
                response_container = st.empty()
                with response_container:
                    streamed_answer = st.write_stream(
                        stream_llm_tokens(st.session_state.llm, formatted_prompt)
                    )

                # Phase 3: Post-stream guardrails validation
                is_safe, final_output = validate_response(
                    streamed_answer, user_query, retrieved_docs
                )

                if not is_safe:
                    # Guardrails blocked — replace streamed content with fallback
                    response_container.empty()
                    response_container.warning(final_output)
                    answer = final_output
                elif final_output != streamed_answer:
                    # Guardrails modified the output (e.g., added disclaimer)
                    response_container.empty()
                    response_container.markdown(final_output)
                    answer = final_output
                else:
                    answer = streamed_answer

                # Add feedback buttons (if LangSmith is enabled)
                if is_langsmith_enabled():
                    st.markdown("---")
                    st.markdown("**Was this answer helpful?**")
                    col1, col2, col3 = st.columns([1, 1, 4])

                    # Get current run ID for feedback
                    run_id = get_current_run_id()

                    with col1:
                        if st.button(
                            "👍 Yes",
                            key=f"thumbs_up_{len(st.session_state.messages)}",
                        ):
                            if run_id:
                                create_feedback(
                                    run_id=run_id,
                                    key="user_rating",
                                    score=1.0,
                                    comment="Helpful answer",
                                )
                                st.success("Thanks for your feedback!")
                                logger.info(
                                    f"Positive feedback recorded for run {run_id}"
                                )

                    with col2:
                        if st.button(
                            "👎 No",
                            key=f"thumbs_down_{len(st.session_state.messages)}",
                        ):
                            if run_id:
                                create_feedback(
                                    run_id=run_id,
                                    key="user_rating",
                                    score=0.0,
                                    comment="Not helpful",
                                )
                                st.warning(
                                    "Thanks for your feedback. We'll work to improve!"
                                )
                                logger.info(
                                    f"Negative feedback recorded for run {run_id}"
                                )

            st.session_state.messages.append({"role": "assistant", "content": answer})
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

        st.divider()

        # ── Knowledge Base section ──────────────────────────────────────────
        st.header("📚 Knowledge Base")

        # Show current index source & metadata
        if gcs_handler.gcs_enabled:
            meta = gcs_handler.get_index_metadata()
            if meta["exists"]:
                last_updated = meta["last_updated"]
                updated_str = (
                    last_updated.strftime("%d %b %Y, %H:%M UTC")
                    if last_updated
                    else "unknown"
                )
                st.success(
                    f"☁️ **GCS** — {meta['total_size_kb']:.0f} KB\n\n"
                    f"Updated: {updated_str}"
                )
            else:
                st.warning("☁️ GCS configured but no index found yet.")
        elif os.path.exists(DB_FAISS_PATH):
            st.info("📂 **Local** FAISS index loaded")
        else:
            st.error("❌ No index found. Upload PDFs below.")

        st.divider()

        # ── PDF Upload UI ───────────────────────────────────────────────────
        st.subheader("⬆️ Update Knowledge Base")
        st.caption(
            "Upload medical PDFs to add to or rebuild the knowledge base. "
            "Changes take effect immediately after indexing."
        )

        uploaded_files = st.file_uploader(
            "Drop PDF files here",
            type=["pdf"],
            accept_multiple_files=True,
            label_visibility="collapsed",
            key="pdf_uploader",
        )

        # Cache uploaded file bytes in session state immediately so they
        # survive the Streamlit rerun triggered by the button click.
        # Without this, st.file_uploader data is lost on Cloud Run reruns.
        if uploaded_files:
            st.session_state["cached_pdfs"] = [
                {"name": f.name, "bytes": f.getbuffer().tobytes()}
                for f in uploaded_files
            ]
        elif "cached_pdfs" not in st.session_state:
            st.session_state["cached_pdfs"] = []

        cached = st.session_state.get("cached_pdfs", [])

        if cached:
            st.caption(f"📄 {len(cached)} file(s) selected")
            col_add, col_rebuild = st.columns(2)

            with col_add:
                if st.button(
                    "⚡ Add to Index",
                    help="Merge these PDFs into the existing index",
                    use_container_width=True,
                    key="btn_add_index",
                ):
                    with st.spinner("Embedding and indexing PDFs..."):
                        ok, msg = rebuild_vectorstore_from_pdfs(cached, mode="add")
                    if ok:
                        st.success(msg)
                        logger.info(msg)
                        st.session_state.pop("cached_pdfs", None)
                        st.rerun()
                    else:
                        st.error(msg)

            with col_rebuild:
                if st.button(
                    "🔄 Rebuild All",
                    help="Delete existing index and rebuild from these PDFs only",
                    use_container_width=True,
                    key="btn_rebuild_index",
                ):
                    with st.spinner("Rebuilding full index from scratch..."):
                        ok, msg = rebuild_vectorstore_from_pdfs(cached, mode="rebuild")
                    if ok:
                        st.success(msg)
                        logger.info(msg)
                        st.session_state.pop("cached_pdfs", None)
                        st.rerun()
                    else:
                        st.error(msg)
        else:
            st.caption("No files selected yet.")

        st.divider()

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
