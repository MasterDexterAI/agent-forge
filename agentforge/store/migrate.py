import asyncio
from pathlib import Path

import psycopg

from agentforge.config import settings


async def main() -> None:
    async with await psycopg.AsyncConnection.connect(settings.database_url, autocommit=True) as conn:
        await conn.execute(
            "create table if not exists schema_migrations (name text primary key, applied_at timestamptz default now())"
        )
        rows = await (await conn.execute("select name from schema_migrations")).fetchall()
        done = {row[0] for row in rows}
        for path in sorted(Path("migrations").glob("*.sql")):
            if path.name in done:
                continue
            async with conn.transaction():
                await conn.execute(path.read_text())
                await conn.execute("insert into schema_migrations (name) values (%s)", (path.name,))
            print(f"applied {path.name}")


if __name__ == "__main__":
    asyncio.run(main())
