"""
Embeddings utility module for financial text using FinGPT-2 and Qdrant.
Provides functions for generating and storing embeddings of financial text.
"""
import os
from typing import Optional, List, Dict, Any
import numpy as np
from functools import lru_cache
import torch
from transformers import AutoTokenizer, AutoModel
from qdrant_client import QdrantClient
from qdrant_client.http import models
from qdrant_client.http.models import Distance, VectorParams
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Constants
MODEL_NAME = "FinGPT/fingpt-sentiment-en"  # FinGPT-2 model for financial text
EMBEDDING_DIM = 768  # FinGPT-2 embedding dimension
COLLECTION_NAME = "buffett_db"
QDRANT_URL = os.getenv("QDRANT_URL", "localhost")
QDRANT_PORT = int(os.getenv("QDRANT_PORT", "6333"))

@lru_cache(maxsize=1)
def get_llm() -> tuple[AutoTokenizer, AutoModel]:
    """
    Get cached FinGPT-2 model and tokenizer.
    
    Returns
    -------
    tuple[AutoTokenizer, AutoModel]
        Cached tokenizer and model instances
    """
    logger.info("Loading FinGPT-2 model and tokenizer...")
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
    model = AutoModel.from_pretrained(MODEL_NAME)
    return tokenizer, model

def get_qdrant_client() -> QdrantClient:
    """
    Get Qdrant client instance.
    
    Returns
    -------
    QdrantClient
        Qdrant client instance
    """
    return QdrantClient(url=QDRANT_URL, port=QDRANT_PORT)

def init_collection() -> None:
    """Initialize Qdrant collection if it doesn't exist."""
    client = get_qdrant_client()
    
    # Check if collection exists
    collections = client.get_collections().collections
    collection_names = [collection.name for collection in collections]
    
    if COLLECTION_NAME not in collection_names:
        logger.info(f"Creating collection {COLLECTION_NAME}...")
        client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=VectorParams(size=EMBEDDING_DIM, distance=Distance.COSINE)
        )

def embed(text: str, store: bool = True) -> np.ndarray:
    """
    Generate embedding for text using FinGPT-2.
    
    Parameters
    ----------
    text : str
        Input text to embed
    store : bool, optional
        Whether to store the embedding in Qdrant, by default True
    
    Returns
    -------
    np.ndarray
        Embedding vector
    """
    # Get model and tokenizer
    tokenizer, model = get_llm()
    
    # Tokenize and generate embedding
    inputs = tokenizer(text, return_tensors="pt", padding=True, truncation=True, max_length=512)
    with torch.no_grad():
        outputs = model(**inputs)
    
    # Use [CLS] token embedding as sentence embedding
    embedding = outputs.last_hidden_state[:, 0, :].numpy()
    
    if store:
        # Store in Qdrant
        client = get_qdrant_client()
        client.upsert(
            collection_name=COLLECTION_NAME,
            points=[
                models.PointStruct(
                    id=hash(text),  # Simple hash as ID
                    vector=embedding[0].tolist(),
                    payload={"text": text}
                )
            ]
        )
    
    return embedding[0]

def search_similar(query: str, limit: int = 5) -> List[Dict[str, Any]]:
    """
    Search for similar texts using embedding similarity.
    
    Parameters
    ----------
    query : str
        Query text
    limit : int, optional
        Maximum number of results to return, by default 5
    
    Returns
    -------
    List[Dict[str, Any]]
        List of similar texts with their similarity scores
    """
    # Generate query embedding
    query_embedding = embed(query, store=False)
    
    # Search in Qdrant
    client = get_qdrant_client()
    search_result = client.search(
        collection_name=COLLECTION_NAME,
        query_vector=query_embedding.tolist(),
        limit=limit
    )
    
    # Format results
    results = []
    for scored_point in search_result:
        results.append({
            "text": scored_point.payload["text"],
            "score": scored_point.score
        })
    
    return results

def clear_collection() -> None:
    """Clear all vectors from the collection."""
    client = get_qdrant_client()
    client.delete_collection(collection_name=COLLECTION_NAME)
    init_collection() 