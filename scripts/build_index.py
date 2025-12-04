"""
Build ChromaDB vector index from scraped Wikipedia corpus.
Chunks documents, generates embeddings, and stores in persistent ChromaDB.
"""

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import List, Dict
import re

import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DocumentChunker:
    """Chunks documents into overlapping segments"""

    def __init__(self, chunk_size: int = 800, chunk_overlap: int = 100):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def chunk_text(self, text: str, doc_id: str, metadata: Dict) -> List[Dict]:
        """Split text into overlapping chunks"""
        # Split into sentences (simple approach)
        sentences = re.split(r'(?<=[.!?])\s+', text)

        chunks = []
        current_chunk = []
        current_length = 0

        for sentence in sentences:
            sentence_length = len(sentence)

            # If adding this sentence exceeds chunk size, save current chunk
            if current_length + sentence_length > self.chunk_size and current_chunk:
                chunk_text = ' '.join(current_chunk)
                chunks.append(chunk_text)

                # Keep overlap for context
                overlap_sentences = []
                overlap_length = 0
                for s in reversed(current_chunk):
                    if overlap_length + len(s) <= self.chunk_overlap:
                        overlap_sentences.insert(0, s)
                        overlap_length += len(s)
                    else:
                        break

                current_chunk = overlap_sentences
                current_length = overlap_length

            current_chunk.append(sentence)
            current_length += sentence_length

        # Add remaining chunk
        if current_chunk:
            chunks.append(' '.join(current_chunk))

        # Create chunk documents with metadata
        chunk_docs = []
        for i, chunk_text in enumerate(chunks):
            chunk_doc = {
                'id': f"{doc_id}_chunk_{i}",
                'text': chunk_text,
                'metadata': {
                    **metadata,
                    'chunk_index': i,
                    'total_chunks': len(chunks)
                }
            }
            chunk_docs.append(chunk_doc)

        return chunk_docs


class CorpusIndexer:
    """Build and manage ChromaDB index for document corpus"""

    def __init__(
        self,
        embedding_model_name: str = "sentence-transformers/all-MiniLM-L6-v2",
        chroma_dir: str = ".chroma/quantum_wiki",
        collection_name: str = "quantum_wiki",
        device: str = "cpu"
    ):
        self.embedding_model_name = embedding_model_name
        self.chroma_dir = Path(chroma_dir)
        self.collection_name = collection_name
        self.device = device

        # Initialize embedding model
        logger.info(f"Loading embedding model: {embedding_model_name}")
        self.embedding_model = SentenceTransformer(embedding_model_name, device=device)
        logger.info(f"Embedding model loaded (device: {device})")

        # Initialize ChromaDB
        self.chroma_client = None
        self.collection = None

    def initialize_chroma(self):
        """Initialize ChromaDB client and collection"""
        self.chroma_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"Initializing ChromaDB at {self.chroma_dir}")

        self.chroma_client = chromadb.PersistentClient(
            path=str(self.chroma_dir),
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )

        # Get or create collection
        try:
            self.collection = self.chroma_client.get_collection(name=self.collection_name)
            logger.info(f"Using existing collection: {self.collection_name}")

            # Optional: delete and recreate for fresh index
            logger.info("Deleting existing collection for fresh index...")
            self.chroma_client.delete_collection(name=self.collection_name)
            self.collection = self.chroma_client.create_collection(
                name=self.collection_name,
                metadata={"description": "Quantum physics Wikipedia articles"}
            )
            logger.info(f"Created fresh collection: {self.collection_name}")

        except Exception:
            self.collection = self.chroma_client.create_collection(
                name=self.collection_name,
                metadata={"description": "Quantum physics Wikipedia articles"}
            )
            logger.info(f"Created new collection: {self.collection_name}")

    def load_corpus(self, corpus_dir: Path) -> List[Dict]:
        """Load all documents from corpus directory"""
        logger.info(f"Loading corpus from {corpus_dir}")

        if not corpus_dir.exists():
            logger.error(f"Corpus directory not found: {corpus_dir}")
            sys.exit(1)

        documents = []
        json_files = list(corpus_dir.glob("*.json"))

        # Skip index.json
        json_files = [f for f in json_files if f.name != "index.json"]

        logger.info(f"Found {len(json_files)} document files")

        for json_file in json_files:
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    doc = json.load(f)
                    documents.append(doc)
            except Exception as e:
                logger.error(f"Error loading {json_file}: {e}")

        logger.info(f"Loaded {len(documents)} documents")
        return documents

    def index_documents(self, documents: List[Dict], chunk_size: int = 800, chunk_overlap: int = 100):
        """Chunk documents and add to ChromaDB with embeddings"""
        chunker = DocumentChunker(chunk_size=chunk_size, chunk_overlap=chunk_overlap)

        all_chunks = []
        for doc in documents:
            doc_id = doc['id']
            content = doc['content']
            metadata = {
                'title': doc['title'],
                'url': doc['url'],
                'doc_id': doc_id
            }

            chunks = chunker.chunk_text(content, doc_id, metadata)
            all_chunks.extend(chunks)

        logger.info(f"Created {len(all_chunks)} chunks from {len(documents)} documents")

        # Process in batches
        batch_size = 100
        total_batches = (len(all_chunks) + batch_size - 1) // batch_size

        for i in range(0, len(all_chunks), batch_size):
            batch = all_chunks[i:i + batch_size]
            batch_num = i // batch_size + 1

            logger.info(f"Processing batch {batch_num}/{total_batches} ({len(batch)} chunks)")

            # Prepare batch data
            ids = [chunk['id'] for chunk in batch]
            texts = [chunk['text'] for chunk in batch]
            metadatas = [chunk['metadata'] for chunk in batch]

            # Generate embeddings
            embeddings = self.embedding_model.encode(
                texts,
                show_progress_bar=False,
                convert_to_numpy=True
            ).tolist()

            # Add to collection
            self.collection.add(
                ids=ids,
                embeddings=embeddings,
                documents=texts,
                metadatas=metadatas
            )

        logger.info(f"Successfully indexed {len(all_chunks)} chunks")

        # Get collection stats
        count = self.collection.count()
        logger.info(f"Collection now contains {count} documents")

    def verify_index(self):
        """Run a test query to verify index is working"""
        logger.info("Verifying index with test query...")

        test_query = "What is quantum entanglement?"
        query_embedding = self.embedding_model.encode([test_query]).tolist()

        results = self.collection.query(
            query_embeddings=query_embedding,
            n_results=3
        )

        logger.info(f"Test query: '{test_query}'")
        logger.info(f"Retrieved {len(results['documents'][0])} results:")

        for i, (doc, metadata) in enumerate(zip(results['documents'][0], results['metadatas'][0])):
            logger.info(f"  {i+1}. {metadata['title']} (chunk {metadata['chunk_index']})")
            logger.info(f"     {doc[:100]}...")

        logger.info("Index verification complete!")


def main():
    parser = argparse.ArgumentParser(description='Build ChromaDB index from Wikipedia corpus')
    parser.add_argument(
        '--corpus-dir',
        type=str,
        default='data/corpus/quantum',
        help='Directory containing scraped corpus JSON files'
    )
    parser.add_argument(
        '--chroma-dir',
        type=str,
        default='.chroma/quantum_wiki',
        help='Directory for ChromaDB persistent storage'
    )
    parser.add_argument(
        '--collection-name',
        type=str,
        default='quantum_wiki',
        help='Name of ChromaDB collection'
    )
    parser.add_argument(
        '--embedding-model',
        type=str,
        default='sentence-transformers/all-MiniLM-L6-v2',
        help='Hugging Face embedding model name'
    )
    parser.add_argument(
        '--chunk-size',
        type=int,
        default=800,
        help='Target chunk size in characters'
    )
    parser.add_argument(
        '--chunk-overlap',
        type=int,
        default=100,
        help='Overlap between chunks in characters'
    )
    parser.add_argument(
        '--device',
        type=str,
        default='cpu',
        choices=['cpu', 'cuda', 'mps'],
        help='Device for embedding model (cpu, cuda, mps)'
    )

    args = parser.parse_args()

    # Initialize indexer
    indexer = CorpusIndexer(
        embedding_model_name=args.embedding_model,
        chroma_dir=args.chroma_dir,
        collection_name=args.collection_name,
        device=args.device
    )

    # Initialize ChromaDB
    indexer.initialize_chroma()

    # Load corpus
    corpus_dir = Path(args.corpus_dir)
    documents = indexer.load_corpus(corpus_dir)

    if not documents:
        logger.error("No documents found to index!")
        sys.exit(1)

    # Index documents
    indexer.index_documents(
        documents,
        chunk_size=args.chunk_size,
        chunk_overlap=args.chunk_overlap
    )

    # Verify
    indexer.verify_index()

    logger.info("Indexing complete!")


if __name__ == '__main__':
    main()
