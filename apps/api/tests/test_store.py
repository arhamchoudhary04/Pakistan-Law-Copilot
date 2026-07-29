"""AccountStore: ownership scoping, turn ordering, and cascade behaviour.

The security-critical property here is that *every* conversation and message
operation is scoped to the owning user. The code gets this right by passing
``user_id`` into each query, but nothing pinned it down — so a refactor that
dropped an ``AND user_id = ?`` would leak another user's chat history with all
tests still green. These tests are that pin.
"""

from __future__ import annotations

import sqlite3

import pytest

from app.db.store import AccountStore, EmailTakenError


def _two_users(store: AccountStore):
    alice = store.create_user("alice@example.com", "Alice", "hash-a")
    bob = store.create_user("bob@example.com", "Bob", "hash-b")
    return alice, bob


# ---- accounts ----


def test_create_user_and_look_it_up(store: AccountStore):
    account = store.create_user("a@example.com", "Ada", "hashed")
    assert store.get_account(account.id) == account
    assert store.get_user_id_by_email("a@example.com") == account.id


def test_duplicate_email_is_rejected(store: AccountStore):
    store.create_user("dup@example.com", "First", "hash-1")
    with pytest.raises(EmailTakenError):
        store.create_user("dup@example.com", "Second", "hash-2")


def test_unknown_account_and_email_return_none(store: AccountStore):
    assert store.get_account("no-such-id") is None
    assert store.get_user_id_by_email("nobody@example.com") is None
    assert store.find_credentials("nobody@example.com") is None


def test_find_credentials_returns_the_stored_hash(store: AccountStore):
    account = store.create_user("c@example.com", "Cy", "the-hash")
    assert store.find_credentials("c@example.com") == (account.id, "the-hash")


def test_update_password_only_affects_the_target_user(store: AccountStore):
    alice, bob = _two_users(store)
    assert store.update_password(alice.id, "new-hash") is True
    assert store.find_credentials("alice@example.com") == (alice.id, "new-hash")
    assert store.find_credentials("bob@example.com") == (bob.id, "hash-b")


def test_update_password_for_unknown_user_reports_failure(store: AccountStore):
    assert store.update_password("no-such-id", "irrelevant") is False


# ---- ownership scoping (the IDOR guard) ----


def test_user_cannot_read_another_users_conversation(store: AccountStore):
    alice, bob = _two_users(store)
    conv = store.create_conversation(alice.id, "Alice's private chat")

    assert store.get_conversation(alice.id, conv["id"]) is not None
    assert store.get_conversation(bob.id, conv["id"]) is None


def test_user_cannot_delete_another_users_conversation(store: AccountStore):
    alice, bob = _two_users(store)
    conv = store.create_conversation(alice.id, "Alice's chat")

    assert store.delete_conversation(bob.id, conv["id"]) is False
    # Still there for its owner — Bob's attempt must not have removed it.
    assert store.get_conversation(alice.id, conv["id"]) is not None
    assert store.delete_conversation(alice.id, conv["id"]) is True


def test_user_cannot_append_a_turn_to_another_users_conversation(store: AccountStore):
    alice, bob = _two_users(store)
    conv = store.create_conversation(alice.id, "Alice's chat")

    assert store.append_turn(bob.id, conv["id"], "q", "a", None) is False
    assert store.get_conversation(alice.id, conv["id"])["messages"] == []


def test_listing_shows_only_your_own_conversations(store: AccountStore):
    alice, bob = _two_users(store)
    store.create_conversation(alice.id, "Alice one")
    store.create_conversation(alice.id, "Alice two")
    store.create_conversation(bob.id, "Bob one")

    assert {c["title"] for c in store.list_conversations(alice.id)} == {"Alice one", "Alice two"}
    assert [c["title"] for c in store.list_conversations(bob.id)] == ["Bob one"]


def test_operations_on_a_nonexistent_conversation_fail_closed(store: AccountStore):
    alice, _ = _two_users(store)
    assert store.get_conversation(alice.id, "no-such-conversation") is None
    assert store.delete_conversation(alice.id, "no-such-conversation") is False
    assert store.append_turn(alice.id, "no-such-conversation", "q", "a", None) is False


# ---- conversations & messages ----


def test_blank_title_falls_back_to_a_default(store: AccountStore):
    alice, _ = _two_users(store)
    assert store.create_conversation(alice.id, "   ")["title"] == "New chat"


def test_turns_are_stored_in_order_as_user_then_assistant(store: AccountStore):
    alice, _ = _two_users(store)
    conv = store.create_conversation(alice.id, "Ordering")

    assert store.append_turn(alice.id, conv["id"], "first q", "first a", None) is True
    assert store.append_turn(alice.id, conv["id"], "second q", "second a", None) is True

    messages = store.get_conversation(alice.id, conv["id"])["messages"]
    assert [(m["role"], m["content"]) for m in messages] == [
        ("user", "first q"),
        ("assistant", "first a"),
        ("user", "second q"),
        ("assistant", "second a"),
    ]


def test_citation_meta_round_trips_so_reopening_restores_sources(store: AccountStore):
    """The whole point of storing meta: a reopened conversation keeps its citations."""
    alice, _ = _two_users(store)
    conv = store.create_conversation(alice.id, "With citations")
    meta = {
        "citations": [{"marker": 1, "chunk_id": "constitution-fundamental-rights.md#10"}],
        "status": "grounded",
    }
    store.append_turn(alice.id, conv["id"], "rights on arrest?", "Article 10 [1].", meta)

    messages = store.get_conversation(alice.id, conv["id"])["messages"]
    assert messages[0]["meta"] is None  # the user turn carries no meta
    assert messages[1]["meta"] == meta


def test_appending_a_turn_bumps_updated_at(store: AccountStore):
    alice, _ = _two_users(store)
    conv = store.create_conversation(alice.id, "Touch me")
    before = store.list_conversations(alice.id)[0]["updated_at"]

    store.append_turn(alice.id, conv["id"], "q", "a", None)
    after = store.list_conversations(alice.id)[0]["updated_at"]
    assert after >= before


def test_deleting_a_conversation_cascades_to_its_messages(tmp_path):
    """Cascade needs PRAGMA foreign_keys per connection — assert it actually holds."""
    db = tmp_path / "cascade.db"
    store = AccountStore(db)
    alice = store.create_user("alice@example.com", "Alice", "hash-a")
    conv = store.create_conversation(alice.id, "Doomed")
    store.append_turn(alice.id, conv["id"], "q", "a", None)

    def message_count() -> int:
        with sqlite3.connect(db) as conn:
            return conn.execute(
                "SELECT COUNT(*) FROM messages WHERE conversation_id = ?", (conv["id"],)
            ).fetchone()[0]

    assert message_count() == 2
    assert store.delete_conversation(alice.id, conv["id"]) is True
    assert message_count() == 0


def test_schema_is_idempotent_across_reopens(tmp_path):
    """Reopening the same file must not fail or lose data (CREATE TABLE IF NOT EXISTS)."""
    db = tmp_path / "reopen.db"
    first = AccountStore(db)
    account = first.create_user("keep@example.com", "Keep", "hash")

    second = AccountStore(db)
    assert second.get_account(account.id) is not None
