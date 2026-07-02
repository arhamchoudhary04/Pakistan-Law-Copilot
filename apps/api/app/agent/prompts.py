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


def build_messages(
    question: str, retrieved: list[RetrievedChunk], feedback: str = ""
) -> list[dict[str, str]]:
    """Build the chat messages for a grounded answer.

    ``feedback`` carries the self-verification note from a previous attempt so the
    model can correct unsupported claims on the retry.
    """
    context = build_context_block(retrieved)
    hint = f"\n\nNote from a previous attempt: {feedback}" if feedback else ""
    user_content = (
        f"Context:\n{context}\n\n"
        f"Question: {question}{hint}\n\n"
        "Answer using only the context above, with [n] citations."
    )
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_content},
    ]


REWRITE_SYSTEM = """You rewrite a user's question into concise search queries for a \
document retrieval system. Output 1-3 short queries, one per line, no numbering or \
extra text. Expand abbreviations and add likely synonyms; do not answer the question."""


def build_rewrite_messages(question: str, feedback: str = "") -> list[dict[str, str]]:
    """Build messages that ask the LLM to produce retrieval queries."""
    hint = (
        f"\n\nThe previous attempt retrieved weak context ({feedback}). "
        "Try broader or differently-worded queries."
        if feedback
        else ""
    )
    return [
        {"role": "system", "content": REWRITE_SYSTEM},
        {"role": "user", "content": f"Question: {question}{hint}"},
    ]
