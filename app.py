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
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

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


# Telegram ID администраторов
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

storage = MemoryStorage()

bot = Bot(
    token=BOT_TOKEN
)

dp = Dispatcher(
    storage=storage
)


# ============================================================
# FSM СОСТОЯНИЯ
# ============================================================

class AdminStates(StatesGroup):

    waiting_points = State()
    waiting_activity_points = State()
    waiting_team_name = State()


# ============================================================
# ПРОВЕРКА АДМИНА
# ============================================================

def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


# ============================================================
# БЕЗОПАСНОЕ РЕДАКТИРОВАНИЕ СООБЩЕНИЯ
# ============================================================

async def safe_edit_text(
    message: Message,
    text: str,
    reply_markup=None,
):

    try:

        await message.edit_text(
            text,
            reply_markup=reply_markup,
            parse_mode="HTML",
        )

    except TelegramBadRequest as e:

        if "message is not modified" not in str(e):
            raise


# ============================================================
# АДМИНСКАЯ КЛАВИАТУРА
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
async def start_handler(message: Message, state: FSMContext):

    await state.clear()

    save_user(
        user_id=message.from_user.id,
        username=message.from_user.username,
        first_name=message.from_user.first_name,
    )

    # --------------------------------------------------------
    # АДМИН
    # --------------------------------------------------------

    if is_admin(message.from_user.id):

        await message.answer(
            "👑 <b>Панель администратора CAMP WARS</b>\n\n"
            "Ты вошёл как администратор.",
            reply_markup=admin_keyboard(),
            parse_mode="HTML",
        )

        return

    # --------------------------------------------------------
    # КАПИТАН
    # --------------------------------------------------------

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
# ВЫБОР КОМАНДЫ КАПИТАНОМ
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

    # Админу выбор команды капитана не нужен
    if is_admin(callback.from_user.id):

        await callback.answer(
            "Эта функция доступна капитанам.",
            show_alert=True,
        )

        return

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

    await safe_edit_text(
        callback.message,

        f"🧢 <b>Команда выбрана:</b>\n"
        f"«{team['name']}»\n\n"
        "Теперь бот сможет присылать тебе секретные задания.",

        captain_keyboard(),
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

    if is_admin(callback.from_user.id):

        keyboard = admin_keyboard()

    else:

        keyboard = captain_keyboard()

    await safe_edit_text(
        callback.message,
        scoreboard_text(),
        keyboard,
    )

    await callback.answer()


# ============================================================
# ============================================================
# ДОБАВИТЬ БАЛЛЫ
# ============================================================
# ============================================================

@dp.callback_query(
    F.data == "add_points"
)
async def add_points_start(
    callback: CallbackQuery,
    state: FSMContext,
):

    if not is_admin(callback.from_user.id):

        await callback.answer(
            "⛔ Нет доступа",
            show_alert=True,
        )

        return

    await state.clear()

    await safe_edit_text(
        callback.message,

        "➕ <b>Добавить баллы</b>\n\n"
        "Выбери команду:",

        points_team_keyboard(),
    )

    await callback.answer()


# ============================================================
# ВЫБОР КОМАНДЫ ДЛЯ РУЧНОГО НАЧИСЛЕНИЯ
# ============================================================

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
    callback: CallbackQuery,
    state: FSMContext,
):

    if not is_admin(callback.from_user.id):

        await callback.answer(
            "⛔ Нет доступа",
            show_alert=True,
        )

        return

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

    await state.set_state(
        AdminStates.waiting_points
    )

    await state.update_data(
        points_team_id=team_id
    )

    await safe_edit_text(
        callback.message,

        f"➕ <b>{team['name']}</b>\n\n"
        "Отправь количество баллов числом.\n\n"
        "Например:\n"
        "<code>150</code>\n"
        "<code>-50</code>",

        None,
    )

    await callback.answer()


# ============================================================
# ВВОД РУЧНЫХ БАЛЛОВ
# ============================================================

@dp.message(
    AdminStates.waiting_points,
    F.text,
)
async def points_input(
    message: Message,
    state: FSMContext,
):

    if not is_admin(message.from_user.id):

        return

    text = message.text.strip()

    if not text.lstrip("-").isdigit():

        await message.answer(
            "❌ Нужно отправить только число.\n\n"
            "Например: <code>100</code> или <code>-50</code>",
            parse_mode="HTML",
        )

        return

    points = int(text)

    data = await state.get_data()

    team_id = data.get(
        "points_team_id"
    )

    if not team_id:

        await state.clear()

        await message.answer(
            "Сессия закончилась. Нажми «Добавить баллы» ещё раз.",
            reply_markup=admin_keyboard(),
        )

        return

    team = get_team(team_id)

    if not team:

        await state.clear()

        await message.answer(
            "Команда не найдена.",
            reply_markup=admin_keyboard(),
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

    await state.clear()

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
# ============================================================
# ЗА АКТИВНОСТЬ
# ============================================================
# ============================================================

@dp.callback_query(
    F.data == "activity"
)
async def activity_handler(
    callback: CallbackQuery,
    state: FSMContext,
):

    if not is_admin(callback.from_user.id):

        await callback.answer(
            "⛔ Нет доступа",
            show_alert=True,
        )

        return

    await state.clear()

    await safe_edit_text(
        callback.message,

        "🏅 <b>За активность</b>\n\n"
        "Выбери команду:",

        activity_team_keyboard(),
    )

    await callback.answer()


# ============================================================
# КОМАНДЫ ДЛЯ АКТИВНОСТИ
# ============================================================

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
    callback: CallbackQuery,
    state: FSMContext,
):

    if not is_admin(callback.from_user.id):

        await callback.answer(
            "⛔ Нет доступа",
            show_alert=True,
        )

        return

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

    await state.set_state(
        AdminStates.waiting_activity_points
    )

    await state.update_data(
        activity_team_id=team_id
    )

    await safe_edit_text(
        callback.message,

        f"🏅 <b>{team['name']}</b>\n\n"
        "Напиши название активности.\n\n"
        "Например:\n"
        "🏓 Пинг-понг\n"
        "🏐 Волейбол\n"
        "⚽ Футбол\n"
        "🎤 Сценка",

        None,
    )

    await callback.answer()


# ============================================================
# НАЗВАНИЕ АКТИВНОСТИ
# ============================================================

@dp.message(
    AdminStates.waiting_activity_points,
    F.text,
)
async def activity_name_input(
    message: Message,
    state: FSMContext,
):

    if not is_admin(message.from_user.id):

        return

    activity = message.text.strip()

    if not activity:

        await message.answer(
            "❌ Название активности не может быть пустым."
        )

        return

    data = await state.get_data()

    team_id = data.get(
        "activity_team_id"
    )

    if not team_id:

        await state.clear()

        await message.answer(
            "Сессия закончилась. Нажми «За активность» ещё раз.",
            reply_markup=admin_keyboard(),
        )

        return

    await state.update_data(
        activity_name=activity
    )

    # Переходим в состояние ожидания количества баллов.
    await state.set_state(
        AdminStates.waiting_points
    )

    await state.update_data(
        points_team_id=team_id
    )

    team = get_team(team_id)

    await message.answer(
        f"🏅 <b>{team['name']}</b>\n\n"
        f"Активность: <b>{activity}</b>\n\n"
        "Теперь отправь количество баллов.\n\n"
        "Например:\n"
        "<code>100</code>\n"
        "<code>250</code>\n"
        "<code>-50</code>",
        parse_mode="HTML",
    )


# ============================================================
# ВВОД БАЛЛОВ ЗА АКТИВНОСТЬ
# ============================================================

@dp.message(
    AdminStates.waiting_points,
    F.text,
)
async def activity_points_input(
    message: Message,
    state: FSMContext,
):

    if not is_admin(message.from_user.id):

        return

    data = await state.get_data()

    activity_name = data.get(
        "activity_name"
    )

    # Если activity_name есть — это начисление
    # за конкретную активность.
    if not activity_name:

        # Это обычное ручное начисление.
        await points_input(
            message,
            state,
        )

        return

    text = message.text.strip()

    if not text.lstrip("-").isdigit():

        await message.answer(
            "❌ Нужно отправить только число.\n\n"
            "Например: <code>100</code>",
            parse_mode="HTML",
        )

        return

    points = int(text)

    team_id = data.get(
        "points_team_id"
    )

    team = get_team(team_id)

    if not team:

        await state.clear()

        await message.answer(
            "Команда не найдена.",
            reply_markup=admin_keyboard(),
        )

        return

    new_score = add_points(
        team_id=team_id,
        points=points,
        user_id=message.from_user.id,
        username=message.from_user.username,
        first_name=message.from_user.first_name,
        activity=activity_name,
    )

    await state.clear()

    sign = "+" if points >= 0 else ""

    await message.answer(
        f"✅ <b>Результат записан</b>\n\n"
        f"🏆 Команда: <b>{team['name']}</b>\n"
        f"🎯 Активность: <b>{activity_name}</b>\n"
        f"💰 Изменение: <b>{sign}{points}</b>\n"
        f"📊 Новый счёт: <b>{new_score}</b>",
        reply_markup=admin_keyboard(),
        parse_mode="HTML",
    )


# ============================================================
# ============================================================
# ИСТОРИЯ
# ============================================================
# ============================================================

@dp.callback_query(
    F.data == "history"
)
async def history_handler(
    callback: CallbackQuery
):

    if not is_admin(callback.from_user.id):

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

            if row["username"]:

                username = (
                    f"@{row['username']}"
                )

            elif row["first_name"]:

                username = row["first_name"]

            else:

                username = "Без имени"

            activity = (
                f"\n🎯 {row['activity']}"
                if row["activity"]
                else ""
            )

            text += (
                f"🕐 {row['created_at']}\n"
                f"🏆 <b>{row['team_name']}</b>: "
                f"<b>{sign}{row['points']}</b>\n"
                f"👤 {username}"
                f"{activity}\n\n"
            )

    await safe_edit_text(
        callback.message,
        text,
        admin_keyboard(),
    )

    await callback.answer()


# ============================================================
# ============================================================
# КОМАНДЫ
# ============================================================
# ============================================================

@dp.callback_query(
    F.data == "teams"
)
async def teams_handler(
    callback: CallbackQuery
):

    if not is_admin(callback.from_user.id):

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

    await safe_edit_text(
        callback.message,
        text,
        rename_teams_keyboard(),
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


# ============================================================
# ПЕРЕИМЕНОВАНИЕ
# ============================================================

@dp.callback_query(
    F.data.startswith("rename:")
)
async def rename_start(
    callback: CallbackQuery,
    state: FSMContext,
):

    if not is_admin(callback.from_user.id):

        await callback.answer(
            "⛔ Нет доступа",
            show_alert=True,
        )

        return

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

    await state.set_state(
        AdminStates.waiting_team_name
    )

    await state.update_data(
        rename_team_id=team_id
    )

    await safe_edit_text(
        callback.message,

        f"✏️ Команда: <b>{team['name']}</b>\n\n"
        "Отправь новое название:",

        None,
    )

    await callback.answer()


# ============================================================
# ОБРАБОТКА НОВОГО НАЗВАНИЯ
# ============================================================

@dp.message(
    AdminStates.waiting_team_name,
    F.text,
)
async def rename_input(
    message: Message,
    state: FSMContext,
):

    if not is_admin(message.from_user.id):

        return

    new_name = message.text.strip()

    if not new_name:

        await message.answer(
            "Название не может быть пустым."
        )

        return

    data = await state.get_data()

    team_id = data.get(
        "rename_team_id"
    )

    if not team_id:

        await state.clear()

        await message.answer(
            "Сессия закончилась.",
            reply_markup=admin_keyboard(),
        )

        return

    rename_team(
        team_id,
        new_name,
    )

    await state.clear()

    await message.answer(
        f"✅ <b>Команда переименована</b>\n\n"
        f"Новое название: <b>{new_name}</b>",
        reply_markup=admin_keyboard(),
        parse_mode="HTML",
    )


# ============================================================
# ============================================================
# СЕКРЕТНЫЕ ЗАДАНИЯ
# ============================================================
# ============================================================

@dp.callback_query(
    F.data == "issue_mission"
)
async def issue_mission_handler(
    callback: CallbackQuery
):

    if not is_admin(callback.from_user.id):

        await callback.answer(
            "⛔ Нет доступа",
            show_alert=True,
        )

        return

    teams = get_teams()

    sent = 0
    failed = 0

    for team in teams:

        # ----------------------------------------------------
        # Берём только задания, которые эта команда
        # ещё никогда не получала.
        # ----------------------------------------------------

        available = get_available_missions(
            team["id"]
        )

        if not available:

            logger.info(
                "Для команды %s нет доступных заданий",
                team["id"],
            )

            failed += 1

            continue

        mission = random.choice(
            available
        )

        # ----------------------------------------------------
        # Ищем капитана команды
        # ----------------------------------------------------

        from database import SessionLocal, User

        with SessionLocal() as session:

            captain = (
                session.query(User)
                .filter(
                    User.team_id == team["id"]
                )
                .first()
            )

        if not captain:

            logger.warning(
                "У команды %s нет капитана",
                team["id"],
            )

            failed += 1

            continue

        # ----------------------------------------------------
        # Записываем выдачу задания
        # ----------------------------------------------------

        issue_mission(
            mission_id=mission["id"],
            team_id=team["id"],
            user_id=captain.id,
        )

        # ----------------------------------------------------
        # Сообщение капитану
        # ----------------------------------------------------

        text = (
            "🕵️ <b>СЕКРЕТНОЕ ЗАДАНИЕ</b>\n\n"

            f"<b>{mission['title']}</b>\n\n"

            f"{mission['description']}\n\n"

            f"🏆 Награда: "
            f"<b>+{mission['points']} очков</b>\n\n"

            "📸 <b>ВАЖНО:</b>\n"
            "Доказательство выполнения необходимо "
            "прислать в <b>чат капитанов</b>.\n\n"

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
                "Не удалось отправить задание капитану %s: %s",
                captain.id,
                e,
            )

            failed += 1

    # --------------------------------------------------------
    # Результат админу
    # --------------------------------------------------------

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

    # Администратору эта функция не нужна
    if is_admin(callback.from_user.id):

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

        f"🏆 Награда: "
        f"<b>+{mission['points']} очков</b>\n\n"

        "📸 <b>Доказательство выполнения "
        "пришлите в чат капитанов.</b>\n\n"

        "🤫 Не рассказывайте другим командам "
        "о своём задании."
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
    callback: CallbackQuery,
    state: FSMContext,
):

    if not is_admin(callback.from_user.id):

        await callback.answer(
            "⛔ Нет доступа",
            show_alert=True,
        )

        return

    await state.clear()

    await safe_edit_text(
        callback.message,

        "👑 <b>Панель администратора CAMP WARS</b>",

        admin_keyboard(),
    )

    await callback.answer()


# ============================================================
# ЗАЩИТА ОТ НЕИЗВЕСТНЫХ CALLBACK
# ============================================================

@dp.callback_query()
async def unknown_callback(
    callback: CallbackQuery
):

    # Любая неизвестная callback-команда
    # просто игнорируется.

    if callback.data:

        logger.warning(
            "Unknown callback: %s from %s",
            callback.data,
            callback.from_user.id,
        )

    await callback.answer()


# ============================================================
# ЗАПУСК
# ============================================================

async def main():

    init_database()

    logger.info(
        "CAMP WARS bot started"
    )

    logger.info(
        "Admins: %s",
        ADMIN_IDS,
    )

    await dp.start_polling(
        bot
    )


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":

    try:

        asyncio.run(
            main()
        )

    except (KeyboardInterrupt, SystemExit):

        logger.info(
            "Bot stopped"
        )
