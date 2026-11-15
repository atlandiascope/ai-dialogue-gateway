import json
import pytest

from sylvie_runtime.memory import SQLiteMemoryStore


def test_memory_requires_explicit_consent(tmp_path):
    store = SQLiteMemoryStore(tmp_path / "memory.db")
    with pytest.raises(PermissionError):
        store.remember("alice", "Likes concise answers")


def test_memory_is_persistent_and_user_scoped(tmp_path):
    path = tmp_path / "memory.db"
    store = SQLiteMemoryStore(path)
    store.set_consent("alice", True)
    record = store.remember("alice", "Prefers concise answers", category="preferences")
    reopened = SQLiteMemoryStore(path)
    assert reopened.retrieve("alice")[0].memory_id == record.memory_id
    assert reopened.retrieve("bob") == []
    assert reopened.delete("bob", record.memory_id) is False
    assert reopened.delete("alice", record.memory_id) is True


def test_opt_out_deletes_existing_memories(tmp_path):
    store = SQLiteMemoryStore(tmp_path / "memory.db")
    store.set_consent("alice", True)
    store.remember("alice", "Remember this")
    store.set_consent("alice", False)
    assert store.retrieve("alice") == []
    with pytest.raises(PermissionError):
        store.remember("alice", "Do not save")


def test_limits_and_export(tmp_path):
    store = SQLiteMemoryStore(tmp_path / "memory.db", max_records_per_user=1)
    store.set_consent("alice", True)
    store.remember("alice", "First")
    store.remember("alice", "Second")
    records = json.loads(store.export("alice"))
    assert len(records) == 1
    assert records[0]["content"] == "Second"
    with pytest.raises(ValueError):
        store.retrieve("alice", limit=101)
