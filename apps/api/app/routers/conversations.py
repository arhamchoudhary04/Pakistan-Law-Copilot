"""Per-user chat history: list, open, create, delete conversations and save turns.

Every endpoint is scoped to the signed-in account, so users only ever see and
touch their own conversations.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.auth.security import CurrentUser
from app.db.store import get_account_store
from app.models.schemas import (
    ConversationDetail,
    ConversationSummary,
    CreateConversationRequest,
    SaveTurnRequest,
)

router = APIRouter(prefix="/conversations")


@router.get("", response_model=list[ConversationSummary])
def list_conversations(account: CurrentUser) -> list[ConversationSummary]:
    rows = get_account_store().list_conversations(account.id)
    return [ConversationSummary(**r) for r in rows]


@router.post("", response_model=ConversationSummary)
def create_conversation(
    body: CreateConversationRequest, account: CurrentUser
) -> ConversationSummary:
    row = get_account_store().create_conversation(account.id, body.title)
    return ConversationSummary(**row)


@router.get("/{conversation_id}", response_model=ConversationDetail)
def get_conversation(conversation_id: str, account: CurrentUser) -> ConversationDetail:
    convo = get_account_store().get_conversation(account.id, conversation_id)
    if convo is None:
        raise HTTPException(status_code=404, detail="Conversation not found.")
    return ConversationDetail(**convo)


@router.delete("/{conversation_id}", status_code=204)
def delete_conversation(conversation_id: str, account: CurrentUser) -> None:
    if not get_account_store().delete_conversation(account.id, conversation_id):
        raise HTTPException(status_code=404, detail="Conversation not found.")


@router.post("/{conversation_id}/turn", status_code=204)
def save_turn(conversation_id: str, body: SaveTurnRequest, account: CurrentUser) -> None:
    ok = get_account_store().append_turn(
        account.id, conversation_id, body.question, body.answer, body.meta
    )
    if not ok:
        raise HTTPException(status_code=404, detail="Conversation not found.")
