import uuid

import pytest
from langchain_core.messages import AIMessage
from pydantic import ValidationError

from app.schemas import ChatRequest, ChatResponse, message_text

"""ChatRequest - rejects"""
# Test empty message validation error
def test_empty_message_rejected():
    with pytest.raises(ValidationError):
        ChatRequest(message="", thread_id=uuid.uuid4())

# Whiespace-only message -> validation error
def test_whitespace_only_message_rejected():
    with pytest.raises(ValidationError):
        ChatRequest(message="   ", thread_id=uuid.uuid4())


# 4001 chars -> validation error
def test_4001_chars_validation_error():
    with pytest.raises(ValidationError):
        ChatRequest(message="x" * 4001, thread_id=uuid.uuid4())

# Unknown extra field -> validation error
def test_unknown_extra_field_validation_error():
    with pytest.raises(ValidationError):
        ChatRequest(message="x", thread_id=uuid.uuid4(), extra_field="extra")

# Non-UUID thread_id -> validation error
def test_non_uuid_thread_id_validation_error():
    with pytest.raises(ValidationError):
        ChatRequest(message="x", thread_id="not_a_uuid")

"""Chat Request - accepts"""
# vallid message + uuid string 
def test_valid_request_strip_whitespace_and_parses_uuid():
    req = ChatRequest(message="  hello ", thread_id="1af23fc2-26de-4f31-b7ac-e8f40ea82122")
    assert req.message == "hello"
    assert isinstance(req.thread_id, uuid.UUID)

# Test message at exactly 4000 chars is accepted
def test_message_at_exactly_4000_chars_accepted():
    req = ChatRequest(message="x" * 4000, thread_id=uuid.uuid4())
    assert len(req.message) == 4000

""" Chat Response """
# Empty answer -> validation error
def test_empty_answer_validation_error():
    with pytest.raises(ValidationError):
        ChatResponse(answer="", thread_id=uuid.uuid4(), tool_rounds=0, soft_limit_reached=False)

# Negative tool_rounds -> validation error
def test_negative_tool_rounds_validation_error():
    with pytest.raises(ValidationError):
        ChatResponse(answer="x", thread_id=uuid.uuid4(), tool_rounds=-1, soft_limit_reached=False)

# A long answer validates fine. tests no cap on answer
def test_long_answer_validates_fine():
    resp = ChatResponse(answer="x" * 10000, thread_id=uuid.uuid4(), tool_rounds=0, soft_limit_reached=False)
    assert resp.answer == "x" * 10000

"""Message Text"""
# Plain string content -> returned as is
def test_plain_string_content_returned_as_is():
    msg = AIMessage(content="Hello, world!")
    assert message_text(msg) == "Hello, world!"
# List of text dicts -> concatenated
def test_list_of_text_dicts_concatenated():
    msg = AIMessage(content=[{"type": "text", "text": "Hello, "}, {"type": "text", "text": "world!"}])
    assert message_text(msg) == "Hello, world!"
# Mixed list with a tool_use block -> tool_use skipped, text kept
def test_mixed_list_with_tool_use_block_tool_use_skipped_text_kept():
    msg = AIMessage(content=[{"type": "text", "text": "Hello, "}, {"type": "tool_use", "id": "toolu_123", "name": "get_checkout_history", "input": {"asset_id": "101"}}, {"type": "text", "text": "world!"}])
    assert message_text(msg) == "Hello, world!"
# Malformed {"type": "text", "text": None} -> skipped, no crash
def test_malformed_text_none_skipped_no_crash():
    msg = AIMessage(content=[{"type": "text", "text": None}])
    assert message_text(msg) == ""
# All non text content -> returns ""
def test_all_non_text_content_returns_empty_string():
    msg = AIMessage(content=[{"type": "tool_use", "id": "toolu_123", "name": "get_checkout_history", "input": {"asset_id": "101"}}])
    assert message_text(msg) == ""

