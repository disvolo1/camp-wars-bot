import sqlite3
from pathlib import Path


DB_PATH = Path("camp_wars.db")


DEFAULT_TEAMS = [
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
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def init_database():
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS teams (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            score INTEGER NOT NULL DEFAULT 0
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS score_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            team_id INTEGER NOT NULL,
            team_name TEXT NOT NULL,
            points INTEGER NOT NULL,
            new_score INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            username TEXT,
            first_name TEXT,
            activity TEXT,
            result TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Для уже существующей базы добавляем новые колонки,
    # если их ещё нет.
    cursor.execute(
        "PRAGMA table_info(score_history)"
    )

    columns = {
        row["name"]
        for row in cursor.fetchall()
    }

    if "activity" not in columns:
        cursor.execute("""
            ALTER TABLE score_history
            ADD COLUMN activity TEXT
        """)

    if "result" not in columns:
        cursor.execute("""
            ALTER TABLE score_history
            ADD COLUMN result TEXT
        """)

    cursor.execute(
        "SELECT COUNT(*) FROM teams"
    )

    count = cursor.fetchone()[0]

    if count == 0:
        for team_name in DEFAULT_TEAMS:
            cursor.execute("""
                INSERT INTO teams (name, score)
                VALUES (?, 0)
            """, (team_name,))

    connection.commit()
    connection.close()


def get_teams():
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT id, name, score
        FROM teams
        ORDER BY id
    """)

    teams = cursor.fetchall()

    connection.close()

    return teams


def get_team(team_id: int):
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT id, name, score
        FROM teams
        WHERE id = ?
    """, (team_id,))

    team = cursor.fetchone()

    connection.close()

    return team


def add_points(
    team_id: int,
    points: int,
    user_id: int,
    username: str | None,
    first_name: str | None,
    activity: str | None = None,
    result: str | None = None,
):
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT id, name, score
        FROM teams
        WHERE id = ?
    """, (team_id,))

    team = cursor.fetchone()

    if team is None:
        connection.close()
        raise ValueError("Команда не найдена")

    new_score = team["score"] + points

    cursor.execute("""
        UPDATE teams
        SET score = ?
        WHERE id = ?
    """, (
        new_score,
        team_id,
    ))

    cursor.execute("""
        INSERT INTO score_history (
            team_id,
            team_name,
            points,
            new_score,
            user_id,
            username,
            first_name,
            activity,
            result
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        team_id,
        team["name"],
        points,
        new_score,
        user_id,
        username,
        first_name,
        activity,
        result,
    ))

    connection.commit()
    connection.close()

    return new_score


def rename_team(
    team_id: int,
    new_name: str,
):
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        UPDATE teams
        SET name = ?
        WHERE id = ?
    """, (
        new_name,
        team_id,
    ))

    connection.commit()

    cursor.execute("""
        SELECT id, name, score
        FROM teams
        WHERE id = ?
    """, (team_id,))

    team = cursor.fetchone()

    connection.close()

    return team


def get_history(limit: int = 50):
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            id,
            team_id,
            team_name,
            points,
            new_score,
            user_id,
            username,
            first_name,
            activity,
            result,
            created_at
        FROM score_history
        ORDER BY id DESC
        LIMIT ?
    """, (limit,))

    history = cursor.fetchall()

    connection.close()

    return history
