import pytest
from sylvie_runtime import LocalTestProvider, SylvieRuntime

def test_create_and_send_message():
    runtime = SylvieRuntime(LocalTestProvider())
    conversation_id = runtime.create_conversation()
    answer = runtime.send(conversation_id, "Hello Sylvie")
    assert answer.role == "assistant"
    assert "Hello Sylvie" in answer.content
    assert [m.role for m in runtime.get_history(conversation_id)] == ["user", "assistant"]

def test_rejects_empty_and_oversized_messages():
    runtime = SylvieRuntime(LocalTestProvider(), max_message_chars=5)
    conversation_id = runtime.create_conversation()
    with pytest.raises(ValueError):
        runtime.send(conversation_id, " ")
    with pytest.raises(ValueError):
        runtime.send(conversation_id, "too long")

def test_unknown_conversation_is_rejected():
    runtime = SylvieRuntime(LocalTestProvider())
    with pytest.raises(KeyError):
        runtime.send("not-a-session", "Hello")

def test_history_is_bounded():
    runtime = SylvieRuntime(LocalTestProvider(), max_history_messages=2)
    conversation_id = runtime.create_conversation()
    runtime.send(conversation_id, "one")
    runtime.send(conversation_id, "two")
    assert len(runtime.get_history(conversation_id)) == 2
