"""Haystack-powered local retrieval utility."""

from __future__ import annotations

from typing import Any

TOOL_SPEC = {
    "name": "haystack_rag",
    "description": (
        "Use Haystack for local ingestion and retrieval. "
        "Supports status checks, ingesting text docs, and querying top matches."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["status", "ingest", "query"],
                "description": "Operation to perform.",
            },
            "index_name": {"type": "string", "description": "In-memory index key (default: default)."},
            "documents": {
                "type": "array",
                "description": "Documents for ingest. Item format: {id?, content, meta?}.",
                "items": {"type": "object"},
            },
            "query": {"type": "string", "description": "Query string for retrieval."},
            "top_k": {"type": "integer", "description": "Top docs to return (default 5)."},
        },
        "required": ["action"],
    },
}

_STATE: dict[str, dict[str, Any]] = {}


def run(args: dict, context: dict) -> dict:
    _ = context
    action = str(args.get("action", "")).strip().lower()
    if action not in {"status", "ingest", "query"}:
        return {"error": "action must be one of: status, ingest, query"}

    try:
        from haystack import Document  # type: ignore[import]
        from haystack.components.retrievers.in_memory import InMemoryBM25Retriever  # type: ignore[import]
        from haystack.document_stores.in_memory import InMemoryDocumentStore  # type: ignore[import]
    except ImportError:
        return {"error": "haystack-ai package is not installed. Run: pip install haystack-ai"}

    if action == "status":
        return {"ok": True, "indexes": sorted(_STATE.keys()), "index_count": len(_STATE)}

    index_name = str(args.get("index_name", "default")).strip() or "default"
    bundle = _STATE.get(index_name)
    if bundle is None:
        store = InMemoryDocumentStore()
        retriever = InMemoryBM25Retriever(document_store=store)
        bundle = {"store": store, "retriever": retriever}
        _STATE[index_name] = bundle
    store = bundle["store"]
    retriever = bundle["retriever"]

    if action == "ingest":
        docs = args.get("documents")
        if not isinstance(docs, list) or not docs:
            return {"error": "documents must be a non-empty array for ingest."}
        hay_docs = []
        for idx, item in enumerate(docs):
            if not isinstance(item, dict):
                return {"error": "Each documents item must be an object."}
            content = str(item.get("content", "")).strip()
            if not content:
                return {"error": f"documents[{idx}].content must be non-empty."}
            doc_id = str(item.get("id", "")).strip() or None
            meta = item.get("meta", {})
            if not isinstance(meta, dict):
                meta = {}
            hay_docs.append(Document(id=doc_id, content=content, meta=meta))
        try:
            store.write_documents(hay_docs)
        except Exception as exc:  # noqa: BLE001
            return {"error": f"Haystack ingest failed: {exc}"}
        return {"ok": True, "index_name": index_name, "ingested_count": len(hay_docs)}

    query = str(args.get("query", "")).strip()
    if not query:
        return {"error": "query is required for action=query"}
    top_k = min(max(1, int(args.get("top_k", 5))), 50)
    try:
        result = retriever.run(query=query, top_k=top_k)
    except Exception as exc:  # noqa: BLE001
        return {"error": f"Haystack query failed: {exc}"}
    docs = result.get("documents", []) if isinstance(result, dict) else []
    matches = []
    for doc in docs:
        content = getattr(doc, "content", None) if not isinstance(doc, dict) else doc.get("content")
        doc_id = getattr(doc, "id", None) if not isinstance(doc, dict) else doc.get("id")
        score = getattr(doc, "score", None) if not isinstance(doc, dict) else doc.get("score")
        meta = getattr(doc, "meta", None) if not isinstance(doc, dict) else doc.get("meta")
        matches.append({"id": doc_id, "score": score, "content": content, "meta": meta})
    return {"ok": True, "index_name": index_name, "query": query, "top_k": top_k, "matches": matches}
