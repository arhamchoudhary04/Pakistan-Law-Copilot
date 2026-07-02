"""Self-verification loop logic (verify_node + routing), tested directly.

verify_node decides whether an answer is supported and whether to loop back for
another attempt. The loop is hard-capped at max_attempts (default 2).
"""

from app.agent import graph
from app.agent.graph import route_after_verify, verify_node
from app.models.schemas import Chunk, RetrievedChunk


def _state(answer: str, attempts: int) -> dict:
    return {
        "question": "q",
        "answer": answer,
        "attempts": attempts,
        "can_retry": True,
        "retrieved": [
            RetrievedChunk(chunk=Chunk(id="d#0", doc_id="d", ordinal=0, content="c"), score=0.9)
        ],
    }


def test_uncited_answer_retries_when_attempts_remain():
    # No citations, first attempt -> should request a retry back to rewrite.
    out = verify_node(_state("Some claim with no citation.", attempts=0), {})
    assert out["retry"] is True
    assert out["attempts"] == 1
    assert route_after_verify(out) == "rewrite"


def test_loop_is_capped_at_max_attempts():
    # Still uncited, but we've hit the cap -> finalize (partial), no more retries.
    out = verify_node(_state("Still no citation.", attempts=1), {})
    assert out["retry"] is False
    assert out["attempts"] == 2
    assert out["status"] == "partial"
    assert route_after_verify(out) == "end"


def test_valid_citation_is_grounded():
    out = verify_node(_state("Answer grounded in a source [1].", attempts=0), {})
    assert out["retry"] is False
    assert out["status"] == "grounded"
    assert out["used_markers"] == [1]


def test_refusal_is_idk_without_retry():
    out = verify_node(_state(graph.IDK_MESSAGE, attempts=0), {})
    assert out["retry"] is False
    assert out["status"] == "idk"


def test_generation_failure_finalizes_partial():
    state = _state("[generation unavailable] no key", attempts=0)
    state["can_retry"] = False
    out = verify_node(state, {})
    assert out["retry"] is False
    assert out["status"] == "partial"
    assert route_after_verify(out) == "end"
