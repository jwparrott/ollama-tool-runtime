from __future__ import annotations

import types
import unittest
from unittest.mock import patch

from tools.custom.haystack_rag import TOOL_SPEC, run


class HaystackRagTests(unittest.TestCase):
    def test_spec_name(self) -> None:
        self.assertEqual(TOOL_SPEC["name"], "haystack_rag")

    def test_missing_package(self) -> None:
        real_import = __import__

        def _block(name, *args, **kwargs):
            if name == "haystack" or name.startswith("haystack."):
                raise ImportError("missing")
            return real_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=_block):
            result = run({"action": "status"}, {})
        self.assertIn("error", result)

    def test_ingest_and_query_with_fake_haystack(self) -> None:
        mod_haystack = types.ModuleType("haystack")
        mod_docstores = types.ModuleType("haystack.document_stores")
        mod_docstores_mem = types.ModuleType("haystack.document_stores.in_memory")
        mod_components = types.ModuleType("haystack.components")
        mod_retrievers = types.ModuleType("haystack.components.retrievers")
        mod_retrievers_mem = types.ModuleType("haystack.components.retrievers.in_memory")

        class Document:
            def __init__(self, id=None, content="", meta=None):
                self.id = id
                self.content = content
                self.meta = meta or {}
                self.score = 0.0

        class InMemoryDocumentStore:
            def __init__(self):
                self.docs = []

            def write_documents(self, docs):
                self.docs.extend(docs)

        class InMemoryBM25Retriever:
            def __init__(self, document_store):
                self.store = document_store

            def run(self, query, top_k=5):
                _ = query
                docs = self.store.docs[:top_k]
                for idx, doc in enumerate(docs):
                    doc.score = 1.0 - (idx * 0.1)
                return {"documents": docs}

        mod_haystack.Document = Document
        mod_docstores_mem.InMemoryDocumentStore = InMemoryDocumentStore
        mod_retrievers_mem.InMemoryBM25Retriever = InMemoryBM25Retriever

        with patch.dict(
            "sys.modules",
            {
                "haystack": mod_haystack,
                "haystack.document_stores": mod_docstores,
                "haystack.document_stores.in_memory": mod_docstores_mem,
                "haystack.components": mod_components,
                "haystack.components.retrievers": mod_retrievers,
                "haystack.components.retrievers.in_memory": mod_retrievers_mem,
            },
        ):
            ingest = run(
                {
                    "action": "ingest",
                    "index_name": "demo",
                    "documents": [{"id": "d1", "content": "hello world", "meta": {"source": "x"}}],
                },
                {},
            )
            self.assertTrue(ingest.get("ok"))
            query = run({"action": "query", "index_name": "demo", "query": "hello", "top_k": 1}, {})
            self.assertTrue(query.get("ok"))
            self.assertEqual(query["matches"][0]["id"], "d1")


if __name__ == "__main__":
    unittest.main()
