from __future__ import annotations

from typing import Any


_SKILLS: tuple[dict[str, Any], ...] = (
    {
        "name": "code-review",
        "summary": "Review code changes for correctness, safety, and regressions.",
        "when_to_use": [
            "Before committing non-trivial code changes",
            "When debugging a subtle production bug",
            "When touching security-sensitive paths",
        ],
        "playbook": [
            "Read changed files and related call sites before judging.",
            "Check error handling, edge cases, and rollback paths.",
            "Run targeted tests first, then full suite.",
            "Report only concrete, reproducible issues.",
        ],
        "recommended_tools": ["search_in_files", "read_file", "run_tests", "find_files"],
    },
    {
        "name": "research",
        "summary": "Gather up-to-date information from external sources before implementing.",
        "when_to_use": [
            "API integrations",
            "Model or dependency selection",
            "Behavior that depends on current events",
        ],
        "playbook": [
            "Fetch authoritative docs pages first.",
            "Extract constraints, authentication requirements, and rate limits.",
            "Propose tools around stable endpoints with explicit fallbacks.",
            "Record source links and assumptions.",
        ],
        "recommended_tools": ["fetch_url", "web_search", "write_file"],
    },
    {
        "name": "testing",
        "summary": "Implement and validate changes with tight feedback loops.",
        "when_to_use": [
            "Any behavior change",
            "Bug fixes that were reproduced locally",
            "Before snapshots/rollbacks are relied on",
        ],
        "playbook": [
            "Write or update focused unit tests for the changed path.",
            "Run fast targeted tests, then full tests.",
            "If failing, isolate regression and iterate quickly.",
            "Do not finalize until all baseline tests pass.",
        ],
        "recommended_tools": ["write_file", "edit_file", "run_tests", "shell_command"],
    },
    {
        "name": "self-update-safe-change",
        "summary": "Perform code updates while preserving recovery paths.",
        "when_to_use": [
            "Editing core runtime files",
            "Large refactors",
            "Potentially risky migrations",
        ],
        "playbook": [
            "Create or verify a snapshot is available.",
            "Apply minimal coherent file updates.",
            "Run tests immediately and inspect stderr.",
            "Rollback if tests fail or critical commands break.",
        ],
        "recommended_tools": ["self_update_files", "run_tests", "list_snapshots", "rollback_snapshot"],
    },
    {
        "name": "new-tool-development",
        "summary": "Design, implement, register, and verify new model tools.",
        "when_to_use": [
            "Extending runtime capabilities",
            "Adding new external API integrations",
            "Replacing repeated manual workflows",
        ],
        "playbook": [
            "Define TOOL_SPEC with strict parameter validation.",
            "Implement run(args, context) with JSON-serializable outputs.",
            "Register tool and add unit tests for success/failure paths.",
            "Live test via chat to ensure the model actually invokes it.",
        ],
        "recommended_tools": ["register_python_tool", "list_tools", "run_tests", "chat"],
    },
    {
        "name": "conversation-memory-learning",
        "summary": "Store interaction logs and user feedback to improve future decisions.",
        "when_to_use": [
            "Long-running projects with repeated decision patterns",
            "When users provide explicit positive/negative feedback",
            "When the model should avoid repeating prior mistakes",
        ],
        "playbook": [
            "Log each meaningful turn with intent, action, and outcome.",
            "Capture user feedback as positive, neutral, or negative reinforcement.",
            "Before major choices, query prior similar interactions.",
            "Bias decisions toward historically positive outcomes.",
        ],
        "recommended_tools": ["conversation_memory", "search_in_files", "read_file"],
    },
    {
        "name": "unstructured-conversation-parsing",
        "summary": "Normalize and parse messy transcript-like text into speaker turns.",
        "when_to_use": [
            "Text message exports",
            "Meeting transcripts with inconsistent formatting",
            "Audio/video transcription text with multiple speakers",
        ],
        "playbook": [
            "Ingest from text, local files, or URLs.",
            "Clean timestamps/noise and normalize whitespace.",
            "Extract speaker-labeled turns while preserving order.",
            "Group contiguous turns and compute conversation stats.",
        ],
        "recommended_tools": ["shared_data_cleaner_parser", "fetch_url", "read_file", "write_file"],
    },
    {
        "name": "retrieval-augmentation-stack",
        "summary": "Use Haystack + Pinecone for hybrid retrieval and memory workflows.",
        "when_to_use": [
            "Semantic memory and long-context recall",
            "Document-grounded answer generation",
            "RAG pipelines combining local and hosted retrieval",
        ],
        "playbook": [
            "Ingest local docs into haystack_rag for fast prototyping.",
            "Store durable embeddings in pinecone_vector_store.",
            "Query both paths and reconcile confidence/feedback.",
            "Persist successful strategies into conversation_memory.",
        ],
        "recommended_tools": ["haystack_rag", "pinecone_vector_store", "conversation_memory"],
    },
    {
        "name": "advanced-web-collection",
        "summary": "Collect dynamic web data via browser automation and Firecrawl pipelines.",
        "when_to_use": [
            "JS-heavy pages not captured by simple HTTP fetch",
            "Multi-page crawl and content extraction workflows",
            "Normalizing scraped content for downstream parsing",
        ],
        "playbook": [
            "Start with web_data_pipeline search/fetch for quick checks.",
            "Use browser_automation for rendered DOM extraction.",
            "Use firecrawl_client for structured scrape/crawl jobs.",
            "Feed outputs into shared_data_cleaner_parser for turn-level parsing.",
        ],
        "recommended_tools": ["web_data_pipeline", "browser_automation", "firecrawl_client", "shared_data_cleaner_parser"],
    },
)


def list_model_skills() -> list[dict[str, Any]]:
    return [dict(skill) for skill in _SKILLS]


def get_model_skill(name: str) -> dict[str, Any]:
    needle = name.strip().lower()
    if not needle:
        raise ValueError("Skill name must not be empty.")
    for skill in _SKILLS:
        if str(skill["name"]).lower() == needle:
            return dict(skill)
    available = ", ".join(skill["name"] for skill in _SKILLS)
    raise KeyError(f"Unknown skill '{name}'. Available skills: {available}")
