"""Prompt construction for grounded, citation-first generation.

The system prompt is the primary guardrail against hallucination: the model is
instructed to answer *only* from the numbered context, cite every claim with
``[n]`` markers that map to the provided chunks, and refuse when the context is
insufficient rather than guessing.
"""

from __future__ import annotations

from app.models.schemas import RetrievedChunk

SYSTEM_PROMPT = """You are Knowledge Copilot, a grounded assistant that answers \
strictly from the provided source excerpts.

Rules:
- Use ONLY the information in the numbered context below. Do not use prior knowledge.
- Cite every factual sentence with the matching source marker, e.g. "... [1]" or "... [2][3]".
- Only cite markers that actually appear in the context (1..N).
- If the context does not contain enough information to answer, reply exactly: \
"I don't know based on the available sources." and nothing else.
- Be concise and do not fabricate citations, URLs, or facts."""


def build_context_block(retrieved: list[RetrievedChunk]) -> str:
    """Render retrieved chunks as a numbered context block for the prompt."""
    blocks = []
    for i, item in enumerate(retrieved, start=1):
        header = item.chunk.section or item.chunk.source or item.chunk.doc_id
        blocks.append(f"[{i}] (source: {header})\n{item.chunk.content}")
    return "\n\n".join(blocks)


def build_messages(question: str, retrieved: list[RetrievedChunk]) -> list[dict[str, str]]:
    """Build the chat messages for a grounded answer."""
    context = build_context_block(retrieved)
    user_content = (
        f"Context:\n{context}\n\n"
        f"Question: {question}\n\n"
        "Answer using only the context above, with [n] citations."
    )
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_content},
    ]
