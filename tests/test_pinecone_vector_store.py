from __future__ import annotations

import types
import unittest
from unittest.mock import patch

from tools.custom.pinecone_vector_store import TOOL_SPEC, run


class PineconeVectorStoreTests(unittest.TestCase):
    def test_spec_name(self) -> None:
        self.assertEqual(TOOL_SPEC["name"], "pinecone_vector_store")

    def test_missing_package(self) -> None:
        real_import = __import__

        def _block(name, *args, **kwargs):
            if name == "pinecone":
                raise ImportError("missing")
            return real_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=_block):
            result = run({"action": "status", "api_key": "k"}, {})
        self.assertIn("error", result)

    def test_status_and_query_with_fake_client(self) -> None:
        fake = types.ModuleType("pinecone")

        class FakeServerlessSpec:
            def __init__(self, cloud, region):
                self.cloud = cloud
                self.region = region

        class FakeMatch:
            def __init__(self, mid, score, metadata):
                self.id = mid
                self.score = score
                self.metadata = metadata

        class FakeQueryResp:
            def __init__(self):
                self.matches = [FakeMatch("a", 0.9, {"x": 1})]

        class FakeIndex:
            def upsert(self, vectors, namespace=None):
                _ = vectors
                _ = namespace
                return {"upserted_count": 1}

            def query(self, vector, top_k, namespace=None, include_metadata=True):
                _ = vector
                _ = top_k
                _ = namespace
                _ = include_metadata
                return FakeQueryResp()

        class FakePinecone:
            def __init__(self, api_key):
                self.api_key = api_key

            def list_indexes(self):
                return ["demo-index"]

            def Index(self, index_name):
                _ = index_name
                return FakeIndex()

            def create_index(self, **kwargs):
                _ = kwargs

        fake.Pinecone = FakePinecone
        fake.ServerlessSpec = FakeServerlessSpec

        with patch.dict("sys.modules", {"pinecone": fake}):
            status = run({"action": "status", "api_key": "k"}, {})
            self.assertTrue(status.get("ok"))
            query = run(
                {
                    "action": "query",
                    "api_key": "k",
                    "index": "demo-index",
                    "vector": [0.1, 0.2, 0.3],
                    "top_k": 1,
                },
                {},
            )
            self.assertTrue(query.get("ok"))
            self.assertEqual(query["matches"][0]["id"], "a")


if __name__ == "__main__":
    unittest.main()
