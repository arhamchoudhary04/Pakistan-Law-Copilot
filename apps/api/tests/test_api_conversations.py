"""``/conversations/*`` over HTTP: authentication, per-user scoping, and round-trip.

The store-level equivalents live in ``test_store.py``; these assert the same
guarantee survives the router and the ``CurrentUser`` dependency, and that a
cross-user attempt is reported as 404 (not 403, which would confirm existence).
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from tests.conftest import auth, signup


def _new_conversation(client: TestClient, token: str, title: str = "My chat") -> str:
    resp = client.post("/conversations", json={"title": title}, headers=auth(token))
    assert resp.status_code == 200, resp.text
    return resp.json()["id"]


# ---- authentication ----


def test_every_conversation_endpoint_requires_authentication(client: TestClient):
    assert client.get("/conversations").status_code == 401
    assert client.post("/conversations", json={"title": "x"}).status_code == 401
    assert client.get("/conversations/any-id").status_code == 401
    assert client.delete("/conversations/any-id").status_code == 401
    assert (
        client.post("/conversations/any-id/turn", json={"question": "q", "answer": "a"})
    ).status_code == 401


# ---- per-user scoping ----


def test_you_only_see_your_own_conversations(client: TestClient):
    alice = signup(client, "alice@example.com")
    bob = signup(client, "bob@example.com")
    _new_conversation(client, alice, "Alice one")
    _new_conversation(client, alice, "Alice two")
    _new_conversation(client, bob, "Bob one")

    alice_titles = {c["title"] for c in client.get("/conversations", headers=auth(alice)).json()}
    bob_titles = {c["title"] for c in client.get("/conversations", headers=auth(bob)).json()}
    assert alice_titles == {"Alice one", "Alice two"}
    assert bob_titles == {"Bob one"}


def test_reading_another_users_conversation_is_a_404(client: TestClient):
    alice = signup(client, "alice@example.com")
    bob = signup(client, "bob@example.com")
    conv_id = _new_conversation(client, alice, "Alice's private chat")

    assert client.get(f"/conversations/{conv_id}", headers=auth(alice)).status_code == 200
    # 404, not 403: Bob must not be able to confirm the conversation exists.
    assert client.get(f"/conversations/{conv_id}", headers=auth(bob)).status_code == 404


def test_deleting_another_users_conversation_is_a_404_and_leaves_it_intact(client: TestClient):
    alice = signup(client, "alice@example.com")
    bob = signup(client, "bob@example.com")
    conv_id = _new_conversation(client, alice)

    assert client.delete(f"/conversations/{conv_id}", headers=auth(bob)).status_code == 404
    assert client.get(f"/conversations/{conv_id}", headers=auth(alice)).status_code == 200


def test_saving_a_turn_into_another_users_conversation_is_a_404(client: TestClient):
    alice = signup(client, "alice@example.com")
    bob = signup(client, "bob@example.com")
    conv_id = _new_conversation(client, alice)

    resp = client.post(
        f"/conversations/{conv_id}/turn",
        json={"question": "injected", "answer": "injected"},
        headers=auth(bob),
    )
    assert resp.status_code == 404
    detail = client.get(f"/conversations/{conv_id}", headers=auth(alice)).json()
    assert detail["messages"] == []


# ---- round trip ----


def test_a_saved_turn_is_restored_with_its_citations(client: TestClient):
    """Reopening a conversation must bring back the clickable sources."""
    token = signup(client, "round@example.com")
    conv_id = _new_conversation(client, token, "Rights on arrest")
    meta = {
        "citations": [
            {
                "marker": 1,
                "chunk_id": "constitution-fundamental-rights.md#10",
                "source": "constitution-fundamental-rights.md",
                "section": "Article 10",
            }
        ],
        "status": "grounded",
    }
    saved = client.post(
        f"/conversations/{conv_id}/turn",
        json={"question": "rights on arrest?", "answer": "Article 10 [1].", "meta": meta},
        headers=auth(token),
    )
    assert saved.status_code == 204

    detail = client.get(f"/conversations/{conv_id}", headers=auth(token)).json()
    assert [m["role"] for m in detail["messages"]] == ["user", "assistant"]
    assert detail["messages"][1]["content"] == "Article 10 [1]."
    assert detail["messages"][1]["meta"] == meta


def test_delete_removes_the_conversation(client: TestClient):
    token = signup(client, "gone@example.com")
    conv_id = _new_conversation(client, token)

    assert client.delete(f"/conversations/{conv_id}", headers=auth(token)).status_code == 204
    assert client.get(f"/conversations/{conv_id}", headers=auth(token)).status_code == 404
    assert client.get("/conversations", headers=auth(token)).json() == []


def test_conversations_are_listed_most_recently_updated_first(client: TestClient):
    token = signup(client, "order@example.com")
    first = _new_conversation(client, token, "Older")
    _new_conversation(client, token, "Newer")

    # Touching the older conversation should float it back to the top.
    client.post(
        f"/conversations/{first}/turn",
        json={"question": "q", "answer": "a"},
        headers=auth(token),
    )
    titles = [c["title"] for c in client.get("/conversations", headers=auth(token)).json()]
    assert titles[0] == "Older"


# ---- validation ----


def test_oversized_title_and_empty_question_are_rejected(client: TestClient):
    token = signup(client, "valid@example.com")
    long_title = client.post(
        "/conversations", json={"title": "x" * 201}, headers=auth(token)
    )
    conv_id = _new_conversation(client, token)
    empty_question = client.post(
        f"/conversations/{conv_id}/turn",
        json={"question": "", "answer": "a"},
        headers=auth(token),
    )
    assert long_title.status_code == 422
    assert empty_question.status_code == 422
