"""
Multi-Embedding Support for RAG System
Supports single, ensemble, and hybrid embedding strategies
"""

import os
from typing import List, Dict, Any, Optional
import numpy as np
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_openai import OpenAIEmbeddings
from langchain.embeddings.base import Embeddings
import yaml
from pathlib import Path


class MultiEmbedding(Embeddings):
    """
    Wrapper for multiple embedding models
    Supports ensemble and hybrid retrieval strategies
    """

    def __init__(self, config_path: str = None):
        """
        Initialize multi-embedding system

        Args:
            config_path: Path to config.yaml file
        """
        if config_path is None:
            config_path = Path(__file__).parent.parent / "config" / "config.yaml"

        with open(config_path, "r") as f:
            self.config = yaml.safe_load(f)

        self.embedding_config = self.config.get("embedding", {})
        self.strategy = self.embedding_config.get("strategy", "single")

        # Initialize embedding models
        self.primary_embedding = None
        self.secondary_embeddings = []
        self.weights = {}

        self._initialize_embeddings()

    def _initialize_embeddings(self):
        """Initialize all embedding models based on strategy"""

        if self.strategy == "single":
            # Single embedding model (backward compatible)
            model_name = self.embedding_config.get(
                "model", "sentence-transformers/all-MiniLM-L6-v2"
            )
            device = self.embedding_config.get("device", "cpu")

            self.primary_embedding = HuggingFaceEmbeddings(
                model_name=model_name, model_kwargs={"device": device}
            )
            print(f"✅ Loaded single embedding model: {model_name}")

        elif self.strategy in ["ensemble", "hybrid"]:
            # Multiple embedding models

            # Load primary model
            primary_config = self.embedding_config.get("primary", {})
            self.primary_embedding = self._load_embedding_model(primary_config)

            # Load secondary models
            secondary_configs = self.embedding_config.get("secondary", [])
            for sec_config in secondary_configs:
                embedding = self._load_embedding_model(sec_config)
                if embedding:
                    self.secondary_embeddings.append(embedding)

            # Set weights
            ensemble_weights = self.embedding_config.get("ensemble_weights", {})
            self.weights = {
                "primary": ensemble_weights.get("primary", 0.5),
                "secondary": ensemble_weights.get("secondary", []),
            }

            print("✅ Loaded ensemble embeddings:")
            print(f"   Primary: {primary_config.get('model')}")
            for i, sec_config in enumerate(secondary_configs):
                print(f"   Secondary {i + 1}: {sec_config.get('model')}")

    def _load_embedding_model(self, config: Dict[str, Any]) -> Optional[Embeddings]:
        """
        Load a single embedding model

        Args:
            config: Model configuration

        Returns:
            Embedding model instance
        """
        provider = config.get("provider", "huggingface")
        model_name = config.get("model")

        if not model_name:
            return None

        try:
            if provider == "huggingface":
                device = config.get("device", "cpu")
                return HuggingFaceEmbeddings(
                    model_name=model_name, model_kwargs={"device": device}
                )

            elif provider == "openai":
                api_key_env = config.get("api_key_env", "OPENAI_API_KEY")
                api_key = os.getenv(api_key_env)

                if not api_key:
                    print(f"⚠️ {api_key_env} not found, skipping {model_name}")
                    return None

                return OpenAIEmbeddings(model=model_name, openai_api_key=api_key)

            else:
                print(f"⚠️ Unknown provider: {provider}")
                return None

        except Exception as e:
            print(f"⚠️ Failed to load {model_name}: {e}")
            return None

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """
        Embed a list of documents

        Args:
            texts: List of documents to embed

        Returns:
            List of embedding vectors
        """
        if self.strategy == "single":
            return self.primary_embedding.embed_documents(texts)

        elif self.strategy == "ensemble":
            return self._ensemble_embed_documents(texts)

        elif self.strategy == "hybrid":
            # For hybrid, we use ensemble for now
            # Can be extended for sparse+dense hybrid
            return self._ensemble_embed_documents(texts)

        else:
            raise ValueError(f"Unknown strategy: {self.strategy}")

    def embed_query(self, text: str) -> List[float]:
        """
        Embed a single query

        Args:
            text: Query text to embed

        Returns:
            Embedding vector
        """
        if self.strategy == "single":
            return self.primary_embedding.embed_query(text)

        elif self.strategy == "ensemble":
            return self._ensemble_embed_query(text)

        elif self.strategy == "hybrid":
            return self._ensemble_embed_query(text)

        else:
            raise ValueError(f"Unknown strategy: {self.strategy}")

    def _ensemble_embed_documents(self, texts: List[str]) -> List[List[float]]:
        """
        Ensemble embedding for documents
        Combines multiple embedding models with weighted average

        Args:
            texts: List of documents

        Returns:
            List of ensemble embedding vectors
        """
        all_embeddings = []

        # Get primary embeddings
        primary_embeds = self.primary_embedding.embed_documents(texts)
        all_embeddings.append((primary_embeds, self.weights["primary"]))

        # Get secondary embeddings
        for i, sec_embedding in enumerate(self.secondary_embeddings):
            if i < len(self.weights["secondary"]):
                sec_embeds = sec_embedding.embed_documents(texts)
                weight = self.weights["secondary"][i]
                all_embeddings.append((sec_embeds, weight))

        # Combine embeddings
        return self._weighted_average_embeddings(all_embeddings)

    def _ensemble_embed_query(self, text: str) -> List[float]:
        """
        Ensemble embedding for query

        Args:
            text: Query text

        Returns:
            Ensemble embedding vector
        """
        all_embeddings = []

        # Get primary embedding
        primary_embed = self.primary_embedding.embed_query(text)
        all_embeddings.append((primary_embed, self.weights["primary"]))

        # Get secondary embeddings
        for i, sec_embedding in enumerate(self.secondary_embeddings):
            if i < len(self.weights["secondary"]):
                sec_embed = sec_embedding.embed_query(text)
                weight = self.weights["secondary"][i]
                all_embeddings.append((sec_embed, weight))

        # Combine embeddings
        combined = self._weighted_average_single_embedding(all_embeddings)
        return combined

    def _weighted_average_embeddings(
        self, embeddings_with_weights: List[tuple]
    ) -> List[List[float]]:
        """
        Weighted average of multiple embedding sets

        Args:
            embeddings_with_weights: List of (embeddings, weight) tuples

        Returns:
            Weighted average embeddings
        """
        if not embeddings_with_weights:
            return []

        # Get number of documents
        num_docs = len(embeddings_with_weights[0][0])

        # Initialize result
        result = []

        # For each document
        for doc_idx in range(num_docs):
            # Collect all embeddings for this document
            doc_embeddings = []
            for embeds, weight in embeddings_with_weights:
                doc_embeddings.append((embeds[doc_idx], weight))

            # Weighted average
            combined = self._weighted_average_single_embedding(doc_embeddings)
            result.append(combined)

        return result

    def _weighted_average_single_embedding(
        self, embeddings_with_weights: List[tuple]
    ) -> List[float]:
        """
        Weighted average of multiple embedding vectors

        Args:
            embeddings_with_weights: List of (embedding, weight) tuples

        Returns:
            Weighted average embedding
        """
        if not embeddings_with_weights:
            return []

        # Normalize embeddings to same dimension (use max dimension)
        max_dim = max(len(emb) for emb, _ in embeddings_with_weights)

        # Initialize result
        result = np.zeros(max_dim)

        # Weighted sum
        for embedding, weight in embeddings_with_weights:
            # Pad if needed
            if len(embedding) < max_dim:
                embedding = np.pad(embedding, (0, max_dim - len(embedding)))

            result += np.array(embedding) * weight

        # Normalize
        norm = np.linalg.norm(result)
        if norm > 0:
            result = result / norm

        return result.tolist()


def load_embeddings(config_path: str = None) -> Embeddings:
    """
    Load embedding model(s) based on configuration

    Args:
        config_path: Path to config.yaml

    Returns:
        Embedding model instance
    """
    try:
        multi_embedding = MultiEmbedding(config_path)
        return multi_embedding
    except Exception as e:
        print(f"⚠️ Failed to load multi-embedding: {e}")
        print("⚠️ Falling back to single embedding model")

        # Fallback to simple HuggingFace embedding
        return HuggingFaceEmbeddings(
            model_name="BAAI/bge-base-en-v1.5", model_kwargs={"device": "cpu"}
        )


# Example usage
if __name__ == "__main__":
    print("Testing Multi-Embedding System...")
    print("=" * 60)

    # Load embeddings
    embeddings = load_embeddings()

    # Test query embedding
    query = "What are the symptoms of diabetes?"
    query_embedding = embeddings.embed_query(query)

    print(f"\nQuery: {query}")
    print(f"Embedding dimension: {len(query_embedding)}")
    print(f"First 5 values: {query_embedding[:5]}")

    # Test document embedding
    docs = [
        "Diabetes symptoms include increased thirst and frequent urination.",
        "Common signs of diabetes are fatigue and blurred vision.",
    ]
    doc_embeddings = embeddings.embed_documents(docs)

    print(f"\nDocuments: {len(docs)}")
    print(f"Embedding dimensions: {[len(emb) for emb in doc_embeddings]}")

    print("\n" + "=" * 60)
    print("✅ Multi-embedding test complete!")
