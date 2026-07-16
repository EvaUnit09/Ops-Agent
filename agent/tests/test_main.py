from typing import Any

from app.main import _ensure_checkpoint_schema


async def test_checkpoint_schema_is_created_with_same_role(monkeypatch) -> None:
    class FakeConnection:
        def __init__(self) -> None:
            self.statements: list[Any] = []
            self.closed = False

        async def execute(self, statement: Any) -> None:
            self.statements.append(statement)

        async def close(self) -> None:
            self.closed = True

    connection = FakeConnection()

    class FakeAsyncConnection:
        @classmethod
        async def connect(cls, database_url: str, *, autocommit: bool) -> FakeConnection:
            assert database_url == "postgresql://same-role@db/opsagent"
            assert autocommit is True
            return connection

    monkeypatch.setattr("app.main.AsyncConnection", FakeAsyncConnection)

    await _ensure_checkpoint_schema(
        "postgresql://same-role@db/opsagent",
        "agent_checkpoints",
    )

    assert len(connection.statements) == 1
    assert "CREATE SCHEMA IF NOT EXISTS" in str(connection.statements[0])
    assert "agent_checkpoints" in str(connection.statements[0])
    assert connection.closed is True
