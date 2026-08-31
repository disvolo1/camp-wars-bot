import sqlite3
from pathlib import Path


DB_PATH = Path("camp_wars.db")


TEAMS = [
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


def get_connection():

    connection = sqlite3.connect(
        DB_PATH
    )

    connection.row_factory = sqlite3.Row

    return connection


def init_database():

    connection = get_connection()

    cursor = connection.cursor()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS teams (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            score INTEGER NOT NULL DEFAULT 0
        )
        """
    )

    cursor.execute(
        "SELECT COUNT(*) FROM teams"
    )

    count = cursor.fetchone()[0]

    if count == 0:

        for team in TEAMS:

            cursor.execute(
                """
                INSERT INTO teams (name, score)
                VALUES (?, 0)
                """,
                (team,),
            )

    connection.commit()

    connection.close()


def add_points(
    team_name: str,
    points: int,
):

    connection = get_connection()

    cursor = connection.cursor()

    cursor.execute(
        """
        UPDATE teams
        SET score = score + ?
        WHERE name = ?
        """,
        (
            points,
            team_name,
        ),
    )

    connection.commit()

    cursor.execute(
        """
        SELECT score
        FROM teams
        WHERE name = ?
        """,
        (team_name,),
    )

    row = cursor.fetchone()

    connection.close()

    if row is None:
        raise ValueError(
            f"Команда не найдена: {team_name}"
        )

    return row["score"]


def get_scores():

    connection = get_connection()

    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT name, score
        FROM teams
        ORDER BY score DESC
        """
    )

    teams = cursor.fetchall()

    connection.close()

    return teams
