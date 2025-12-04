"""
ChromaDB retriever for RAG with Phoenix instrumentation using OpenInference conventions.
"""

import logging
import json
from typing import List, Dict, Optional
from dataclasses import dataclass
from pathlib import Path

from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode, SpanKind

import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer

from app.config import settings

# OpenInference semantic conventions
from openinference.semconv.trace import (
    SpanAttributes,
    OpenInferenceSpanKindValues,
    DocumentAttributes,
)

logger = logging.getLogger(__name__)


@dataclass
class RetrievedDocument:
    """Document retrieved from vector store"""
    id: str
    content: str
    title: str
    url: str
    doc_id: str
    chunk_index: int
    distance: float  # Similarity score


class QuantumWikiRetriever:
    """Retriever for quantum physics Wikipedia corpus"""

    def __init__(
        self,
        chroma_dir: str = None,
        collection_name: str = None,
        embedding_model_name: str = None,
        device: str = "cpu"
    ):
        self.chroma_dir = Path(chroma_dir or settings.chroma_persist_dir)
        self.collection_name = collection_name or settings.chroma_collection_name
        self.embedding_model_name = embedding_model_name or settings.embedding_model
        self.device = device

        self.tracer = trace.get_tracer(__name__)

        # Initialize components
        self._init_embedding_model()
        self._init_chroma()

    def _init_embedding_model(self):
        """Initialize the embedding model"""
        logger.info(f"Loading embedding model: {self.embedding_model_name}")
        self.embedding_model = SentenceTransformer(
            self.embedding_model_name,
            device=self.device
        )
        logger.info("Embedding model loaded")

    def _init_chroma(self):
        """Initialize ChromaDB client and collection"""
        if not self.chroma_dir.exists():
            raise FileNotFoundError(
                f"ChromaDB directory not found: {self.chroma_dir}. "
                "Please run build_index.py first."
            )

        logger.info(f"Connecting to ChromaDB at {self.chroma_dir}")
        self.chroma_client = chromadb.PersistentClient(
            path=str(self.chroma_dir),
            settings=Settings(anonymized_telemetry=False)
        )

        try:
            self.collection = self.chroma_client.get_collection(
                name=self.collection_name
            )
            count = self.collection.count()
            logger.info(f"Connected to collection '{self.collection_name}' ({count} documents)")
        except Exception as e:
            raise RuntimeError(
                f"Failed to load collection '{self.collection_name}': {e}. "
                "Please run build_index.py first."
            )

    def retrieve(
        self,
        query: str,
        top_k: int = None,
        conversation_history: Optional[List[Dict]] = None
    ) -> List[RetrievedDocument]:
        """
        Retrieve relevant documents for a query.

        Args:
            query: User query
            top_k: Number of documents to retrieve
            conversation_history: Optional chat history for context (not used yet)

        Returns:
            List of retrieved documents
        """
        top_k = top_k or settings.rag_top_k

        with self.tracer.start_as_current_span(
            "rag.retrieve",
            kind=SpanKind.CLIENT
        ) as span:
            try:
                # Set OpenInference span kind
                span.set_attribute(
                    SpanAttributes.OPENINFERENCE_SPAN_KIND,
                    OpenInferenceSpanKindValues.RETRIEVER.value
                )

                # Set retrieval query using OpenInference conventions
                span.set_attribute(SpanAttributes.INPUT_VALUE, query)

                # Generate query embedding
                logger.debug(f"Generating embedding for query: {query[:100]}...")
                query_embedding = self.embedding_model.encode(
                    [query],
                    convert_to_numpy=True
                ).tolist()

                # Query ChromaDB
                logger.debug(f"Querying ChromaDB for top {top_k} results")
                results = self.collection.query(
                    query_embeddings=query_embedding,
                    n_results=top_k,
                    include=["documents", "metadatas", "distances"]
                )

                # Parse results and set document attributes
                documents = []
                if results['documents'] and results['documents'][0]:
                    for idx, (doc_text, metadata, distance) in enumerate(zip(
                        results['documents'][0],
                        results['metadatas'][0],
                        results['distances'][0]
                    )):
                        retrieved_doc = RetrievedDocument(
                            id=metadata.get('doc_id', 'unknown'),
                            content=doc_text,
                            title=metadata.get('title', 'Unknown'),
                            url=metadata.get('url', ''),
                            doc_id=metadata.get('doc_id', ''),
                            chunk_index=metadata.get('chunk_index', 0),
                            distance=distance
                        )
                        documents.append(retrieved_doc)

                        # Set document attributes using OpenInference conventions
                        doc_prefix = f"{SpanAttributes.RETRIEVAL_DOCUMENTS}.{idx}"
                        span.set_attribute(
                            f"{doc_prefix}.{DocumentAttributes.DOCUMENT_ID}",
                            retrieved_doc.id
                        )
                        span.set_attribute(
                            f"{doc_prefix}.{DocumentAttributes.DOCUMENT_CONTENT}",
                            doc_text
                        )
                        span.set_attribute(
                            f"{doc_prefix}.{DocumentAttributes.DOCUMENT_METADATA}",
                            json.dumps({
                                "title": retrieved_doc.title,
                                "url": retrieved_doc.url,
                                "chunk_index": retrieved_doc.chunk_index
                            })
                        )
                        span.set_attribute(
                            f"{doc_prefix}.{DocumentAttributes.DOCUMENT_SCORE}",
                            float(distance)
                        )

                span.set_status(Status(StatusCode.OK))
                logger.info(f"Retrieved {len(documents)} documents for query")

                return documents

            except Exception as e:
                logger.error(f"Error during retrieval: {e}")
                span.set_status(Status(StatusCode.ERROR, str(e)))
                span.record_exception(e)
                raise

    def format_context(self, documents: List[RetrievedDocument]) -> str:
        """
        Format retrieved documents into a context string for the LLM.

        Args:
            documents: List of retrieved documents

        Returns:
            Formatted context string
        """
        if not documents:
            return ""

        context_parts = []
        context_parts.append("# Retrieved Context from Wikipedia\n")

        for i, doc in enumerate(documents, 1):
            context_parts.append(f"\n## Source {i}: {doc.title}")
            context_parts.append(f"URL: {doc.url}")
            context_parts.append(f"\n{doc.content}\n")
            context_parts.append("-" * 80)

        return "\n".join(context_parts)

    def health_check(self) -> bool:
        """Check if retriever is working"""
        try:
            count = self.collection.count()
            logger.info(f"Retriever health check OK ({count} documents)")
            return count > 0
        except Exception as e:
            logger.error(f"Retriever health check failed: {e}")
            return False
