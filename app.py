import os
import asyncio
import logging

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder

from database import (
    init_database,
    get_teams,
    get_team,
    add_points,
    rename_team,
    get_history,
)


# ============================================================
# НАСТРОЙКИ
# ============================================================

BOT_TOKEN = os.getenv("BOT_TOKEN")

if not BOT_TOKEN:
    raise RuntimeError("Не задан BOT_TOKEN")


# ============================================================
# BOT
# ============================================================

logging.basicConfig(
    level=logging.INFO
)

bot = Bot(
    token=BOT_TOKEN
)

dp = Dispatcher()


# ============================================================
# СОСТОЯНИЕ ПОЛЬЗОВАТЕЛЕЙ
# ============================================================

# Здесь временно хранится:
#
# action = "add_points"
# team_id = 3
#
# или
#
# action = "rename_team"
# team_id = 3

user_state = {}


# ============================================================
# ГЛАВНОЕ МЕНЮ
# ============================================================

def main_keyboard():

    builder = InlineKeyboardBuilder()

    builder.button(
        text="➕ Добавить баллы",
        callback_data="add_points",
    )

    builder.button(
        text="🏆 Табло",
        callback_data="scoreboard",
    )

    builder.button(
        text="📜 История",
        callback_data="history",
    )

    builder.button(
        text="✏️ Названия команд",
        callback_data="rename_menu",
    )

    builder.adjust(1)

    return builder.as_markup()


# ============================================================
# КНОПКА НАЗАД
# ============================================================

def back_keyboard():

    builder = InlineKeyboardBuilder()

    builder.button(
        text="◀️ Назад",
        callback_data="main_menu",
    )

    return builder.as_markup()


# ============================================================
# КЛАВИАТУРА КОМАНД
# ============================================================

def teams_keyboard(prefix):

    builder = InlineKeyboardBuilder()

    teams = get_teams()

    for team in teams:

        builder.button(
            text=team["name"],
            callback_data=f"{prefix}:{team['id']}",
        )

    builder.adjust(2)

    builder.button(
        text="◀️ Назад",
        callback_data="main_menu",
    )

    return builder.as_markup()


# ============================================================
# /START
# ============================================================

@dp.message(Command("start"))
async def start(message: Message):

    user_state.pop(
        message.from_user.id,
        None,
    )

    await message.answer(
        "🔥 CAMP WARS\n\n"
        "Панель управления:",
        reply_markup=main_keyboard(),
    )


# ============================================================
# ГЛАВНОЕ МЕНЮ
# ============================================================

@dp.callback_query(
    F.data == "main_menu"
)
async def main_menu(
    callback: CallbackQuery,
):

    user_state.pop(
        callback.from_user.id,
        None,
    )

    await callback.message.edit_text(
        "🔥 CAMP WARS\n\n"
        "Панель управления:",
        reply_markup=main_keyboard(),
    )

    await callback.answer()


# ============================================================
# ДОБАВИТЬ БАЛЛЫ
# ============================================================

@dp.callback_query(
    F.data == "add_points"
)
async def add_points_start(
    callback: CallbackQuery,
):

    user_state[
        callback.from_user.id
    ] = {
        "action": "add_points",
    }

    await callback.message.edit_text(
        "➕ ДОБАВИТЬ БАЛЛЫ\n\n"
        "Выберите команду:",
        reply_markup=teams_keyboard(
            "points_team"
        ),
    )

    await callback.answer()


# ============================================================
# ВЫБОР КОМАНДЫ ДЛЯ ДОБАВЛЕНИЯ БАЛЛОВ
# ============================================================

@dp.callback_query(
    F.data.startswith("points_team:")
)
async def select_points_team(
    callback: CallbackQuery,
):

    team_id = int(
        callback.data.split(":")[1]
    )

    team = get_team(team_id)

    if team is None:

        await callback.answer(
            "Команда не найдена",
            show_alert=True,
        )

        return

    user_state[
        callback.from_user.id
    ] = {
        "action": "add_points",
        "team_id": team_id,
    }

    await callback.message.edit_text(
        "➕ ДОБАВИТЬ БАЛЛЫ\n\n"
        f"👥 {team['name']}\n"
        f"🏆 Сейчас: {team['score']}\n\n"
        "Введите количество баллов.\n\n"
        "Например:\n"
        "250",
        reply_markup=back_keyboard(),
    )

    await callback.answer()


# ============================================================
# ПЕРЕИМЕНОВАНИЕ КОМАНД
# ============================================================

@dp.callback_query(
    F.data == "rename_menu"
)
async def rename_menu(
    callback: CallbackQuery,
):

    await callback.message.edit_text(
        "✏️ НАЗВАНИЯ КОМАНД\n\n"
        "Выберите команду:",
        reply_markup=teams_keyboard(
            "rename_team"
        ),
    )

    await callback.answer()


# ============================================================
# ВЫБОР КОМАНДЫ ДЛЯ ПЕРЕИМЕНОВАНИЯ
# ============================================================

@dp.callback_query(
    F.data.startswith("rename_team:")
)
async def select_rename_team(
    callback: CallbackQuery,
):

    team_id = int(
        callback.data.split(":")[1]
    )

    team = get_team(team_id)

    if team is None:

        await callback.answer(
            "Команда не найдена",
            show_alert=True,
        )

        return

    user_state[
        callback.from_user.id
    ] = {
        "action": "rename_team",
        "team_id": team_id,
    }

    await callback.message.edit_text(
        "✏️ ПЕРЕИМЕНОВАНИЕ\n\n"
        f"Сейчас:\n"
        f"{team['name']}\n\n"
        "Введите новое название команды.",
        reply_markup=back_keyboard(),
    )

    await callback.answer()


# ============================================================
# ЕДИНЫЙ ОБРАБОТЧИК ТЕКСТА
# ============================================================

@dp.message(F.text)
async def text_handler(
    message: Message,
):

    user_id = message.from_user.id

    state = user_state.get(user_id)

    # Если пользователь ничего не делает —
    # игнорируем обычный текст.

    if not state:
        return

    text = message.text.strip()

    # ========================================================
    # ДОБАВЛЕНИЕ БАЛЛОВ
    # ========================================================

    if state.get("action") == "add_points":

        try:

            points = int(text)

        except ValueError:

            await message.answer(
                "❌ Введите только число.\n\n"
                "Например:\n"
                "250"
            )

            return

        if points <= 0:

            await message.answer(
                "❌ Баллы должны быть больше 0.\n\n"
                "Введите положительное число."
            )

            return

        team_id = state.get("team_id")

        if not team_id:

            user_state.pop(
                user_id,
                None,
            )

            await message.answer(
                "❌ Команда не выбрана.\n"
                "Начните заново через /start."
            )

            return

        # Информация о пользователе Telegram

        username = message.from_user.username

        first_name = message.from_user.first_name

        # Начисляем баллы + записываем историю

        new_score = add_points(
            team_id=team_id,
            points=points,
            user_id=user_id,
            username=username,
            first_name=first_name,
        )

        team = get_team(team_id)

        user_state.pop(
            user_id,
            None,
        )

        await message.answer(
            "✅ ГОТОВО!\n\n"
            f"👥 {team['name']}\n"
            f"➕ +{points} баллов\n"
            f"🏆 Новый счёт: {new_score}",
            reply_markup=main_keyboard(),
        )

        return

    # ========================================================
    # ПЕРЕИМЕНОВАНИЕ КОМАНДЫ
    # ========================================================

    if state.get("action") == "rename_team":

        new_name = text

        if not new_name:

            await message.answer(
                "❌ Название не может быть пустым."
            )

            return

        if len(new_name) > 40:

            await message.answer(
                "❌ Название слишком длинное.\n"
                "Максимум 40 символов."
            )

            return

        team_id = state.get("team_id")

        if not team_id:

            user_state.pop(
                user_id,
                None,
            )

            await message.answer(
                "❌ Команда не выбрана.\n"
                "Начните заново через /start."
            )

            return

        team = rename_team(
            team_id,
            new_name,
        )

        user_state.pop(
            user_id,
            None,
        )

        await message.answer(
            "✅ НАЗВАНИЕ ИЗМЕНЕНО!\n\n"
            f"👥 {team['name']}\n"
            f"🏆 Счёт: {team['score']}",
            reply_markup=main_keyboard(),
        )

        return


# ============================================================
# ТАБЛО
# ============================================================

@dp.callback_query(
    F.data == "scoreboard"
)
async def scoreboard(
    callback: CallbackQuery,
):

    teams = get_teams()

    sorted_teams = sorted(
        teams,
        key=lambda team: team["score"],
        reverse=True,
    )

    lines = [
        "🔥 CAMP WARS",
        "",
        "🏆 ОБЩИЙ РЕЙТИНГ",
        "",
    ]

    medals = {
        1: "🥇",
        2: "🥈",
        3: "🥉",
    }

    for position, team in enumerate(
        sorted_teams,
        start=1,
    ):

        prefix = medals.get(
            position,
            f"{position}.",
        )

        lines.append(
            f"{prefix} {team['name']} — {team['score']}"
        )

    await callback.message.edit_text(
        "\n".join(lines),
        reply_markup=main_keyboard(),
    )

    await callback.answer()


# ============================================================
# ИСТОРИЯ
# ============================================================

@dp.callback_query(
    F.data == "history"
)
async def history(
    callback: CallbackQuery,
):

    history_items = get_history(
        limit=30
    )

    if not history_items:

        await callback.message.edit_text(
            "📜 ИСТОРИЯ\n\n"
            "Пока изменений нет.",
            reply_markup=back_keyboard(),
        )

        await callback.answer()

        return

    lines = [
        "📜 ИСТОРИЯ ИЗМЕНЕНИЙ",
        "",
    ]

    for item in history_items:

        # Кто сделал изменение

        if item["username"]:

            author = (
                f"@{item['username']}"
            )

        elif item["first_name"]:

            author = item["first_name"]

        else:

            author = (
                f"ID {item['user_id']}"
            )

        # Баллы

        points = item["points"]

        if points > 0:

            points_text = (
                f"+{points}"
            )

        else:

            points_text = str(points)

        # Дата

        created_at = str(
            item["created_at"]
        )

        # SQLite хранит дату в UTC.
        # Пока показываем её компактно.

        if len(created_at) >= 16:

            created_at = created_at[:16]

        lines.append(
            f"🕐 {created_at}\n"
            f"👥 {item['team_name']}\n"
            f"💰 {points_text} → {item['new_score']}\n"
            f"👤 {author}\n"
        )

    text = "\n".join(lines)

    await callback.message.edit_text(
        text,
        reply_markup=back_keyboard(),
    )

    await callback.answer()


# ============================================================
# ЗАПУСК
# ============================================================

async def main():

    print(
        "🔥 CAMP WARS BOT STARTED"
    )

    init_database()

    await dp.start_polling(
        bot
    )


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":

    asyncio.run(main())
