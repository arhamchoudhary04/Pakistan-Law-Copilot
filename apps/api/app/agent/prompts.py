"""Prompt construction for grounded, citation-first generation.

The system prompt is the primary guardrail against hallucination: the model is
instructed to answer *only* from the numbered context, cite every claim with
``[n]`` markers that map to the provided chunks, and refuse when the context is
insufficient rather than guessing.
"""

from __future__ import annotations

from app.models.schemas import RetrievedChunk

SYSTEM_PROMPT = """You are Pakistan Law Copilot, a grounded assistant that explains \
Pakistani law in plain language, strictly from the provided source excerpts (the \
Constitution and Acts of Pakistan).

Rules:
- Use ONLY the information in the numbered context below. Do not use prior knowledge \
of law, other countries' law, or anything not in the context.
- Cite every legal statement with the matching source marker, e.g. "... [1]" or "... [2][3]", \
and refer to the provision by name where helpful (e.g. "Article 10A" or "PECA Section 21").
- Only cite markers that actually appear in the context (1..N).
- If the context does not contain enough information to answer, reply exactly: \
"I don't know based on the available sources." and nothing else.
- Be concise, neutral, and do not fabricate citations, provisions, penalties, or facts.
- Reply in the SAME language and script the user used (English, Urdu, or Roman Urdu). \
Keep provision names and the [n] citation markers in English (e.g. "Article 10A") even \
when the rest of the answer is in Urdu or Roman Urdu.
- This is legal information, not legal advice. If the question concerns a specific personal \
situation, add one short closing line advising the person to consult a qualified lawyer."""

# Used when answering from a user-uploaded document instead of the law corpus.
DOCUMENT_SYSTEM = """You are a grounded assistant that answers questions strictly from \
the provided excerpts of the user's uploaded document.

Rules:
- Use ONLY the information in the numbered context below. Do not use outside knowledge.
- Cite every claim with the matching source marker, e.g. "... [1]" or "... [2][3]".
- Only cite markers that actually appear in the context (1..N).
- If the context does not contain enough information to answer, reply exactly: \
"I don't know based on the available sources." and nothing else.
- Reply in the same language the user used. Be concise and do not fabricate anything."""

_SYSTEM_BY_MODE = {"law": SYSTEM_PROMPT, "document": DOCUMENT_SYSTEM}


def build_context_block(retrieved: list[RetrievedChunk]) -> str:
    """Render retrieved chunks as a numbered context block for the prompt."""
    blocks = []
    for i, item in enumerate(retrieved, start=1):
        header = item.chunk.section or item.chunk.source or item.chunk.doc_id
        blocks.append(f"[{i}] (source: {header})\n{item.chunk.content}")
    return "\n\n".join(blocks)


def build_messages(
    question: str,
    retrieved: list[RetrievedChunk],
    feedback: str = "",
    mode: str = "law",
) -> list[dict[str, str]]:
    """Build the chat messages for a grounded answer.

    ``feedback`` carries the self-verification note from a previous attempt so the
    model can correct unsupported claims on the retry. ``mode`` selects the system
    prompt: the legal assistant ("law") or the generic uploaded-document one.
    """
    context = build_context_block(retrieved)
    hint = f"\n\nNote from a previous attempt: {feedback}" if feedback else ""
    user_content = (
        f"Context:\n{context}\n\n"
        f"Question: {question}{hint}\n\n"
        "Answer using only the context above, with [n] citations."
    )
    return [
        {"role": "system", "content": _SYSTEM_BY_MODE.get(mode, SYSTEM_PROMPT)},
        {"role": "user", "content": user_content},
    ]


REWRITE_SYSTEM = """You rewrite a user's question into concise search queries for a \
document retrieval system whose documents are in ENGLISH.

The question may be in English, Urdu (Urdu script), or Roman Urdu (Urdu written in \
Latin letters). Always translate the meaning into ENGLISH and output 1-3 short \
English queries, one per line, no numbering or extra text. Expand abbreviations and \
add likely legal synonyms. Do not answer the question.

If a "Recent conversation" is given and the new question is a follow-up that refers \
back to it (e.g. "what about the punishment?", "and for a second offence?"), resolve \
those references into self-contained queries using the conversation."""


def build_rewrite_messages(
    question: str,
    feedback: str = "",
    history: list[tuple[str, str]] | None = None,
) -> list[dict[str, str]]:
    """Build messages that ask the LLM to produce retrieval queries."""
    hint = (
        f"\n\nThe previous attempt retrieved weak context ({feedback}). "
        "Try broader or differently-worded queries."
        if feedback
        else ""
    )
    convo = ""
    if history:
        turns = "\n".join(f"User: {q}\nAssistant: {a[:200]}" for q, a in history[-3:])
        convo = f"Recent conversation:\n{turns}\n\n"
    return [
        {"role": "system", "content": REWRITE_SYSTEM},
        {"role": "user", "content": f"{convo}Question: {question}{hint}"},
    ]
