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

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()


# ============================================================
# СОСТОЯНИЕ ПОЛЬЗОВАТЕЛЕЙ
# ============================================================

user_state = {}


# ============================================================
# АКТИВНОСТИ
# ============================================================

# Обычная активность:
# победа = 100

REGULAR_ACTIVITIES = [
    ("football", "⚽ Футбол"),
    ("volleyball", "🏐 Волейбол"),
    ("pingpong", "🏓 Пинг-понг"),
    ("streetball", "🏀 Стритбол"),
    ("badminton", "🏸 Бадминтон"),
    ("tablegames", "🎲 Настолки"),
]


# Большой турнир:
# 1 место = 500
# 2 место = 300
# 3 место = 150

BIG_TOURNAMENTS = [
    ("pingpong", "🏓 Пинг-понг"),
]


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
        text="➕ Вручную",
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
# НАЗАД
# ============================================================

def back_keyboard():

    builder = InlineKeyboardBuilder()

    builder.button(
        text="◀️ Назад",
        callback_data="main_menu",
    )

    return builder.as_markup()


# ============================================================
# КОМАНДЫ
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
            callback_data=f"activity:{key}",
        )

    builder.button(
        text="🏆 Большой турнир",
        callback_data="big_tournament",
    )

    builder.button(
        text="◀️ Назад",
        callback_data="main_menu",
    )

    builder.adjust(2)

    return builder.as_markup()


# ============================================================
# РЕЗУЛЬТАТЫ ОБЫЧНОЙ АКТИВНОСТИ
# ============================================================

def regular_result_keyboard():

    builder = InlineKeyboardBuilder()

    builder.button(
        text=f"🥇 Победа +{REGULAR_WIN_POINTS}",
        callback_data="regular_result:win",
    )

    builder.button(
        text="◀️ Назад",
        callback_data="activity",
    )

    builder.adjust(1)

    return builder.as_markup()


# ============================================================
# МЕСТА БОЛЬШОГО ТУРНИРА
# ============================================================

def tournament_result_keyboard():

    builder = InlineKeyboardBuilder()

    builder.button(
        text="🥇 1 место +500",
        callback_data="tournament_result:1",
    )

    builder.button(
        text="🥈 2 место +300",
        callback_data="tournament_result:2",
    )

    builder.button(
        text="🥉 3 место +150",
        callback_data="tournament_result:3",
    )

    builder.button(
        text="◀️ Назад",
        callback_data="activity",
    )

    builder.adjust(1)

    return builder.as_markup()


# ============================================================
# ПОДТВЕРЖДЕНИЕ
# ============================================================

def confirmation_keyboard():

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
# АКТИВНОСТЬ
# ============================================================

@dp.callback_query(
    F.data == "activity"
)
async def activity_menu(
    callback: CallbackQuery,
):

    user_state.pop(
        callback.from_user.id,
        None,
    )

    await callback.message.edit_text(
        "🏅 НАЧИСЛИТЬ ЗА АКТИВНОСТЬ\n\n"
        "Выберите мероприятие:",
        reply_markup=activities_keyboard(),
    )

    await callback.answer()


# ============================================================
# ВЫБОР ОБЫЧНОЙ АКТИВНОСТИ
# ============================================================

@dp.callback_query(
    F.data.startswith("activity:")
)
async def select_activity(
    callback: CallbackQuery,
):

    activity_key = callback.data.split(":")[1]

    activity_name = next(
        (
            name
            for key, name
            in REGULAR_ACTIVITIES
            if key == activity_key
        ),
        None,
    )

    if not activity_name:

        await callback.answer(
            "Активность не найдена",
            show_alert=True,
        )

        return

    user_state[
        callback.from_user.id
    ] = {
        "action": "activity",
        "activity": activity_name,
        "points": REGULAR_WIN_POINTS,
    }

    await callback.message.edit_text(
        f"🏅 {activity_name}\n\n"
        "Выберите команду:",
        reply_markup=teams_keyboard(
            "activity_team"
        ),
    )

    await callback.answer()


# ============================================================
# ВЫБОР КОМАНДЫ ОБЫЧНОЙ АКТИВНОСТИ
# ============================================================

@dp.callback_query(
    F.data.startswith("activity_team:")
)
async def select_activity_team(
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

    state = user_state.get(
        callback.from_user.id
    )

    if not state:

        await callback.answer(
            "Начните заново",
            show_alert=True,
        )

        return

    state["team_id"] = team_id
    state["result"] = "🥇 Победа"

    await callback.message.edit_text(
        "⚠️ ПРОВЕРЬТЕ НАЧИСЛЕНИЕ\n\n"
        f"👥 Команда: {team['name']}\n"
        f"🏅 Активность: {state['activity']}\n"
        f"🥇 Результат: Победа\n"
        f"💰 Баллы: +{state['points']}",
        reply_markup=confirmation_keyboard(),
    )

    await callback.answer()


# ============================================================
# БОЛЬШОЙ ТУРНИР
# ============================================================

@dp.callback_query(
    F.data == "big_tournament"
)
async def big_tournament(
    callback: CallbackQuery,
):

    await callback.message.edit_text(
        "🏆 БОЛЬШОЙ ТУРНИР\n\n"
        "Выберите дисциплину:",
        reply_markup=InlineKeyboardBuilder().as_markup(),
    )

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

    await callback.message.edit_reply_markup(
        reply_markup=builder.as_markup()
    )

    await callback.answer()


# ============================================================
# ВЫБОР ДИСЦИПЛИНЫ БОЛЬШОГО ТУРНИРА
# ============================================================

@dp.callback_query(
    F.data.startswith("big_activity:")
)
async def select_big_activity(
    callback: CallbackQuery,
):

    activity_key = callback.data.split(":")[1]

    activity_name = next(
        (
            name
            for key, name
            in BIG_TOURNAMENTS
            if key == activity_key
        ),
        None,
    )

    if not activity_name:

        await callback.answer(
            "Турнир не найден",
            show_alert=True,
        )

        return

    user_state[
        callback.from_user.id
    ] = {
        "action": "big_activity",
        "activity": f"🏆 {activity_name}",
    }

    await callback.message.edit_text(
        f"🏆 {activity_name}\n\n"
        "Выберите команду:",
        reply_markup=teams_keyboard(
            "big_team"
        ),
    )

    await callback.answer()


# ============================================================
# ВЫБОР КОМАНДЫ БОЛЬШОГО ТУРНИРА
# ============================================================

@dp.callback_query(
    F.data.startswith("big_team:")
)
async def select_big_team(
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

    state = user_state.get(
        callback.from_user.id
    )

    if not state:

        await callback.answer(
            "Начните заново",
            show_alert=True,
        )

        return

    state["team_id"] = team_id

    await callback.message.edit_text(
        f"{state['activity']}\n\n"
        f"👥 {team['name']}\n\n"
        "Какое место заняла команда?",
        reply_markup=tournament_result_keyboard(),
    )

    await callback.answer()


# ============================================================
# ВЫБОР МЕСТА БОЛЬШОГО ТУРНИРА
# ============================================================

@dp.callback_query(
    F.data.startswith("tournament_result:")
)
async def tournament_result(
    callback: CallbackQuery,
):

    place = callback.data.split(":")[1]

    state = user_state.get(
        callback.from_user.id
    )

    if not state:

        await callback.answer(
            "Начните заново",
            show_alert=True,
        )

        return

    points = BIG_TOURNAMENT_POINTS[place]

    state["points"] = points
    state["result"] = f"{place} место"

    team = get_team(
        state["team_id"]
    )

    medals = {
        "1": "🥇",
        "2": "🥈",
        "3": "🥉",
    }

    await callback.message.edit_text(
        "⚠️ ПРОВЕРЬТЕ НАЧИСЛЕНИЕ\n\n"
        f"👥 Команда: {team['name']}\n"
        f"🏆 Турнир: {state['activity']}\n"
        f"{medals[place]} Результат: {place} место\n"
        f"💰 Баллы: +{points}",
        reply_markup=confirmation_keyboard(),
    )

    await callback.answer()


# ============================================================
# ПОДТВЕРЖДЕНИЕ НАЧИСЛЕНИЯ
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

    team_id = state["team_id"]
    points = state["points"]

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

    team = get_team(team_id)

    user_state.pop(
        callback.from_user.id,
        None,
    )

    await callback.message.edit_text(
        "✅ БАЛЛЫ НАЧИСЛЕНЫ!\n\n"
        f"👥 {team['name']}\n"
        f"🏅 {state.get('activity')}\n"
        f"🏆 {state.get('result')}\n"
        f"➕ +{points}\n"
        f"💰 Новый счёт: {new_score}",
        reply_markup=main_keyboard(),
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

    await callback.message.edit_text(
        "❌ Начисление отменено.",
        reply_markup=main_keyboard(),
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
        "action": "manual_points"
    }

    await callback.message.edit_text(
        "➕ ДОБАВИТЬ БАЛЛЫ ВРУЧНУЮ\n\n"
        "Выберите команду:",
        reply_markup=teams_keyboard(
            "manual_team"
        ),
    )

    await callback.answer()


# ============================================================
# ВЫБОР КОМАНДЫ ДЛЯ РУЧНОГО НАЧИСЛЕНИЯ
# ============================================================

@dp.callback_query(
    F.data.startswith("manual_team:")
)
async def select_manual_team(
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
        "action": "manual_points",
        "team_id": team_id,
    }

    await callback.message.edit_text(
        "➕ ВРУЧНУЮ\n\n"
        f"👥 {team['name']}\n"
        f"🏆 Сейчас: {team['score']}\n\n"
        "Введите количество баллов:",
        reply_markup=back_keyboard(),
    )

    await callback.answer()


# ============================================================
# НАЗВАНИЯ КОМАНД
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

    if not team:

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
        "Введите новое название:",
        reply_markup=back_keyboard(),
    )

    await callback.answer()


# ============================================================
# ТЕКСТОВЫЙ ВВОД
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
    # РУЧНЫЕ БАЛЛЫ
    # ========================================================

    if state.get("action") == "manual_points":

        try:
            points = int(text)
        except ValueError:

            await message.answer(
                "❌ Введите только число.\n\n"
                "Например: 250"
            )

            return

        if points <= 0:

            await message.answer(
                "❌ Баллы должны быть больше 0."
            )

            return

        team_id = state.get("team_id")

        if not team_id:

            user_state.pop(
                user_id,
                None,
            )

            await message.answer(
                "❌ Команда не выбрана."
            )

            return

        team = get_team(team_id)

        state["points"] = points
        state["activity"] = "✏️ Ручное начисление"
        state["result"] = "Вручную"

        await message.answer(
            "⚠️ ПРОВЕРЬТЕ НАЧИСЛЕНИЕ\n\n"
            f"👥 Команда: {team['name']}\n"
            f"💰 Баллы: +{points}\n\n"
            "Подтвердить?",
            reply_markup=confirmation_keyboard(),
        )

        return

    # ========================================================
    # ПЕРЕИМЕНОВАНИЕ
    # ========================================================

    if state.get("action") == "rename_team":

        if len(text) > 40:

            await message.answer(
                "❌ Максимум 40 символов."
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

        if item["username"]:
            author = f"@{item['username']}"
        elif item["first_name"]:
            author = item["first_name"]
        else:
            author = f"ID {item['user_id']}"

        points_text = (
            f"+{item['points']}"
            if item["points"] > 0
            else str(item["points"])
        )

        created_at = str(
            item["created_at"]
        )

        if len(created_at) >= 16:
            created_at = created_at[:16]

        activity = (
            item["activity"]
            or "—"
        )

        result = (
            item["result"]
            or "—"
        )

        lines.append(
            f"🕐 {created_at}\n"
            f"👥 {item['team_name']}\n"
            f"🏅 {activity}\n"
            f"🏆 {result}\n"
            f"💰 {points_text} → {item['new_score']}\n"
            f"👤 {author}\n"
        )

    await callback.message.edit_text(
        "\n".join(lines),
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


if __name__ == "__main__":
    asyncio.run(main())
