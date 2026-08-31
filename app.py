import os
import asyncio
import logging

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder

from database import (
    init_database,
    add_points,
    get_scores,
)


# ============================================================
# НАСТРОЙКИ
# ============================================================

BOT_TOKEN = os.getenv("BOT_TOKEN")

if not BOT_TOKEN:
    raise RuntimeError("Не задан BOT_TOKEN")


# ============================================================
# КОМАНДЫ
# ============================================================

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


# ============================================================
# АКТИВНОСТИ
# ============================================================

NORMAL_ACTIVITIES = [
    "🏓 Пинг-понг",
    "🏐 Волейбол",
    "⚽ Футбол",
    "🏀 Стритбол",
    "🏸 Бадминтон",
    "🎲 Настольные игры",
]


TOURNAMENT_ACTIVITIES = [
    "🏆 Большой турнир по пинг-понгу",
    "🏆 Большой турнир по волейболу",
    "🎭 Отрядные сценки",
    "🔥 Гранд-финал",
]


# ============================================================
# СИСТЕМА ОЧКОВ
# ============================================================

NORMAL_WIN_POINTS = 100

TOURNAMENT_POINTS = {
    1: 1000,
    2: 600,
    3: 350,
}

FINAL_POINTS = {
    1: 2000,
    2: 1200,
    3: 700,
}


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

user_state = {}


# ============================================================
# ДОСТУП
# ============================================================

# Сейчас доступ открыт абсолютно всем.
#
# Любой человек может:
# - открыть бота;
# - посмотреть таблицу;
# - записать результат.
#
# Для тестирования это удобно.
#
# Перед лагерем обязательно вернём
# ограничение на запись результатов.

def is_admin(user_id: int) -> bool:
    return True


# ============================================================
# ГЛАВНОЕ МЕНЮ
# ============================================================

def main_keyboard():

    builder = InlineKeyboardBuilder()

    builder.button(
        text="➕ Записать результат",
        callback_data="add_result",
    )

    builder.button(
        text="🏆 Табло",
        callback_data="scoreboard",
    )

    builder.adjust(1)

    return builder.as_markup()


# ============================================================
# КОМАНДЫ
# ============================================================

def teams_keyboard():

    builder = InlineKeyboardBuilder()

    for index, team in enumerate(TEAMS):

        builder.button(
            text=team,
            callback_data=f"team:{index}",
        )

    builder.adjust(2)

    return builder.as_markup()


# ============================================================
# АКТИВНОСТИ
# ============================================================

def activities_keyboard():

    builder = InlineKeyboardBuilder()

    for index, activity in enumerate(
        NORMAL_ACTIVITIES
    ):

        builder.button(
            text=activity,
            callback_data=f"normal:{index}",
        )

    for index, activity in enumerate(
        TOURNAMENT_ACTIVITIES
    ):

        builder.button(
            text=activity,
            callback_data=f"tournament:{index}",
        )

    builder.adjust(1)

    return builder.as_markup()


# ============================================================
# ОБЫЧНЫЙ МАТЧ
# ============================================================

def normal_result_keyboard():

    builder = InlineKeyboardBuilder()

    builder.button(
        text="🏆 ПОБЕДА +100",
        callback_data="normal_win",
    )

    builder.button(
        text="❌ Отмена",
        callback_data="cancel",
    )

    builder.adjust(1)

    return builder.as_markup()


# ============================================================
# БОЛЬШОЙ ТУРНИР
# ============================================================

def tournament_result_keyboard():

    builder = InlineKeyboardBuilder()

    builder.button(
        text="🥇 1 место",
        callback_data="place:1",
    )

    builder.button(
        text="🥈 2 место",
        callback_data="place:2",
    )

    builder.button(
        text="🥉 3 место",
        callback_data="place:3",
    )

    builder.button(
        text="❌ Отмена",
        callback_data="cancel",
    )

    builder.adjust(1)

    return builder.as_markup()


# ============================================================
# ТАБЛО
# ============================================================

def build_scoreboard(teams):

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
        teams,
        start=1,
    ):

        if position <= 3:
            prefix = medals[position]
        else:
            prefix = f"{position}."

        lines.append(
            f"{prefix} {team['name']} — {team['score']}"
        )

    return "\n".join(lines)


# ============================================================
# /START
# ============================================================

@dp.message(Command("start"))
async def start(
    message: Message,
):

    await message.answer(
        "🔥 CAMP WARS\n\n"
        "Панель управления:",
        reply_markup=main_keyboard(),
    )


# ============================================================
# ЗАПИСАТЬ РЕЗУЛЬТАТ
# ============================================================

@dp.callback_query(
    F.data == "add_result"
)
async def add_result_start(
    callback: CallbackQuery,
):

    await callback.message.edit_text(
        "👥 Выберите команду:",
        reply_markup=teams_keyboard(),
    )

    await callback.answer()


# ============================================================
# ВЫБОР КОМАНДЫ
# ============================================================

@dp.callback_query(
    F.data.startswith("team:")
)
async def select_team(
    callback: CallbackQuery,
):

    index = int(
        callback.data.split(":")[1]
    )

    team = TEAMS[index]

    user_state[
        callback.from_user.id
    ] = {
        "team": team
    }

    await callback.message.edit_text(
        f"👥 Команда:\n\n"
        f"{team}\n\n"
        f"🎯 Выберите активность:",
        reply_markup=activities_keyboard(),
    )

    await callback.answer()


# ============================================================
# ВЫБОР АКТИВНОСТИ
# ============================================================

@dp.callback_query(
    F.data.startswith("normal:")
    | F.data.startswith("tournament:")
)
async def select_activity(
    callback: CallbackQuery,
):

    kind, index = callback.data.split(":")

    index = int(index)

    state = user_state.get(
        callback.from_user.id
    )

    if not state:

        await callback.answer(
            "Сессия устарела. Начните заново.",
            show_alert=True,
        )

        return

    # Обычный матч

    if kind == "normal":

        activity = NORMAL_ACTIVITIES[index]

        state["activity"] = activity
        state["kind"] = "normal"

        await callback.message.edit_text(
            f"👥 {state['team']}\n\n"
            f"🎯 {activity}\n\n"
            f"Результат:",
            reply_markup=normal_result_keyboard(),
        )

    # Турнир

    else:

        activity = TOURNAMENT_ACTIVITIES[index]

        state["activity"] = activity
        state["kind"] = "tournament"

        await callback.message.edit_text(
            f"👥 {state['team']}\n\n"
            f"🎯 {activity}\n\n"
            f"Выберите место:",
            reply_markup=tournament_result_keyboard(),
        )

    await callback.answer()


# ============================================================
# ПОБЕДА В ОБЫЧНОМ МАТЧЕ
# ============================================================

@dp.callback_query(
    F.data == "normal_win"
)
async def normal_win(
    callback: CallbackQuery,
):

    state = user_state.get(
        callback.from_user.id
    )

    if not state:

        await callback.answer(
            "Сессия устарела. Начните заново.",
            show_alert=True,
        )

        return

    team = state["team"]
    activity = state["activity"]

    new_score = add_points(
        team,
        NORMAL_WIN_POINTS,
    )

    await callback.message.edit_text(
        "✅ Результат записан!\n\n"
        f"👥 {team}\n"
        f"🎯 {activity}\n"
        f"🏆 Победа\n\n"
        f"➕ {NORMAL_WIN_POINTS} очков\n\n"
        f"💰 Всего команды: {new_score}",
        reply_markup=main_keyboard(),
    )

    user_state.pop(
        callback.from_user.id,
        None,
    )

    await callback.answer(
        "Очки начислены!"
    )


# ============================================================
# МЕСТО В ТУРНИРЕ
# ============================================================

@dp.callback_query(
    F.data.startswith("place:")
)
async def tournament_place(
    callback: CallbackQuery,
):

    state = user_state.get(
        callback.from_user.id
    )

    if not state:

        await callback.answer(
            "Сессия устарела. Начните заново.",
            show_alert=True,
        )

        return

    place = int(
        callback.data.split(":")[1]
    )

    team = state["team"]
    activity = state["activity"]

    if activity == "🔥 Гранд-финал":

        points = FINAL_POINTS[place]

    else:

        points = TOURNAMENT_POINTS[place]

    new_score = add_points(
        team,
        points,
    )

    medals = {
        1: "🥇",
        2: "🥈",
        3: "🥉",
    }

    await callback.message.edit_text(
        "✅ Результат записан!\n\n"
        f"👥 {team}\n"
        f"🎯 {activity}\n"
        f"{medals[place]} {place} место\n\n"
        f"➕ {points} очков\n\n"
        f"💰 Всего команды: {new_score}",
        reply_markup=main_keyboard(),
    )

    user_state.pop(
        callback.from_user.id,
        None,
    )

    await callback.answer(
        "Очки начислены!"
    )


# ============================================================
# ТАБЛО
# ============================================================

@dp.callback_query(
    F.data == "scoreboard"
)
async def scoreboard(
    callback: CallbackQuery,
):

    teams = get_scores()

    await callback.message.edit_text(
        build_scoreboard(teams),
        reply_markup=main_keyboard(),
    )

    await callback.answer()


# ============================================================
# ОТМЕНА
# ============================================================

@dp.callback_query(
    F.data == "cancel"
)
async def cancel(
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

    await callback.answer(
        "Отменено"
    )


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

    asyncio.run(
        main()
    )
