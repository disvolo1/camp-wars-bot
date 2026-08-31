import asyncio
import logging
import os
import random

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from aiogram.exceptions import TelegramBadRequest

from database import (
    init_database,
    get_teams,
    get_team,
    rename_team,
    add_points,
    get_history,
    save_user,
    get_user,
    set_user_team,
    create_mission,
    get_missions,
    get_available_missions,
    issue_mission,
    get_active_mission_for_team,
)


# ============================================================
# НАСТРОЙКИ
# ============================================================

BOT_TOKEN = os.getenv("BOT_TOKEN")

if not BOT_TOKEN:
    raise RuntimeError("Не задан BOT_TOKEN")


ADMIN_IDS = {
    128835770,
    994383,
}


# ============================================================
# ЛОГИ
# ============================================================

logging.basicConfig(
    level=logging.INFO
)

logger = logging.getLogger(__name__)


# ============================================================
# BOT
# ============================================================

bot = Bot(
    token=BOT_TOKEN
)

dp = Dispatcher()


# ============================================================
# ПРОВЕРКА АДМИНА
# ============================================================

def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


# ============================================================
# КЛАВИАТУРА АДМИНА
# ============================================================

def admin_keyboard():

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🏆 Табло",
                    callback_data="scoreboard",
                )
            ],
            [
                InlineKeyboardButton(
                    text="🏅 За активность",
                    callback_data="activity",
                ),
                InlineKeyboardButton(
                    text="➕ Добавить баллы",
                    callback_data="add_points",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="📜 История",
                    callback_data="history",
                )
            ],
            [
                InlineKeyboardButton(
                    text="✏️ Команды",
                    callback_data="teams",
                )
            ],
            [
                InlineKeyboardButton(
                    text="🕵️ Выдать задание",
                    callback_data="issue_mission",
                )
            ],
        ]
    )


# ============================================================
# КЛАВИАТУРА КАПИТАНА
# ============================================================

def captain_keyboard():

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🏆 Табло",
                    callback_data="scoreboard",
                )
            ],
            [
                InlineKeyboardButton(
                    text="🕵️ Моё задание",
                    callback_data="my_mission",
                )
            ],
        ]
    )


# ============================================================
# START
# ============================================================

@dp.message(Command("start"))
async def start_handler(message: Message):

    save_user(
        user_id=message.from_user.id,
        username=message.from_user.username,
        first_name=message.from_user.first_name,
    )

    if is_admin(message.from_user.id):

        await message.answer(
            "👑 <b>Панель администратора CAMP WARS</b>\n\n"
            "Ты вошёл как администратор.",
            reply_markup=admin_keyboard(),
            parse_mode="HTML",
        )

        return

    user = get_user(
        message.from_user.id
    )

    if not user:

        await message.answer(
            "Ошибка регистрации. Попробуйте ещё раз."
        )

        return

    if not user["team_id"]:

        await message.answer(
            "🧢 <b>CAMP WARS</b>\n\n"
            "Выбери свою команду:",
            reply_markup=team_selection_keyboard(),
            parse_mode="HTML",
        )

        return

    team = get_team(
        user["team_id"]
    )

    await message.answer(
        f"🧢 <b>Ты капитан команды «{team['name']}»</b>\n\n"
        "Здесь будут появляться ваши секретные задания.",
        reply_markup=captain_keyboard(),
        parse_mode="HTML",
    )


# ============================================================
# ВЫБОР КОМАНДЫ
# ============================================================

def team_selection_keyboard():

    teams = get_teams()

    rows = []

    for team in teams:

        rows.append(
            [
                InlineKeyboardButton(
                    text=team["name"],
                    callback_data=f"select_team:{team['id']}",
                )
            ]
        )

    return InlineKeyboardMarkup(
        inline_keyboard=rows
    )


@dp.callback_query(
    F.data.startswith("select_team:")
)
async def select_team(
    callback: CallbackQuery
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

    set_user_team(
        callback.from_user.id,
        team_id,
    )

    await callback.message.edit_text(
        f"🧢 <b>Команда выбрана:</b>\n"
        f"«{team['name']}»\n\n"
        "Теперь бот сможет присылать тебе секретные задания.",
        reply_markup=captain_keyboard(),
        parse_mode="HTML",
    )

    await callback.answer()


# ============================================================
# ТАБЛО
# ============================================================

def scoreboard_text():

    teams = get_teams()

    teams = sorted(
        teams,
        key=lambda x: x["score"],
        reverse=True,
    )

    text = "🏆 <b>CAMP WARS — ТАБЛО</b>\n\n"

    medals = [
        "🥇",
        "🥈",
        "🥉",
    ]

    for index, team in enumerate(teams):

        if index < 3:
            prefix = medals[index]
        else:
            prefix = f"{index + 1}."

        text += (
            f"{prefix} "
            f"<b>{team['name']}</b> — "
            f"{team['score']} очков\n"
        )

    return text


@dp.callback_query(
    F.data == "scoreboard"
)
async def scoreboard(
    callback: CallbackQuery
):

    text = scoreboard_text()

    try:

        await callback.message.edit_text(
            text,
            reply_markup=(
                admin_keyboard()
                if is_admin(
                    callback.from_user.id
                )
                else captain_keyboard()
            ),
            parse_mode="HTML",
        )

    except TelegramBadRequest as e:

        if "message is not modified" not in str(e):

            raise

    await callback.answer()


# ============================================================
# ДОБАВЛЕНИЕ БАЛЛОВ
# ============================================================

@dp.callback_query(
    F.data == "add_points"
)
async def add_points_start(
    callback: CallbackQuery
):

    if not is_admin(
        callback.from_user.id
    ):

        await callback.answer(
            "⛔ Нет доступа",
            show_alert=True,
        )

        return

    await callback.message.edit_text(
        "➕ <b>Добавить баллы</b>\n\n"
        "Выбери команду:",
        reply_markup=points_team_keyboard(),
        parse_mode="HTML",
    )

    await callback.answer()


def points_team_keyboard():

    teams = get_teams()

    rows = []

    for team in teams:

        rows.append(
            [
                InlineKeyboardButton(
                    text=team["name"],
                    callback_data=f"points_team:{team['id']}",
                )
            ]
        )

    rows.append(
        [
            InlineKeyboardButton(
                text="⬅️ Назад",
                callback_data="admin_home",
            )
        ]
    )

    return InlineKeyboardMarkup(
        inline_keyboard=rows
    )


@dp.callback_query(
    F.data.startswith("points_team:")
)
async def points_team(
    callback: CallbackQuery
):

    if not is_admin(
        callback.from_user.id
    ):

        await callback.answer(
            "⛔ Нет доступа",
            show_alert=True,
        )

        return

    team_id = int(
        callback.data.split(":")[1]
    )

    team = get_team(team_id)

    await callback.message.edit_text(
        f"➕ <b>{team['name']}</b>\n\n"
        "Теперь отправь мне количество баллов числом.\n\n"
        "Например:\n"
        "<code>150</code>\n"
        "<code>-50</code>",
        parse_mode="HTML",
    )

    # Сохраняем временный выбор команды
    await dp.storage.set_data(
        bot=bot,
        chat=callback.from_user.id,
        data={
            "points_team_id": team_id
        }
    )

    await callback.answer()


# ============================================================
# ТЕКСТ — ВВОД БАЛЛОВ
# ============================================================

@dp.message(
    F.text.regexp(r"^-?\d+$")
)
async def points_input(
    message: Message
):

    if not is_admin(
        message.from_user.id
    ):

        return

    try:

        data = await dp.storage.get_data(
            bot=bot,
            chat=message.from_user.id,
        )

    except Exception:

        data = {}

    team_id = data.get(
        "points_team_id"
    )

    if not team_id:

        return

    points = int(
        message.text
    )

    team = get_team(
        team_id
    )

    if not team:

        await message.answer(
            "Команда не найдена."
        )

        return

    new_score = add_points(
        team_id=team_id,
        points=points,
        user_id=message.from_user.id,
        username=message.from_user.username,
        first_name=message.from_user.first_name,
        activity="Ручное начисление",
    )

    await dp.storage.clear(
        bot=bot,
        chat=message.from_user.id,
    )

    sign = "+" if points >= 0 else ""

    await message.answer(
        f"✅ <b>Баллы добавлены</b>\n\n"
        f"Команда: <b>{team['name']}</b>\n"
        f"Изменение: <b>{sign}{points}</b>\n"
        f"Новый счёт: <b>{new_score}</b>",
        reply_markup=admin_keyboard(),
        parse_mode="HTML",
    )


# ============================================================
# ИСТОРИЯ
# ============================================================

@dp.callback_query(
    F.data == "history"
)
async def history_handler(
    callback: CallbackQuery
):

    if not is_admin(
        callback.from_user.id
    ):

        await callback.answer(
            "⛔ Нет доступа",
            show_alert=True,
        )

        return

    history = get_history(
        limit=30
    )

    if not history:

        text = "📜 <b>История пока пустая.</b>"

    else:

        text = "📜 <b>Последние изменения</b>\n\n"

        for row in history:

            sign = (
                "+"
                if row["points"] >= 0
                else ""
            )

            username = (
                f"@{row['username']}"
                if row["username"]
                else row["first_name"]
            )

            activity = (
                f" — {row['activity']}"
                if row["activity"]
                else ""
            )

            text += (
                f"🕐 {row['created_at']}\n"
                f"🏆 {row['team_name']}: "
                f"<b>{sign}{row['points']}</b>\n"
                f"👤 {username}"
                f"{activity}\n\n"
            )

    await callback.message.edit_text(
        text,
        reply_markup=admin_keyboard(),
        parse_mode="HTML",
    )

    await callback.answer()


# ============================================================
# КОМАНДЫ
# ============================================================

@dp.callback_query(
    F.data == "teams"
)
async def teams_handler(
    callback: CallbackQuery
):

    if not is_admin(
        callback.from_user.id
    ):

        await callback.answer(
            "⛔ Нет доступа",
            show_alert=True,
        )

        return

    teams = get_teams()

    text = "✏️ <b>Команды</b>\n\n"

    for team in teams:

        text += (
            f"{team['id']}. "
            f"{team['name']} — "
            f"{team['score']} очков\n"
        )

    await callback.message.edit_text(
        text,
        reply_markup=rename_teams_keyboard(),
        parse_mode="HTML",
    )

    await callback.answer()


def rename_teams_keyboard():

    teams = get_teams()

    rows = []

    for team in teams:

        rows.append(
            [
                InlineKeyboardButton(
                    text=f"✏️ {team['name']}",
                    callback_data=f"rename:{team['id']}",
                )
            ]
        )

    rows.append(
        [
            InlineKeyboardButton(
                text="⬅️ Назад",
                callback_data="admin_home",
            )
        ]
    )

    return InlineKeyboardMarkup(
        inline_keyboard=rows
    )


@dp.callback_query(
    F.data.startswith("rename:")
)
async def rename_start(
    callback: CallbackQuery
):

    if not is_admin(
        callback.from_user.id
    ):

        await callback.answer(
            "⛔ Нет доступа",
            show_alert=True,
        )

        return

    team_id = int(
        callback.data.split(":")[1]
    )

    team = get_team(team_id)

    await dp.storage.set_data(
        bot=bot,
        chat=callback.from_user.id,
        data={
            "rename_team_id": team_id
        }
    )

    await callback.message.edit_text(
        f"✏️ Команда: <b>{team['name']}</b>\n\n"
        "Отправь новое название:",
        parse_mode="HTML",
    )

    await callback.answer()


# ============================================================
# ОБРАБОТКА НОВОГО НАЗВАНИЯ
# ============================================================

@dp.message()
async def text_handler(
    message: Message
):

    if not is_admin(
        message.from_user.id
    ):

        return

    data = await dp.storage.get_data(
        bot=bot,
        chat=message.from_user.id,
    )

    team_id = data.get(
        "rename_team_id"
    )

    if not team_id:

        return

    new_name = (
        message.text
        .strip()
    )

    if not new_name:

        await message.answer(
            "Название не может быть пустым."
        )

        return

    rename_team(
        team_id,
        new_name,
    )

    await dp.storage.clear(
        bot=bot,
        chat=message.from_user.id,
    )

    await message.answer(
        f"✅ Команда переименована:\n\n"
        f"<b>{new_name}</b>",
        reply_markup=admin_keyboard(),
        parse_mode="HTML",
    )


# ============================================================
# ВЫДАТЬ ЗАДАНИЕ
# ============================================================

@dp.callback_query(
    F.data == "issue_mission"
)
async def issue_mission_handler(
    callback: CallbackQuery
):

    if not is_admin(
        callback.from_user.id
    ):

        await callback.answer(
            "⛔ Нет доступа",
            show_alert=True,
        )

        return

    teams = get_teams()

    available_for_all = True

    for team in teams:

        available = get_available_missions(
            team["id"]
        )

        if not available:

            available_for_all = False
            break

    if not available_for_all:

        await callback.message.answer(
            "⚠️ Для одной или нескольких команд "
            "закончились уникальные задания."
        )

        await callback.answer()

        return

    sent = 0

    failed = 0

    for team in teams:

        available = get_available_missions(
            team["id"]
        )

        if not available:

            continue

        mission = random.choice(
            available
        )

        # Ищем капитана этой команды
        # среди зарегистрированных пользователей.

        from database import SessionLocal, User

        with SessionLocal() as session:

            captain = (
                session.query(User)
                .filter(
                    User.team_id
                    == team["id"]
                )
                .first()
            )

        if not captain:

            failed += 1
            continue

        issue_mission(
            mission_id=mission["id"],
            team_id=team["id"],
            user_id=captain.id,
        )

        text = (
            "🕵️ <b>СЕКРЕТНОЕ ЗАДАНИЕ</b>\n\n"
            f"<b>{mission['title']}</b>\n\n"
            f"{mission['description']}\n\n"
            f"🏆 Награда: <b>+{mission['points']} очков</b>\n\n"
            "📸 <b>Важно:</b> доказательство выполнения "
            "необходимо прислать в <b>чат капитанов</b>.\n\n"
            "🤫 Не рассказывайте другим командам "
            "о своём задании."
        )

        try:

            await bot.send_message(
                captain.id,
                text,
                parse_mode="HTML",
            )

            sent += 1

        except Exception as e:

            logger.exception(
                "Не удалось отправить миссию "
                "капитану %s: %s",
                captain.id,
                e,
            )

            failed += 1

    await callback.message.answer(
        f"🕵️ <b>Задания выданы</b>\n\n"
        f"📨 Отправлено: <b>{sent}</b>\n"
        f"⚠️ Не отправлено: <b>{failed}</b>",
        parse_mode="HTML",
    )

    await callback.answer()


# ============================================================
# МОЁ ЗАДАНИЕ
# ============================================================

@dp.callback_query(
    F.data == "my_mission"
)
async def my_mission_handler(
    callback: CallbackQuery
):

    if is_admin(
        callback.from_user.id
    ):

        await callback.answer(
            "Эта кнопка доступна капитанам.",
            show_alert=True,
        )

        return

    user = get_user(
        callback.from_user.id
    )

    if not user or not user["team_id"]:

        await callback.answer(
            "Сначала выбери команду.",
            show_alert=True,
        )

        return

    mission = get_active_mission_for_team(
        user["team_id"]
    )

    if not mission:

        await callback.message.answer(
            "🕵️ Сейчас у вашей команды "
            "нет активного задания."
        )

        await callback.answer()

        return

    text = (
        "🕵️ <b>ВАШЕ СЕКРЕТНОЕ ЗАДАНИЕ</b>\n\n"
        f"<b>{mission['title']}</b>\n\n"
        f"{mission['description']}\n\n"
        f"🏆 Награда: <b>+{mission['points']} очков</b>\n\n"
        "📸 <b>Доказательство выполнения "
        "пришлите в чат капитанов.</b>"
    )

    await callback.message.answer(
        text,
        parse_mode="HTML",
    )

    await callback.answer()


# ============================================================
# АДМИН — ГЛАВНОЕ МЕНЮ
# ============================================================

@dp.callback_query(
    F.data == "admin_home"
)
async def admin_home(
    callback: CallbackQuery
):

    if not is_admin(
        callback.from_user.id
    ):

        await callback.answer(
            "⛔ Нет доступа",
            show_alert=True,
        )

        return

    await callback.message.edit_text(
        "👑 <b>Панель администратора CAMP WARS</b>",
        reply_markup=admin_keyboard(),
        parse_mode="HTML",
    )

    await callback.answer()


# ============================================================
# АКТИВНОСТЬ
# ============================================================

@dp.callback_query(
    F.data == "activity"
)
async def activity_handler(
    callback: CallbackQuery
):

    if not is_admin(
        callback.from_user.id
    ):

        await callback.answer(
            "⛔ Нет доступа",
            show_alert=True,
        )

        return

    await callback.message.edit_text(
        "🏅 <b>За активность</b>\n\n"
        "Выбери команду:",
        reply_markup=activity_team_keyboard(),
        parse_mode="HTML",
    )

    await callback.answer()


def activity_team_keyboard():

    teams = get_teams()

    rows = []

    for team in teams:

        rows.append(
            [
                InlineKeyboardButton(
                    text=team["name"],
                    callback_data=f"activity_team:{team['id']}",
                )
            ]
        )

    rows.append(
        [
            InlineKeyboardButton(
                text="⬅️ Назад",
                callback_data="admin_home",
            )
        ]
    )

    return InlineKeyboardMarkup(
        inline_keyboard=rows
    )


@dp.callback_query(
    F.data.startswith("activity_team:")
)
async def activity_team(
    callback: CallbackQuery
):

    if not is_admin(
        callback.from_user.id
    ):

        await callback.answer(
            "⛔ Нет доступа",
            show_alert=True,
        )

        return

    team_id = int(
        callback.data.split(":")[1]
    )

    team = get_team(team_id)

    await dp.storage.set_data(
        bot=bot,
        chat=callback.from_user.id,
        data={
            "points_team_id": team_id,
            "activity_mode": True,
        }
    )

    await callback.message.edit_text(
        f"🏅 <b>{team['name']}</b>\n\n"
        "Отправь количество баллов:",
        parse_mode="HTML",
    )

    await callback.answer()


# ============================================================
# ЗАПУСК
# ============================================================

async def main():

    init_database()

    logger.info(
        "Bot started"
    )

    await dp.start_polling(
        bot
    )


if __name__ == "__main__":

    asyncio.run(
        main()
    )
