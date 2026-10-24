from agentmem.models import Memory
from agentmem.store import Store


def test_save_and_get(tmp_path):
    s = Store(str(tmp_path))
    m = Memory(user_id="u1", content="Prefers TypeScript")
    s.save(m)
    assert s.get(m.id).content == "Prefers TypeScript"


def test_search_is_scoped_to_user(tmp_path):
    s = Store(str(tmp_path))
    s.save(Memory(user_id="u1", content="Lives in Rewa"))
    s.save(Memory(user_id="u2", content="Lives in Paris"))
    hits = s.search("u1", "where does the user live?")
    assert [m.user_id for m, _ in hits] == ["u1"]


def test_supersede_keeps_history_but_hides_from_search(tmp_path):
    s = Store(str(tmp_path))
    old = Memory(user_id="u1", content="Lives in Rewa")
    new = Memory(user_id="u1", content="Lives in Bhopal")
    s.save(old)
    s.save(new)
    s.supersede(old.id, new.id)

    assert s.get(old.id).superseded_by == new.id
    assert s.get(old.id).valid_to is not None
    assert [m.id for m in s.list_active("u1")] == [new.id]
    hits = s.search("u1", "where does the user live?")
    assert old.id not in [m.id for m, _ in hits]