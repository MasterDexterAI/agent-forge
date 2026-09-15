# postgres checkpoint setup for langchain

from psycopg_pool import AsyncConnectionPool
from psycopg.rows import dict_row
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
import os

async def initialize_checkpointer():
    pool = AsyncConnectionPool(
        conninfo=os.environ["DATABASE_URL"],
        max_size=10,
        kwargs={"autocommit": True, "prepare_threshold": 0, "row_factory": dict_row},
    )
    checkpointer = AsyncPostgresSaver(conn=pool)
    await checkpointer.setup()
    return checkpointer