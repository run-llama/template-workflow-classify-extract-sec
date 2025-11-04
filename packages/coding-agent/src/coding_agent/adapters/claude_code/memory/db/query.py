import aiosqlite
from contextlib import asynccontextmanager
from typing import AsyncIterator
from .constants import (
    CREATE_VIRTUAL_TABLE_STATEMENT,
    GET_MATCHES_STATEMENT,
    INSERT_RECORD_STATEMENT,
)
from .models import MemoryMatch


@asynccontextmanager
async def sqlite_connection() -> AsyncIterator[aiosqlite.Connection]:
    async with aiosqlite.connect("claude_memory.db") as db:
        yield db


async def init_db() -> None:
    async with sqlite_connection() as conn:
        await conn.execute("PRAGMA journal_mode=WAL;")
        await conn.execute(CREATE_VIRTUAL_TABLE_STATEMENT)
        await conn.commit()


async def get_matches(pattern: str) -> list[MemoryMatch]:
    async with sqlite_connection() as conn:
        rows = await (await conn.execute(GET_MATCHES_STATEMENT, (pattern,))).fetchmany(
            10
        )
        matches: list[MemoryMatch] = []
        for row in rows:
            matches.append(MemoryMatch(content=row[0]))
        return matches


async def insert_record(record: MemoryMatch) -> None:
    async with sqlite_connection() as conn:
        await conn.execute(CREATE_VIRTUAL_TABLE_STATEMENT)
        await conn.execute(INSERT_RECORD_STATEMENT, (record.content,))
        await conn.commit()
