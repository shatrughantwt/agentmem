from agentmem.models import Memory, TraceEvent


def test_memory_defaults():
    m = Memory(user_id="boruto", content="Prefers TypeScript")
    assert m.id.startswith("mem_")
    assert m.valid_to is None
    assert m.access_count == 0


def test_trace_event_requires_reason():
    t = TraceEvent(op="add", user_id="boruto", input="hi", reason="new fact")
    assert t.result == {}