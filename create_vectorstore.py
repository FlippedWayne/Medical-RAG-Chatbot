import os
import sys
from pathlib import Path
from typing import List

from langchain_community.document_loaders import PyPDFLoader, DirectoryLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document

from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Use centralized logger and exceptions
from src.utils.logger import get_logger
from src.utils.exceptions import VectorStoreError

# Import LangSmith observability
from langsmith import traceable

# Disable verbose logging from LangChain libraries
import logging
logging.getLogger("langchain").setLevel(logging.WARNING)
logging.getLogger("langchain_community").setLevel(logging.WARNING)
logging.getLogger("langchain_core").setLevel(logging.WARNING)
logging.getLogger("langsmith").setLevel(logging.WARNING)

# Initialize logger with custom log file (only once)
logger = get_logger(__name__, log_to_file=True, custom_log_file="vector_creation.log")

# Configure LangSmith for vector store creation tracking
os.environ["LANGCHAIN_PROJECT"] = "medical-chatbot-vectorstore"
os.environ["LANGCHAIN_TRACING_V2"] = "true"

# Get API key from environment
langsmith_api_key = os.getenv("LANGSMITH_API_KEY") or os.getenv("LANGCHAIN_API_KEY")
if langsmith_api_key:
    logger.info("✅ LangSmith tracing enabled for vector store creation")
    logger.info(f"📊 Project: medical-chatbot-vectorstore")
else:
    logger.warning("⚠️ LangSmith API key not found. Tracing disabled.")

# Load configuration from config.yaml
import yaml

def load_config():
    """Load configuration from config.yaml"""
    config_path = Path("src/config/config.yaml")
    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        logger.info(f"✅ Configuration loaded from {config_path}")
        return config
    except Exception as e:
        logger.warning(f"⚠️ Failed to load config: {e}. Using defaults.")
        return {}

# Load config
config = load_config()

# Get embedding configuration from config.yaml
embedding_config = config.get('embedding', {})

# Determine which embedding model to use based on strategy
strategy = embedding_config.get('strategy', 'single')
if strategy == 'single':
    # Use the legacy single model or primary model
    DEFAULT_EMBEDDING_MODEL = embedding_config.get('model') or \
                             embedding_config.get('primary', {}).get('model', 'sentence-transformers/all-MiniLM-L6-v2')
else:
    # For ensemble/hybrid, use primary model for vector store creation
    DEFAULT_EMBEDDING_MODEL = embedding_config.get('primary', {}).get('model', 'BAAI/bge-base-en-v1.5')

logger.info(f"📝 Using embedding model: {DEFAULT_EMBEDDING_MODEL}")
logger.info(f"📝 Embedding strategy: {strategy}")

# Constants
DATA_PATH = "data/"
DB_FAISS_PATH = "vectorstore/db_faiss"
CHUNK_SIZE = 500
CHUNK_OVERLAP = 50


class DocumentLoadError(Exception):
    """Custom exception for document loading errors"""
    pass


class EmbeddingError(Exception):
    """Custom exception for embedding errors"""
    pass


# VectorStoreError is imported from src.utils.exceptions


def validate_data_directory(data_path: str) -> None:
    """
    Validate that the data directory exists and contains PDF files.
    
    Args:
        data_path: Path to data directory
        
    Raises:
        DocumentLoadError: If directory doesn't exist or has no PDFs
    """
    try:
        path = Path(data_path)
        
        # Check if directory exists
        if not path.exists():
            error_msg = f"Data directory not found: {data_path}"
            logger.error(error_msg)
            raise DocumentLoadError(error_msg)
        
        if not path.is_dir():
            error_msg = f"Path is not a directory: {data_path}"
            logger.error(error_msg)
            raise DocumentLoadError(error_msg)
        
        # Check for PDF files
        pdf_files = list(path.glob('*.pdf'))
        if not pdf_files:
            error_msg = f"No PDF files found in {data_path}"
            logger.error(error_msg)
            raise DocumentLoadError(error_msg)
        
        logger.info(f"Found {len(pdf_files)} PDF file(s) in {data_path}")
        for pdf in pdf_files:
            logger.info(f"  - {pdf.name} ({pdf.stat().st_size / 1024:.2f} KB)")
            
    except DocumentLoadError:
        raise
    except Exception as e:
        error_msg = f"Error validating data directory: {str(e)}"
        logger.error(error_msg)
        raise DocumentLoadError(error_msg)


@traceable(name="load_pdf_files", tags=["pdf", "loading"])
def load_pdf_files(data_path: str) -> List[Document]:
    """
    Load PDF files from directory with error handling.
    
    Args:
        data_path: Path to directory containing PDF files
        
    Returns:
        List[Document]: List of loaded documents
        
    Raises:
        DocumentLoadError: If PDF loading fails
    """
    try:
        logger.info(f"📄 Loading PDF files from {data_path}")
        
        # Validate directory first
        validate_data_directory(data_path)
        
        # Create directory loader
        loader = DirectoryLoader(
            data_path,
            glob='*.pdf',
            loader_cls=PyPDFLoader,
            show_progress=True
        )
        
        # Load documents
        documents = loader.load()
        
        if not documents:
            error_msg = "No documents were loaded from PDF files"
            logger.error(error_msg)
            raise DocumentLoadError(error_msg)
        
        logger.info(f"✅ Successfully loaded {len(documents)} pages from PDF files")
        
        # Log output metadata for LangSmith
        from langsmith import get_current_run_tree
        run = get_current_run_tree()
        if run:
            run.extra = run.extra or {}
            run.extra.update({
                "num_documents": len(documents),
                "data_path": data_path
            })
        
        return documents
        
    except DocumentLoadError:
        raise
    except Exception as e:
        error_msg = f"Failed to load PDF files: {str(e)}"
        logger.error(error_msg)
        raise DocumentLoadError(error_msg)


@traceable(name="create_text_chunks", tags=["chunking", "text_splitting"])
def create_chunks(documents: List[Document], chunk_size: int = CHUNK_SIZE, 
                  chunk_overlap: int = CHUNK_OVERLAP) -> List[Document]:
    """
    Split documents into chunks with error handling.
    
    Args:
        documents: List of documents to chunk
        chunk_size: Size of each chunk
        chunk_overlap: Overlap between chunks
        
    Returns:
        List[Document]: List of chunked documents
        
    Raises:
        DocumentLoadError: If chunking fails
    """
    try:
        logger.info(f"✂️  Creating chunks (size={chunk_size}, overlap={chunk_overlap})")
        
        if not documents:
            raise ValueError("No documents provided for chunking")
        
        # Validate parameters
        if chunk_size <= 0:
            raise ValueError(f"Invalid chunk_size: {chunk_size}")
        if chunk_overlap < 0 or chunk_overlap >= chunk_size:
            raise ValueError(f"Invalid chunk_overlap: {chunk_overlap}")
        
        # Create text splitter
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap
        )
        
        # Split documents
        text_chunks = text_splitter.split_documents(documents)
        
        if not text_chunks:
            error_msg = "No chunks were created from documents"
            logger.error(error_msg)
            raise DocumentLoadError(error_msg)
        
        logger.info(f"✅ Successfully created {len(text_chunks)} text chunks")
        
        # Log statistics
        avg_chunk_size = sum(len(chunk.page_content) for chunk in text_chunks) / len(text_chunks)
        logger.info(f"📊 Average chunk size: {avg_chunk_size:.0f} characters")
        
        # Log output metadata for LangSmith
        from langsmith import get_current_run_tree
        run = get_current_run_tree()
        if run:
            run.extra = run.extra or {}
            run.extra.update({
                "num_chunks": len(text_chunks),
                "avg_chunk_size": int(avg_chunk_size),
                "chunk_size": chunk_size,
                "chunk_overlap": chunk_overlap
            })
        
        return text_chunks
        
    except ValueError as e:
        logger.error(f"Validation error: {str(e)}")
        raise DocumentLoadError(str(e))
    except Exception as e:
        error_msg = f"Failed to create chunks: {str(e)}"
        logger.error(error_msg)
        raise DocumentLoadError(error_msg)


@traceable(name="load_embedding_model", tags=["embeddings", "model"])
def get_embedding_model(model_name: str = DEFAULT_EMBEDDING_MODEL) -> HuggingFaceEmbeddings:
    """
    Initialize embedding model with error handling.
    
    Args:
        model_name: Name of the HuggingFace model
        
    Returns:
        HuggingFaceEmbeddings: Initialized embedding model
        
    Raises:
        EmbeddingError: If model initialization fails
    """
    try:
        logger.info(f"🧠 Loading embedding model: {model_name}")
        
        embedding_model = HuggingFaceEmbeddings(model_name=model_name)
        
        logger.info("✅ Embedding model loaded successfully")
        
        # Log output metadata for LangSmith
        from langsmith import get_current_run_tree
        run = get_current_run_tree()
        if run:
            run.extra = run.extra or {}
            run.extra.update({
                "model_name": model_name
            })
        
        return embedding_model
        
    except Exception as e:
        error_msg = f"Failed to load embedding model '{model_name}': {str(e)}"
        logger.error(error_msg)
        raise EmbeddingError(error_msg)


@traceable(name="create_faiss_vectorstore", tags=["faiss", "storage"])
def create_vector_store(text_chunks: List[Document], 
                       embedding_model: HuggingFaceEmbeddings,
                       db_path: str = DB_FAISS_PATH) -> None:
    """
    Create and save FAISS vector store with error handling.
    
    Args:
        text_chunks: List of document chunks
        embedding_model: Embedding model instance
        db_path: Path to save the vector store
        
    Raises:
        VectorStoreError: If vector store creation fails
    """
    try:
        logger.info(f"💾 Creating FAISS vector store with {len(text_chunks)} chunks")
        
        if not text_chunks:
            raise ValueError("No text chunks provided")
        
        # Create output directory if it doesn't exist
        output_path = Path(db_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        logger.info(f"📁 Output directory: {output_path.parent}")
        
        # Create FAISS database
        db = FAISS.from_documents(text_chunks, embedding_model)
        
        # Save to disk
        db.save_local(db_path)
        
        logger.info(f"✅ Successfully saved vector store to {db_path}")
        
        # Verify the save
        if not output_path.exists():
            raise VectorStoreError(f"Vector store was not saved to {db_path}")
        
        # Log file sizes
        total_size = 0
        for file in output_path.parent.glob('*'):
            if file.is_file():
                file_size = file.stat().st_size / 1024
                total_size += file_size
                logger.info(f"  - {file.name}: {file_size:.2f} KB")
        
        # Log output metadata for LangSmith
        from langsmith import get_current_run_tree
        run = get_current_run_tree()
        if run:
            run.extra = run.extra or {}
            run.extra.update({
                "num_chunks": len(text_chunks),
                "db_path": db_path,
                "total_size_kb": int(total_size)
            })
                
    except ValueError as e:
        logger.error(f"Validation error: {str(e)}")
        raise VectorStoreError(str(e))
    except Exception as e:
        error_msg = f"Failed to create vector store: {str(e)}"
        logger.error(error_msg)
        raise VectorStoreError(error_msg)


@traceable(
    name="vectorstore_creation_pipeline",
    metadata={"data_path": DATA_PATH, "db_path": DB_FAISS_PATH, "chunk_size": CHUNK_SIZE, "embedding_model": DEFAULT_EMBEDDING_MODEL},
    tags=["vectorstore", "pipeline", "setup"]
)
def main():
    """Main function to create vector store with comprehensive error handling"""
    
    print("=" * 60)
    print("MEDICAL CHATBOT - VECTOR STORE CREATION")
    print("=" * 60)
    print()
    
    try:
        # Step 1: Load PDF files
        print("📄 Step 1: Loading PDF files...")
        logger.info("=" * 60)
        logger.info("Starting vector store creation process")
        logger.info("=" * 60)
        
        documents = load_pdf_files(DATA_PATH)
        print(f"✅ Loaded {len(documents)} pages from PDF files")
        print()
        
        # Step 2: Create chunks
        print("✂️  Step 2: Creating text chunks...")
        text_chunks = create_chunks(documents)
        print(f"✅ Created {len(text_chunks)} text chunks")
        print()
        
        # Step 3: Load embedding model
        print("🧠 Step 3: Loading embedding model...")
        embedding_model = get_embedding_model()
        print(f"✅ Loaded embedding model: {DEFAULT_EMBEDDING_MODEL}")
        print()
        
        # Step 4: Create and save vector store
        print("💾 Step 4: Creating FAISS vector store...")
        create_vector_store(text_chunks, embedding_model)
        print(f"✅ Vector store saved to {DB_FAISS_PATH}")
        print()
        
        # Success summary
        print("=" * 60)
        print("✅ SUCCESS! Vector store created successfully")
        print("=" * 60)
        print()
        print("📊 Summary:")
        print(f"  - PDF Pages Loaded: {len(documents)}")
        print(f"  - Text Chunks Created: {len(text_chunks)}")
        print(f"  - Vector Store Location: {DB_FAISS_PATH}")
        print()
        print("🚀 You can now run the chatbot with: streamlit run app.py")
        print()
        
        logger.info("Vector store creation completed successfully")
        return 0
        
    except (DocumentLoadError, EmbeddingError, VectorStoreError) as e:
        print()
        print("=" * 60)
        print("❌ ERROR OCCURRED")
        print("=" * 60)
        print(f"Error Type: {type(e).__name__}")
        print(f"Error Message: {str(e)}")
        print()
        print("💡 Suggestions:")
        
        if isinstance(e, DocumentLoadError):
            print("  - Ensure PDF files are in the 'data/' directory")
            print("  - Check that PDF files are not corrupted")
            print("  - Verify file permissions")
        elif isinstance(e, EmbeddingError):
            print("  - Check your internet connection")
            print("  - Ensure you have enough disk space")
            print("  - Try running again (model will be downloaded)")
        elif isinstance(e, VectorStoreError):
            print("  - Ensure you have write permissions")
            print("  - Check available disk space")
            print("  - Verify the vectorstore directory is accessible")
        
        print()
        print("📝 Check 'vector_creation.log' for detailed error information")
        print()
        
        logger.error(f"Vector store creation failed: {str(e)}", exc_info=True)
        return 1
        
    except Exception as e:
        print()
        print("=" * 60)
        print("❌ UNEXPECTED ERROR")
        print("=" * 60)
        print(f"Error: {str(e)}")
        print()
        print("📝 Check 'vector_creation.log' for detailed error information")
        print()
        
        logger.critical(f"Unexpected error: {str(e)}", exc_info=True)
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
