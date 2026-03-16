import uuid
import threading
from datetime import datetime
from typing import Optional

from backend.config.settings import get_settings
from backend.utils.logger import get_logger

logger = get_logger(__name__)

# ChromaDB client and collection are module-level singletons.
# They're initialized lazily on first use via _get_collection().
_chroma_client = None
_collection = None
_memory_lock = threading.Lock()


def _get_collection():
    """
    Returns the ChromaDB collection, initializing it on first call.

    Lazy initialization: ChromaDB is imported and set up ONLY when
    the memory layer is first accessed. If memory is disabled in settings,
    this function is never called — zero overhead.

    The collection is a persistent on-disk vector database stored at
    settings.memory_dir (default: "memory/"). It survives restarts.

    Returns:
        A ChromaDB collection object with .add() and .query() methods.

    Raises:
        ImportError: If chromadb is not installed.
        RuntimeError: If ChromaDB fails to initialize.
    """
    global _chroma_client, _collection

    # Return existing collection if already initialized
    if _collection is not None:
        return _collection

    # Thread-safe initialization (double-checked locking pattern)
    with _memory_lock:
        # Check again inside the lock (another thread may have initialized)
        if _collection is not None:
            return _collection

        try:
            import chromadb  # Local import — only loaded when memory is used

            settings = get_settings()

            # PersistentClient stores vectors on disk.
            # path= is the directory where the database files live.
            # It's created automatically if it doesn't exist.
            _chroma_client = chromadb.PersistentClient(path=settings.memory_dir)

            # get_or_create_collection:
            # - If the collection already exists: loads it (all past memories intact)
            # - If not: creates a new empty collection
            #
            # "content_memory" is just the collection name — think of it as a table name.
            # metadata={"hnsw:space": "cosine"} tells ChromaDB to use cosine similarity
            # for distance calculation (standard for text similarity).
            _collection = _chroma_client.get_or_create_collection(
                name="content_memory",
                metadata={"hnsw:space": "cosine"},
            )

            logger.info(
                "memory_initialized",
                path=settings.memory_dir,
                existing_entries=_collection.count(),
            )

            return _collection

        except ImportError:
            raise ImportError(
                "chromadb is not installed. "
                "Run: uv pip install chromadb  "
                "Or add 'chromadb' to pyproject.toml dependencies."
            )
        except Exception as e:
            logger.error("memory_init_failed", error=str(e))
            raise RuntimeError(f"ChromaDB initialization failed: {e}")


def store_memory(
    input_notes: str,
    generated_posts: dict,
    metadata: dict = None,
) -> bool:
    """
    Stores a successful pipeline run in the semantic memory.

    Called by run_pipeline_service() after a successful generation.
    The input notes become the searchable "document" — future similar
    notes will match against this.

    The generated posts are stored in ChromaDB metadata (not searchable,
    but retrievable when a match is found).

    Args:
        input_notes:     The raw developer notes that produced this content.
                         This is what gets embedded and indexed for similarity search.
        generated_posts: Dict of platform → post content.
                         e.g. {"linkedin": "I fixed...", "twitter": "1/ Fixed..."}
        metadata:        Optional additional context (style used, platforms, etc.)

    Returns:
        True if stored successfully, False on failure.
    """
    settings = get_settings()

    if not settings.memory_enabled:
        return False

    if not input_notes or not generated_posts:
        return False

    try:
        collection = _get_collection()

        # ChromaDB metadata values must be strings, ints, floats, or bools.
        # Build metadata dynamically from generated_posts to support any platform
        chroma_metadata = {
            "timestamp": datetime.utcnow().isoformat(),
            "platforms": list(generated_posts.keys()),  # Store as list of platform names
            "style": (metadata or {}).get("style_used", "dhruv_default"),
            "notes_length": len(input_notes),
        }

        # Store posts as platform-specific fields (max ChromaDB string length ~40k)
        for platform, content in generated_posts.items():
            # Truncate very long content and make field name safe
            field_name = f"post_{platform.lower()[:20]}"  # Limit field name length
            max_len = 5000 if platform == "blog" else 2000
            chroma_metadata[field_name] = content[:max_len] if content else ""

        # Use UUID for guaranteed uniqueness (prevents timestamp/hash collisions)
        doc_id = f"content_{uuid.uuid4().hex[:12]}"

        collection.add(
            documents=[input_notes],       # The text that gets embedded
            metadatas=[chroma_metadata],   # Associated data (not embedded)
            ids=[doc_id],                  # Unique identifier
        )

        logger.info(
            "memory_stored",
            doc_id=doc_id,
            platforms=list(generated_posts.keys()),
            notes_preview=input_notes[:60].replace("\n", " "),
        )

        return True

    except Exception as e:
        # Memory storage failure should NEVER crash the pipeline
        logger.error("memory_store_failed", error=str(e))
        return False


def search_memory(input_notes: str) -> Optional[dict]:
    """
    Searches for semantically similar past content.

    ChromaDB converts input_notes to an embedding vector and finds
    the most similar document in the collection. If the similarity
    exceeds the configured threshold, returns the past generated content.

    This result is used in two ways:
      1. As a reference for the LLM: "here's how you wrote about similar work before"
      2. As a potential early exit: if similarity is very high, you may want to
         regenerate with slight variation rather than fully rerun the pipeline

    Args:
        input_notes: The new developer notes to search against.

    Returns:
        Dict with keys: similarity, past_notes, past_posts, timestamp, style
        Or None if no similar content found above threshold.
    """
    settings = get_settings()

    if not settings.memory_enabled:
        return None

    if not input_notes or not input_notes.strip():
        return None

    try:
        collection = _get_collection()

        # Nothing stored yet — can't search
        if collection.count() == 0:
            logger.info("memory_search_empty", reason="no_entries")
            return None

        # Query ChromaDB for the most similar past document
        # n_results=1 — we only want the single best match
        # include= — what data to return alongside the match
        results = collection.query(
            query_texts=[input_notes],
            n_results=1,
            include=["documents", "metadatas", "distances"],
        )

        # ChromaDB returns nested lists (supports multiple queries at once)
        # We sent 1 query, so we access [0] to get the first query's results
        if not results["ids"] or not results["ids"][0]:
            return None

        # Distance is a cosine distance — lower = more similar
        # Convert to similarity: similarity = 1 - distance
        # Distance 0.0 = identical, Distance 1.0 = completely different
        distance = results["distances"][0][0]
        similarity = 1.0 - distance

        logger.info(
            "memory_search_result",
            similarity=round(similarity, 3),
            threshold=settings.memory_similarity_threshold,
            match_found=similarity >= settings.memory_similarity_threshold,
        )

        # Only return a result if it clears the similarity threshold
        if similarity < settings.memory_similarity_threshold:
            return None

        # Extract the matched document and its metadata
        past_notes = results["documents"][0][0]
        meta = results["metadatas"][0][0]

        # Reconstruct the past_posts dict from metadata fields
        # Dynamically find all "post_*" fields (supports any platform)
        past_posts = {}
        for key, value in meta.items():
            if key.startswith("post_") and value:
                platform = key[5:]  # Remove "post_" prefix to get platform name
                past_posts[platform] = value

        return {
            "similarity": round(similarity, 3),
            "past_notes_preview": past_notes[:200],
            "past_posts": past_posts,
            "timestamp": meta.get("timestamp", "unknown"),
            "style": meta.get("style", "dhruv_default"),
        }

    except Exception as e:
        # Search failure → return None (pipeline continues normally)
        logger.error("memory_search_failed", error=str(e))
        return None


def get_memory_stats() -> dict:
    """
    Returns stats about the memory store.
    Used by /health endpoint and settings UI.
    """
    settings = get_settings()

    if not settings.memory_enabled:
        return {"enabled": False, "entry_count": 0}

    try:
        collection = _get_collection()
        return {
            "enabled": True,
            "entry_count": collection.count(),
            "memory_dir": settings.memory_dir,
            "similarity_threshold": settings.memory_similarity_threshold,
        }
    except Exception as e:
        return {"enabled": True, "entry_count": -1, "error": str(e)}