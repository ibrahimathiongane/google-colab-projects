import os

import models
from alembic import context
from sqlalchemy import create_engine

config = context.config
target_metadata = models.Base.metadata


def run_migrations_offline() -> None:
    url = os.environ["DATABASE_URL"]
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    context.begin_transaction()
    context.run_migrations()


def run_migrations_online() -> None:
    url = os.environ["DATABASE_URL"]
    engine = create_engine(url)
    with engine.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )
        with context.begin_transaction():
            context.run_migrations()
    engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
