import os

from sqlalchemy import Integer, String, select
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise RuntimeError("Не задан DATABASE_URL")


# Render PostgreSQL обычно отдаёт URL в формате:
# postgresql://...
#
# SQLAlchemy async требует:
# postgresql+asyncpg://...

if DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace(
        "postgresql://",
        "postgresql+asyncpg://",
        1,
    )


engine = create_async_engine(
    DATABASE_URL,
    echo=False,
)


SessionLocal = async_sessionmaker(
    engine,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    pass


class Team(Base):
    __tablename__ = "teams"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
    )

    name: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False,
    )

    score: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )


async def init_database():

    async with engine.begin() as connection:

        await connection.run_sync(
            Base.metadata.create_all
        )

    async with SessionLocal() as session:

        result = await session.execute(
            select(Team)
        )

        teams = result.scalars().all()

        if teams:
            return

        team_names = [
            "🐻 Медведи",
            "🦊 Лисы",
            "🐺 Волки",
            "🦁 Львы",
            "🐯 Тигры",
            "🐼 Панды",
            "🐸 Лягушки",
            "🦅 Орлы",
            "🦄 Единороги",
            "🦈 Акулы",
        ]

        for name in team_names:

            session.add(
                Team(
                    name=name,
                    score=0,
                )
            )

        await session.commit()


async def add_points(
    team_name: str,
    points: int,
):

    async with SessionLocal() as session:

        result = await session.execute(
            select(Team).where(
                Team.name == team_name
            )
        )

        team = result.scalar_one()

        team.score += points

        await session.commit()

        return team.score


async def get_scores():

    async with SessionLocal() as session:

        result = await session.execute(
            select(Team).order_by(
                Team.score.desc()
            )
        )

        return result.scalars().all()
