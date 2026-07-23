"""Pinecone vector database integration tool."""

from __future__ import annotations

from typing import Any

DEFAULT_INDEX_NAME = "llama-runtime-index"

TOOL_SPEC = {
    "name": "pinecone_vector_store",
    "description": (
        "Use Pinecone for vector storage and retrieval. "
        "Supports status checks, index bootstrap, upsert, and query."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["status", "upsert", "query"],
                "description": "Operation: status, upsert vectors, or query vectors.",
            },
            "api_key": {"type": "string", "description": "Pinecone API key (optional if PINECONE_API_KEY env set)."},
            "index": {
                "type": "string",
                "description": f"Pinecone index name (default: {DEFAULT_INDEX_NAME}).",
            },
            "create_if_missing": {"type": "boolean", "description": "Create index when missing."},
            "dimension": {"type": "integer", "description": "Vector dimension (required if creating index)."},
            "metric": {"type": "string", "description": "Similarity metric, default cosine."},
            "cloud": {"type": "string", "description": "Cloud provider for new serverless index (default aws)."},
            "region": {"type": "string", "description": "Region for new serverless index (default us-east-1)."},
            "namespace": {"type": "string", "description": "Namespace for upsert/query."},
            "vectors": {
                "type": "array",
                "description": "Vectors for upsert. Item format: {id, values, metadata?}.",
                "items": {"type": "object"},
            },
            "top_k": {"type": "integer", "description": "Top matches to return for query (default 5)."},
            "vector": {"type": "array", "description": "Query vector.", "items": {"type": "number"}},
            "include_metadata": {"type": "boolean", "description": "Include metadata in query results (default true)."},
        },
        "required": ["action"],
    },
}


def run(args: dict, context: dict) -> dict:
    _ = context
    action = str(args.get("action", "")).strip().lower()
    if not action:
        return {"error": "action is required"}
    if action not in {"status", "upsert", "query"}:
        return {"error": "action must be one of: status, upsert, query"}

    try:
        import os
        from pinecone import Pinecone, ServerlessSpec  # type: ignore[import]
    except ImportError:
        return {"error": "pinecone package is not installed. Run: pip install pinecone"}

    api_key = str(args.get("api_key") or os.environ.get("PINECONE_API_KEY", "")).strip()
    if not api_key:
        return {"error": "Pinecone API key is required (arg api_key or env PINECONE_API_KEY)."}

    try:
        pc = Pinecone(api_key=api_key)
    except Exception as exc:  # noqa: BLE001
        return {"error": f"Could not initialize Pinecone client: {exc}"}

    if action == "status":
        try:
            indexes = pc.list_indexes()
        except Exception as exc:  # noqa: BLE001
            return {"error": f"Pinecone status check failed: {exc}"}
        names = _extract_index_names(indexes)
        return {"ok": True, "index_count": len(names), "indexes": names}

    index_name = str(args.get("index") or DEFAULT_INDEX_NAME).strip()

    idx_result = _ensure_index(pc, index_name, args, ServerlessSpec)
    if "error" in idx_result:
        return idx_result
    index_obj = idx_result["index"]

    if action == "upsert":
        vectors = args.get("vectors")
        if not isinstance(vectors, list) or not vectors:
            return {"error": "vectors must be a non-empty array for upsert."}
        normalized = []
        for item in vectors:
            if not isinstance(item, dict):
                return {"error": "Each vectors item must be an object with id and values."}
            item_id = str(item.get("id", "")).strip()
            values = item.get("values")
            metadata = item.get("metadata")
            if not item_id:
                return {"error": "Each vector must include non-empty id."}
            if not isinstance(values, list) or not values:
                return {"error": f"Vector '{item_id}' must include non-empty numeric values list."}
            normalized.append({"id": item_id, "values": values, "metadata": metadata if isinstance(metadata, dict) else {}})
        namespace = str(args.get("namespace", "")).strip() or None
        try:
            response = index_obj.upsert(vectors=normalized, namespace=namespace)
        except Exception as exc:  # noqa: BLE001
            return {"error": f"Pinecone upsert failed: {exc}"}
        return {"ok": True, "upserted_count": len(normalized), "namespace": namespace, "response": _safe_obj(response)}

    top_k = min(max(1, int(args.get("top_k", 5))), 100)
    query_vector = args.get("vector")
    if not isinstance(query_vector, list) or not query_vector:
        return {"error": "vector must be a non-empty numeric list for query."}
    namespace = str(args.get("namespace", "")).strip() or None
    include_metadata = bool(args.get("include_metadata", True))
    try:
        response = index_obj.query(
            vector=query_vector,
            top_k=top_k,
            namespace=namespace,
            include_metadata=include_metadata,
        )
    except Exception as exc:  # noqa: BLE001
        return {"error": f"Pinecone query failed: {exc}"}
    matches = []
    raw_matches = getattr(response, "matches", None) or (response.get("matches", []) if isinstance(response, dict) else [])
    for match in raw_matches:
        score = getattr(match, "score", None) if not isinstance(match, dict) else match.get("score")
        mid = getattr(match, "id", None) if not isinstance(match, dict) else match.get("id")
        metadata = getattr(match, "metadata", None) if not isinstance(match, dict) else match.get("metadata")
        matches.append({"id": mid, "score": score, "metadata": metadata})
    return {"ok": True, "top_k": top_k, "namespace": namespace, "matches": matches}


def _ensure_index(pc: Any, index_name: str, args: dict, serverless_spec_cls: Any) -> dict:
    try:
        names = set(_extract_index_names(pc.list_indexes()))
    except Exception as exc:  # noqa: BLE001
        return {"error": f"Failed to list indexes: {exc}"}

    if index_name not in names:
        if not bool(args.get("create_if_missing", False)):
            return {"error": f"Index '{index_name}' does not exist. Set create_if_missing=true to create it."}
        dimension = int(args.get("dimension", 0))
        if dimension <= 0:
            return {"error": "dimension must be > 0 when creating a new index."}
        metric = str(args.get("metric", "cosine")).strip() or "cosine"
        cloud = str(args.get("cloud", "aws")).strip() or "aws"
        region = str(args.get("region", "us-east-1")).strip() or "us-east-1"
        try:
            pc.create_index(
                name=index_name,
                dimension=dimension,
                metric=metric,
                spec=serverless_spec_cls(cloud=cloud, region=region),
            )
        except Exception as exc:  # noqa: BLE001
            return {"error": f"Failed to create index '{index_name}': {exc}"}
    try:
        return {"index": pc.Index(index_name)}
    except Exception as exc:  # noqa: BLE001
        return {"error": f"Failed to open index '{index_name}': {exc}"}


def _extract_index_names(indexes: Any) -> list[str]:
    if isinstance(indexes, list):
        names = []
        for item in indexes:
            if isinstance(item, str):
                names.append(item)
            elif isinstance(item, dict):
                if "name" in item:
                    names.append(str(item["name"]))
        return names
    names_attr = getattr(indexes, "names", None)
    if callable(names_attr):
        try:
            values = names_attr()
            return [str(x) for x in values]
        except Exception:  # noqa: BLE001
            return []
    if isinstance(indexes, dict):
        data = indexes.get("indexes", [])
        return [str(item.get("name")) for item in data if isinstance(item, dict) and "name" in item]
    return []


def _safe_obj(value: Any) -> Any:
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if isinstance(value, dict):
        return {str(k): _safe_obj(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_safe_obj(item) for item in value]
    text = str(value)
    return text[:5000]
