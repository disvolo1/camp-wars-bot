import os
import asyncio
import logging

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.exceptions import TelegramBadRequest

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
# ЛОГИ
# ============================================================

logging.basicConfig(
    level=logging.INFO
)


# ============================================================
# BOT
# ============================================================

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()


# ============================================================
# ВРЕМЕННОЕ СОСТОЯНИЕ ПОЛЬЗОВАТЕЛЕЙ
# ============================================================

user_state = {}


# ============================================================
# БАЛЛЫ
# ============================================================

REGULAR_WIN_POINTS = 100

BIG_TOURNAMENT_POINTS = {
    "1": 500,
    "2": 300,
    "3": 150,
}


# ============================================================
# ОБЫЧНЫЕ АКТИВНОСТИ
# ============================================================

REGULAR_ACTIVITIES = [
    ("football", "⚽ Футбол"),
    ("volleyball", "🏐 Волейбол"),
    ("pingpong", "🏓 Пинг-понг"),
    ("streetball", "🏀 Стритбол"),
    ("badminton", "🏸 Бадминтон"),
    ("tablegames", "🎲 Настолки"),
]


# ============================================================
# БОЛЬШИЕ ТУРНИРЫ
# ============================================================

BIG_TOURNAMENTS = [
    ("pingpong", "🏓 Пинг-понг"),
]


# ============================================================
# БЕЗОПАСНОЕ РЕДАКТИРОВАНИЕ СООБЩЕНИЯ
# ============================================================

async def safe_edit(
    message,
    text,
    reply_markup=None,
):
    try:
        await message.edit_text(
            text,
            reply_markup=reply_markup,
        )

    except TelegramBadRequest as error:

        if "message is not modified" not in str(error):
            raise


# ============================================================
# ГЛАВНОЕ МЕНЮ
# ============================================================

def main_keyboard():

    builder = InlineKeyboardBuilder()

    builder.button(
        text="🏆 Табло",
        callback_data="scoreboard",
    )

    builder.button(
        text="🏅 За активность",
        callback_data="activity",
    )

    builder.button(
        text="➕ Добавить баллы",
        callback_data="manual_points",
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

def back_keyboard(
    callback_data="main_menu"
):

    builder = InlineKeyboardBuilder()

    builder.button(
        text="◀️ Назад",
        callback_data=callback_data,
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
# АКТИВНОСТИ
# ============================================================

def activities_keyboard():

    builder = InlineKeyboardBuilder()

    for key, name in REGULAR_ACTIVITIES:

        builder.button(
            text=name,
            callback_data=f"regular_activity:{key}",
        )

    builder.button(
        text="🏆 Большие турниры",
        callback_data="big_tournament",
    )

    builder.button(
        text="◀️ Назад",
        callback_data="main_menu",
    )

    builder.adjust(2)

    return builder.as_markup()


# ============================================================
# МЕСТА В БОЛЬШОМ ТУРНИРЕ
# ============================================================

def tournament_places_keyboard():

    builder = InlineKeyboardBuilder()

    builder.button(
        text="🥇 1 место — +500",
        callback_data="tournament_place:1",
    )

    builder.button(
        text="🥈 2 место — +300",
        callback_data="tournament_place:2",
    )

    builder.button(
        text="🥉 3 место — +150",
        callback_data="tournament_place:3",
    )

    builder.button(
        text="◀️ Назад",
        callback_data="big_tournament",
    )

    builder.adjust(1)

    return builder.as_markup()


# ============================================================
# ПОДТВЕРЖДЕНИЕ
# ============================================================

def confirm_keyboard():

    builder = InlineKeyboardBuilder()

    builder.button(
        text="✅ Начислить",
        callback_data="confirm_points",
    )

    builder.button(
        text="❌ Отмена",
        callback_data="cancel_points",
    )

    builder.adjust(2)

    return builder.as_markup()


# ============================================================
# /START
# ============================================================

@dp.message(Command("start"))
async def start(
    message: Message,
):

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

    await safe_edit(
        callback.message,
        "🔥 CAMP WARS\n\n"
        "Панель управления:",
        main_keyboard(),
    )

    await callback.answer()


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

    teams = sorted(
        teams,
        key=lambda team: team["score"],
        reverse=True,
    )

    medals = {
        1: "🥇",
        2: "🥈",
        3: "🥉",
    }

    lines = [
        "🔥 CAMP WARS",
        "",
        "🏆 ОБЩИЙ РЕЙТИНГ",
        "",
    ]

    for position, team in enumerate(
        teams,
        start=1,
    ):

        prefix = medals.get(
            position,
            f"{position}.",
        )

        lines.append(
            f"{prefix} {team['name']} — {team['score']}"
        )

    await safe_edit(
        callback.message,
        "\n".join(lines),
        main_keyboard(),
    )

    await callback.answer()


# ============================================================
# ЗА АКТИВНОСТЬ
# ============================================================

@dp.callback_query(
    F.data == "activity"
)
async def activity(
    callback: CallbackQuery,
):

    user_state.pop(
        callback.from_user.id,
        None,
    )

    await safe_edit(
        callback.message,
        "🏅 ЗА АКТИВНОСТЬ\n\n"
        "Выберите мероприятие:",
        activities_keyboard(),
    )

    await callback.answer()


# ============================================================
# ВЫБОР ОБЫЧНОЙ АКТИВНОСТИ
# ============================================================

@dp.callback_query(
    F.data.startswith("regular_activity:")
)
async def regular_activity(
    callback: CallbackQuery,
):

    activity_key = callback.data.split(":")[1]

    activity_name = None

    for key, name in REGULAR_ACTIVITIES:

        if key == activity_key:
            activity_name = name
            break

    if activity_name is None:

        await callback.answer(
            "Активность не найдена",
            show_alert=True,
        )

        return

    user_state[
        callback.from_user.id
    ] = {
        "action": "regular_activity",
        "activity": activity_name,
        "points": REGULAR_WIN_POINTS,
        "result": "🥇 Победа",
    }

    await safe_edit(
        callback.message,
        f"🏅 {activity_name}\n\n"
        "Выберите команду-победителя:",
        teams_keyboard("regular_team"),
    )

    await callback.answer()


# ============================================================
# ВЫБОР КОМАНДЫ В ОБЫЧНОЙ АКТИВНОСТИ
# ============================================================

@dp.callback_query(
    F.data.startswith("regular_team:")
)
async def regular_team(
    callback: CallbackQuery,
):

    team_id = int(
        callback.data.split(":")[1]
    )

    team = get_team(team_id)

    state = user_state.get(
        callback.from_user.id
    )

    if not team or not state:

        await callback.answer(
            "Начните операцию заново",
            show_alert=True,
        )

        return

    state["team_id"] = team_id

    await safe_edit(
        callback.message,
        "⚠️ ПРОВЕРЬТЕ НАЧИСЛЕНИЕ\n\n"
        f"👥 Команда: {team['name']}\n"
        f"🏅 Активность: {state['activity']}\n"
        f"🏆 Результат: Победа\n"
        f"➕ Баллы: {state['points']}\n\n"
        "Всё верно?",
        confirm_keyboard(),
    )

    await callback.answer()


# ============================================================
# БОЛЬШИЕ ТУРНИРЫ
# ============================================================

@dp.callback_query(
    F.data == "big_tournament"
)
async def big_tournament(
    callback: CallbackQuery,
):

    builder = InlineKeyboardBuilder()

    for key, name in BIG_TOURNAMENTS:

        builder.button(
            text=name,
            callback_data=f"big_activity:{key}",
        )

    builder.button(
        text="◀️ Назад",
        callback_data="activity",
    )

    builder.adjust(1)

    await safe_edit(
        callback.message,
        "🏆 БОЛЬШИЕ ТУРНИРЫ\n\n"
        "Выберите турнир:",
        builder.as_markup(),
    )

    await callback.answer()


# ============================================================
# ВЫБОР БОЛЬШОГО ТУРНИРА
# ============================================================

@dp.callback_query(
    F.data.startswith("big_activity:")
)
async def big_activity(
    callback: CallbackQuery,
):

    tournament_key = callback.data.split(":")[1]

    tournament_name = None

    for key, name in BIG_TOURNAMENTS:

        if key == tournament_key:
            tournament_name = name
            break

    if tournament_name is None:

        await callback.answer(
            "Турнир не найден",
            show_alert=True,
        )

        return

    user_state[
        callback.from_user.id
    ] = {
        "action": "big_tournament",
        "activity": f"🏆 {tournament_name}",
    }

    await safe_edit(
        callback.message,
        f"🏆 {tournament_name}\n\n"
        "Выберите команду:",
        teams_keyboard("big_team"),
    )

    await callback.answer()


# ============================================================
# ВЫБОР КОМАНДЫ В БОЛЬШОМ ТУРНИРЕ
# ============================================================

@dp.callback_query(
    F.data.startswith("big_team:")
)
async def big_team(
    callback: CallbackQuery,
):

    team_id = int(
        callback.data.split(":")[1]
    )

    team = get_team(team_id)

    state = user_state.get(
        callback.from_user.id
    )

    if not team or not state:

        await callback.answer(
            "Начните операцию заново",
            show_alert=True,
        )

        return

    state["team_id"] = team_id

    await safe_edit(
        callback.message,
        f"{state['activity']}\n\n"
        f"👥 {team['name']}\n\n"
        "Выберите занятое место:",
        tournament_places_keyboard(),
    )

    await callback.answer()


# ============================================================
# МЕСТО В БОЛЬШОМ ТУРНИРЕ
# ============================================================

@dp.callback_query(
    F.data.startswith("tournament_place:")
)
async def tournament_place(
    callback: CallbackQuery,
):

    place = callback.data.split(":")[1]

    state = user_state.get(
        callback.from_user.id
    )

    if not state:

        await callback.answer(
            "Начните операцию заново",
            show_alert=True,
        )

        return

    points = BIG_TOURNAMENT_POINTS.get(
        place
    )

    if points is None:

        await callback.answer(
            "Ошибка баллов",
            show_alert=True,
        )

        return

    team = get_team(
        state["team_id"]
    )

    if not team:

        await callback.answer(
            "Команда не найдена",
            show_alert=True,
        )

        return

    medals = {
        "1": "🥇",
        "2": "🥈",
        "3": "🥉",
    }

    state["points"] = points
    state["result"] = (
        f"{medals[place]} {place} место"
    )

    await safe_edit(
        callback.message,
        "⚠️ ПРОВЕРЬТЕ НАЧИСЛЕНИЕ\n\n"
        f"👥 Команда: {team['name']}\n"
        f"🏆 Турнир: {state['activity']}\n"
        f"🏅 Результат: {place} место\n"
        f"➕ Баллы: {points}\n\n"
        "Всё верно?",
        confirm_keyboard(),
    )

    await callback.answer()


# ============================================================
# РУЧНОЕ НАЧИСЛЕНИЕ
# ============================================================

@dp.callback_query(
    F.data == "manual_points"
)
async def manual_points(
    callback: CallbackQuery,
):

    user_state[
        callback.from_user.id
    ] = {
        "action": "manual",
    }

    await safe_edit(
        callback.message,
        "➕ ДОБАВИТЬ БАЛЛЫ\n\n"
        "Выберите команду:",
        teams_keyboard("manual_team"),
    )

    await callback.answer()


# ============================================================
# КОМАНДА ДЛЯ РУЧНОГО НАЧИСЛЕНИЯ
# ============================================================

@dp.callback_query(
    F.data.startswith("manual_team:")
)
async def manual_team(
    callback: CallbackQuery,
):

    team_id = int(
        callback.data.split(":")[1]
    )

    team = get_team(team_id)

    if not team:

        await callback.answer(
            "Команда не найдена",
            show_alert=True,
        )

        return

    user_state[
        callback.from_user.id
    ] = {
        "action": "manual",
        "team_id": team_id,
    }

    await safe_edit(
        callback.message,
        "➕ ДОБАВИТЬ БАЛЛЫ\n\n"
        f"👥 {team['name']}\n"
        f"🏆 Текущий счёт: {team['score']}\n\n"
        "Введите количество баллов числом.\n\n"
        "Например: 250",
        back_keyboard(),
    )

    await callback.answer()


# ============================================================
# ПОДТВЕРЖДЕНИЕ
# ============================================================

@dp.callback_query(
    F.data == "confirm_points"
)
async def confirm_points(
    callback: CallbackQuery,
):

    state = user_state.get(
        callback.from_user.id
    )

    if not state:

        await callback.answer(
            "Начисление устарело",
            show_alert=True,
        )

        return

    team_id = state.get("team_id")
    points = state.get("points")

    if not team_id or points is None:

        await callback.answer(
            "Недостаточно данных",
            show_alert=True,
        )

        return

    team_before = get_team(team_id)

    if not team_before:

        await callback.answer(
            "Команда не найдена",
            show_alert=True,
        )

        return

    username = callback.from_user.username
    first_name = callback.from_user.first_name

    new_score = add_points(
        team_id=team_id,
        points=points,
        user_id=callback.from_user.id,
        username=username,
        first_name=first_name,
        activity=state.get("activity"),
        result=state.get("result"),
    )

    team_after = get_team(team_id)

    activity_name = (
        state.get("activity")
        or "—"
    )

    result = (
        state.get("result")
        or "—"
    )

    user_state.pop(
        callback.from_user.id,
        None,
    )

    await safe_edit(
        callback.message,
        "✅ БАЛЛЫ НАЧИСЛЕНЫ!\n\n"
        f"👥 {team_after['name']}\n"
        f"🏅 {activity_name}\n"
        f"🏆 {result}\n"
        f"➕ +{points}\n"
        f"💰 Новый счёт: {new_score}",
        main_keyboard(),
    )

    await callback.answer(
        "Баллы начислены!"
    )


# ============================================================
# ОТМЕНА
# ============================================================

@dp.callback_query(
    F.data == "cancel_points"
)
async def cancel_points(
    callback: CallbackQuery,
):

    user_state.pop(
        callback.from_user.id,
        None,
    )

    await safe_edit(
        callback.message,
        "❌ Начисление отменено.",
        main_keyboard(),
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

        await safe_edit(
            callback.message,
            "📜 ИСТОРИЯ\n\n"
            "Изменений пока нет.",
            back_keyboard(),
        )

        await callback.answer()

        return

    lines = [
        "📜 ИСТОРИЯ ИЗМЕНЕНИЙ",
        "",
    ]

    for item in history_items:

        username = item["username"]

        if username:
            author = f"@{username}"
        elif item["first_name"]:
            author = item["first_name"]
        else:
            author = f"ID {item['user_id']}"

        points = item["points"]

        if points > 0:
            points_text = f"+{points}"
        else:
            points_text = str(points)

        activity_name = (
            item["activity"]
            or "—"
        )

        result = (
            item["result"]
            or "—"
        )

        lines.append(
            f"👥 {item['team_name']}\n"
            f"🏅 {activity_name}\n"
            f"🏆 {result}\n"
            f"💰 {points_text} → {item['new_score']}\n"
            f"👤 {author}\n"
            f"🕐 {item['created_at']}\n"
        )

    text = "\n".join(lines)

    # Telegram имеет ограничение длины сообщения.
    if len(text) > 3900:
        text = text[:3900] + "\n\n..."

    await safe_edit(
        callback.message,
        text,
        back_keyboard(),
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

    await safe_edit(
        callback.message,
        "✏️ НАЗВАНИЯ КОМАНД\n\n"
        "Выберите команду:",
        teams_keyboard("rename_team"),
    )

    await callback.answer()


# ============================================================
# ВЫБОР КОМАНДЫ ДЛЯ ПЕРЕИМЕНОВАНИЯ
# ============================================================

@dp.callback_query(
    F.data.startswith("rename_team:")
)
async def rename_team_select(
    callback: CallbackQuery,
):

    team_id = int(
        callback.data.split(":")[1]
    )

    team = get_team(team_id)

    if not team:

        await callback.answer(
            "Команда не найдена",
            show_alert=True,
        )

        return

    user_state[
        callback.from_user.id
    ] = {
        "action": "rename",
        "team_id": team_id,
    }

    await safe_edit(
        callback.message,
        "✏️ ПЕРЕИМЕНОВАНИЕ\n\n"
        f"Текущее название:\n"
        f"{team['name']}\n\n"
        "Введите новое название команды:",
        back_keyboard(),
    )

    await callback.answer()


# ============================================================
# ТЕКСТОВЫЕ СООБЩЕНИЯ
# ============================================================

@dp.message(F.text)
async def text_handler(
    message: Message,
):

    user_id = message.from_user.id

    state = user_state.get(user_id)

    if not state:
        return

    text = message.text.strip()

    # ========================================================
    # РУЧНОЕ КОЛИЧЕСТВО БАЛЛОВ
    # ========================================================

    if state.get("action") == "manual":

        try:
            points = int(text)
        except ValueError:

            await message.answer(
                "❌ Нужно ввести число.\n\n"
                "Например: 250"
            )

            return

        if points <= 0:

            await message.answer(
                "❌ Количество баллов должно быть больше 0."
            )

            return

        team_id = state.get("team_id")

        team = get_team(team_id)

        if not team:

            user_state.pop(
                user_id,
                None,
            )

            await message.answer(
                "❌ Команда не найдена.",
                reply_markup=main_keyboard(),
            )

            return

        state["points"] = points
        state["activity"] = "✏️ Ручное начисление"
        state["result"] = "Вручную"

        await message.answer(
            "⚠️ ПРОВЕРЬТЕ НАЧИСЛЕНИЕ\n\n"
            f"👥 Команда: {team['name']}\n"
            f"➕ Баллы: +{points}\n\n"
            "Всё верно?",
            reply_markup=confirm_keyboard(),
        )

        return

    # ========================================================
    # ПЕРЕИМЕНОВАНИЕ
    # ========================================================

    if state.get("action") == "rename":

        if len(text) > 40:

            await message.answer(
                "❌ Название слишком длинное.\n"
                "Максимум 40 символов."
            )

            return

        if len(text) < 1:

            await message.answer(
                "❌ Название не может быть пустым."
            )

            return

        team_id = state.get("team_id")

        team = rename_team(
            team_id,
            text,
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


if __name__ == "__main__":
    asyncio.run(main())
