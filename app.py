import os
import logging

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder


# =========================
# НАСТРОЙКИ
# =========================

BOT_TOKEN = os.getenv("BOT_TOKEN")

# Telegram ID пользователей, которым разрешено пользоваться ботом.
# Например: ADMIN_IDS=123456789,987654321
ADMIN_IDS = {
    int(user_id.strip())
    for user_id in os.getenv("ADMIN_IDS", "").split(",")
    if user_id.strip()
}


# =========================
# КОМАНДЫ
# =========================

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


# Обычные матчи
NORMAL_ACTIVITIES = [
    "🏓 Пинг-понг",
    "🏐 Волейбол",
    "⚽ Футбол",
    "🏀 Стритбол",
    "🏸 Бадминтон",
    "🎲 Настольные игры",
]


# Большие турниры
TOURNAMENT_ACTIVITIES = [
    "🏆 Большой турнир по пинг-понгу",
    "🏆 Большой турнир по волейболу",
    "🎭 Сценки",
    "🔥 Гранд-финал",
]


# Очки
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


# =========================
# ВРЕМЕННЫЕ ДАННЫЕ
# =========================

# Пока храним всё в памяти.
# На следующем этапе перенесём это в PostgreSQL.
scores = {
    team: 0
    for team in TEAMS
}


# =========================
# BOT
# =========================

logging.basicConfig(level=logging.INFO)

if not BOT_TOKEN:
    raise RuntimeError("Не задан BOT_TOKEN")

bot = Bot(BOT_TOKEN)
dp = Dispatcher()


# =========================
# ПРОВЕРКА ДОСТУПА
# =========================

def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


# =========================
# КЛАВИАТУРЫ
# =========================

def main_keyboard():
    builder = InlineKeyboardBuilder()

    builder.button(
        text="➕ Записать результат",
        callback_data="add_result"
    )

    builder.button(
        text="🏆 Табло",
        callback_data="scoreboard"
    )

    builder.adjust(1)

    return builder.as_markup()


def teams_keyboard():
    builder = InlineKeyboardBuilder()

    for index, team in enumerate(TEAMS):
        builder.button(
            text=team,
            callback_data=f"team:{index}"
        )

    builder.adjust(2)

    return builder.as_markup()


def activities_keyboard():
    builder = InlineKeyboardBuilder()

    for index, activity in enumerate(NORMAL_ACTIVITIES):
        builder.button(
            text=activity,
            callback_data=f"normal:{index}"
        )

    for index, activity in enumerate(TOURNAMENT_ACTIVITIES):
        builder.button(
            text=activity,
            callback_data=f"tournament:{index}"
        )

    builder.adjust(1)

    return builder.as_markup()


def normal_result_keyboard():
    builder = InlineKeyboardBuilder()

    builder.button(
        text="🏆 ПОБЕДА +100",
        callback_data="normal_win"
    )

    builder.button(
        text="❌ Отмена",
        callback_data="cancel"
    )

    builder.adjust(1)

    return builder.as_markup()


def tournament_result_keyboard():
    builder = InlineKeyboardBuilder()

    builder.button(
        text="🥇 1 место",
        callback_data="place:1"
    )

    builder.button(
        text="🥈 2 место",
        callback_data="place:2"
    )

    builder.button(
        text="🥉 3 место",
        callback_data="place:3"
    )

    builder.button(
        text="❌ Отмена",
        callback_data="cancel"
    )

    builder.adjust(1)

    return builder.as_markup()


# =========================
# ТАБЛО
# =========================

def get_scoreboard_text():
    sorted_scores = sorted(
        scores.items(),
        key=lambda item: item[1],
        reverse=True
    )

    lines = [
        "🔥 CAMP WARS",
        "",
        "🏆 ОБЩИЙ РЕЙТИНГ",
        ""
    ]

    medals = {
        1: "🥇",
        2: "🥈",
        3: "🥉"
    }

    for position, (team, score) in enumerate(sorted_scores, start=1):
        prefix = medals.get(position, f"{position}.")
        lines.append(
            f"{prefix} {team} — {score}"
        )

    return "\n".join(lines)


# =========================
# СОСТОЯНИЕ ПОЛЬЗОВАТЕЛЕЙ
# =========================

user_state = {}


# =========================
# START
# =========================

@dp.message(Command("start"))
async def start(message: Message):

    if not is_admin(message.from_user.id):
        await message.answer(
            "⛔ Доступ закрыт."
        )
        return

    await message.answer(
        "🔥 CAMP WARS\n\n"
        "Панель управления результатами:",
        reply_markup=main_keyboard()
    )


# =========================
# ЗАПИСАТЬ РЕЗУЛЬТАТ
# =========================

@dp.callback_query(F.data == "add_result")
async def add_result(callback: CallbackQuery):

    if not is_admin(callback.from_user.id):
        await callback.answer(
            "⛔ Доступ закрыт",
            show_alert=True
        )
        return

    await callback.message.edit_text(
        "👥 Выберите команду:",
        reply_markup=teams_keyboard()
    )

    await callback.answer()


# =========================
# ВЫБОР КОМАНДЫ
# =========================

@dp.callback_query(F.data.startswith("team:"))
async def select_team(callback: CallbackQuery):

    if not is_admin(callback.from_user.id):
        await callback.answer(
            "⛔ Доступ закрыт",
            show_alert=True
        )
        return

    team_index = int(
        callback.data.split(":")[1]
    )

    team = TEAMS[team_index]

    user_state[callback.from_user.id] = {
        "team": team
    }

    await callback.message.edit_text(
        f"👥 Команда:\n\n"
        f"{team}\n\n"
        f"🎯 Теперь выберите активность:",
        reply_markup=activities_keyboard()
    )

    await callback.answer()


# =========================
# ВЫБОР АКТИВНОСТИ
# =========================

@dp.callback_query(
    F.data.startswith("normal:")
    | F.data.startswith("tournament:")
)
async def select_activity(callback: CallbackQuery):

    if not is_admin(callback.from_user.id):
        await callback.answer(
            "⛔ Доступ закрыт",
            show_alert=True
        )
        return

    kind, index = callback.data.split(":")
    index = int(index)

    state = user_state.get(callback.from_user.id)

    if not state:
        await callback.answer(
            "Начните заново",
            show_alert=True
        )
        return

    if kind == "normal":

        activity = NORMAL_ACTIVITIES[index]

        state["activity"] = activity
        state["kind"] = "normal"

        await callback.message.edit_text(
            f"{state['team']}\n"
            f"{activity}\n\n"
            f"Результат:",
            reply_markup=normal_result_keyboard()
        )

    else:

        activity = TOURNAMENT_ACTIVITIES[index]

        state["activity"] = activity
        state["kind"] = "tournament"

        await callback.message.edit_text(
            f"{state['team']}\n"
            f"{activity}\n\n"
            f"Выберите место:",
            reply_markup=tournament_result_keyboard()
        )

    await callback.answer()


# =========================
# ОБЫЧНАЯ ПОБЕДА
# =========================

@dp.callback_query(F.data == "normal_win")
async def normal_win(callback: CallbackQuery):

    if not is_admin(callback.from_user.id):
        await callback.answer(
            "⛔ Доступ закрыт",
            show_alert=True
        )
        return

    state = user_state.get(callback.from_user.id)

    if not state:
        await callback.answer(
            "Начните заново",
            show_alert=True
        )
        return

    team = state["team"]
    activity = state["activity"]

    scores[team] += NORMAL_WIN_POINTS

    new_score = scores[team]

    await callback.message.edit_text(
        f"✅ Результат записан!\n\n"
        f"{team}\n"
        f"{activity}\n"
        f"🏆 Победа\n\n"
        f"+{NORMAL_WIN_POINTS} очков\n\n"
        f"💰 Всего команды: {new_score}",
        reply_markup=main_keyboard()
    )

    user_state.pop(callback.from_user.id, None)

    await callback.answer("Очки начислены!")


# =========================
# МЕСТО В ТУРНИРЕ
# =========================

@dp.callback_query(F.data.startswith("place:"))
async def tournament_place(callback: CallbackQuery):

    if not is_admin(callback.from_user.id):
        await callback.answer(
            "⛔ Доступ закрыт",
            show_alert=True
        )
        return

    state = user_state.get(callback.from_user.id)

    if not state:
        await callback.answer(
            "Начните заново",
            show_alert=True
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

    scores[team] += points

    new_score = scores[team]

    medals = {
        1: "🥇",
        2: "🥈",
        3: "🥉"
    }

    await callback.message.edit_text(
        f"✅ Результат записан!\n\n"
        f"{team}\n"
        f"{activity}\n"
        f"{medals[place]} {place} место\n\n"
        f"+{points} очков\n\n"
        f"💰 Всего команды: {new_score}",
        reply_markup=main_keyboard()
    )

    user_state.pop(callback.from_user.id, None)

    await callback.answer("Очки начислены!")


# =========================
# ТАБЛО
# =========================

@dp.callback_query(F.data == "scoreboard")
async def scoreboard(callback: CallbackQuery):

    if not is_admin(callback.from_user.id):
        await callback.answer(
            "⛔ Доступ закрыт",
            show_alert=True
        )
        return

    await callback.message.edit_text(
        get_scoreboard_text(),
        reply_markup=main_keyboard()
    )

    await callback.answer()


# =========================
# ОТМЕНА
# =========================

@dp.callback_query(F.data == "cancel")
async def cancel(callback: CallbackQuery):

    user_state.pop(
        callback.from_user.id,
        None
    )

    await callback.message.edit_text(
        "🔥 CAMP WARS\n\n"
        "Панель управления результатами:",
        reply_markup=main_keyboard()
    )

    await callback.answer()


# =========================
# ЗАПУСК
# =========================

async def main():

    print("🔥 CAMP WARS BOT STARTED")

    await dp.start_polling(bot)


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
