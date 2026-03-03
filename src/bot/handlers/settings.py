"""
src/bot/handlers/settings.py — налаштування через FSM-діалог.
"""

from __future__ import annotations

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from src.bot.keyboards import (
    CB_HELP, CB_SET_BITRATE, CB_SET_DURATION,
    CB_SET_PLAYLIST, CB_SETTINGS,
    mix_menu_kb, settings_kb,
)
from src.bot.states import MixFlow

router = Router(name="settings")

ALLOWED_BITRATES = {"128k", "192k", "256k", "320k"}


# ─────────────────────────────────────────────────────────────────────────────
# Inline — відкрити меню налаштувань
# ─────────────────────────────────────────────────────────────────────────────

@router.callback_query(F.data == CB_SETTINGS)
async def cb_settings(call: CallbackQuery, state: FSMContext) -> None:
    await call.answer()
    data = await state.get_data()
    await call.message.edit_text(
        "⚙️ <b>Налаштування</b>\n\nОбери параметр:",
        reply_markup=settings_kb(
            duration_sec=float(data.get("duration_sec", 60)),
            bitrate=str(data.get("bitrate", "192k")),
        ),
    )


# ─────────────────────────────────────────────────────────────────────────────
# Inline — запит введення від користувача (FSM)
# ─────────────────────────────────────────────────────────────────────────────

@router.callback_query(F.data == CB_SET_PLAYLIST)
async def cb_set_playlist(call: CallbackQuery, state: FSMContext) -> None:
    await call.answer()
    await state.set_state(MixFlow.waiting_for_playlist_url)
    await call.message.answer(
        "🔗 <b>Введи URL YouTube-плейлиста:</b>\n\n"
        "Приклад:\n<code>https://www.youtube.com/playlist?list=PLxxxxxxx</code>"
    )


@router.callback_query(F.data == CB_SET_DURATION)
async def cb_set_duration(call: CallbackQuery, state: FSMContext) -> None:
    await call.answer()
    await state.set_state(MixFlow.waiting_for_duration)
    await call.message.answer(
        "⏱ <b>Введи тривалість фрагменту в секундах</b> (10–600):\n\n"
        "Приклад: <code>60</code>"
    )


@router.callback_query(F.data == CB_SET_BITRATE)
async def cb_set_bitrate(call: CallbackQuery, state: FSMContext) -> None:
    await call.answer()
    await state.set_state(MixFlow.waiting_for_bitrate)
    await call.message.answer(
        "🎚 <b>Введи бітрейт mp3:</b>\n\n"
        f"Доступні: {', '.join(f'<code>{b}</code>' for b in sorted(ALLOWED_BITRATES))}"
    )


@router.callback_query(F.data == CB_HELP)
async def cb_help_inline(call: CallbackQuery) -> None:
    await call.answer()
    await call.message.answer(
        "❓ Натисни /help для повної довідки."
    )


# ─────────────────────────────────────────────────────────────────────────────
# FSM — отримання введених значень
# ─────────────────────────────────────────────────────────────────────────────

@router.message(MixFlow.waiting_for_playlist_url)
async def fsm_playlist_url(message: Message, state: FSMContext) -> None:
    url = (message.text or "").strip()
    if "youtube.com/playlist" not in url and "youtu.be" not in url:
        await message.answer(
            "⚠️ Схоже, це не YouTube-плейлист.\n"
            "Введи коректний URL:\n"
            "<code>https://www.youtube.com/playlist?list=PLxxxxxxx</code>"
        )
        return

    await state.update_data(playlist_url=url)
    await state.set_state(None)
    await state.update_data(playlist_url=url)     # зберігаємо після clear стану

    await message.answer(
        f"✅ <b>Плейлист збережено:</b>\n<code>{url}</code>\n\n"
        f"Тепер натисни ▶️ <b>Почати завантаження</b>.",
        reply_markup=mix_menu_kb(),
    )


@router.message(MixFlow.waiting_for_duration)
async def fsm_duration(message: Message, state: FSMContext) -> None:
    try:
        sec = float((message.text or "").strip())
        if not (10 <= sec <= 600):
            raise ValueError
    except ValueError:
        await message.answer("⚠️ Введи ціле число від 10 до 600.")
        return

    await state.update_data(duration_sec=sec)
    await state.set_state(None)
    await state.update_data(duration_sec=sec)

    data = await state.get_data()
    await message.answer(
        f"✅ Тривалість: <b>{int(sec)} сек</b>",
        reply_markup=settings_kb(duration_sec=sec, bitrate=str(data.get("bitrate", "192k"))),
    )


@router.message(MixFlow.waiting_for_bitrate)
async def fsm_bitrate(message: Message, state: FSMContext) -> None:
    bitrate = (message.text or "").strip().lower()
    if bitrate not in ALLOWED_BITRATES:
        await message.answer(
            f"⚠️ Допустимі значення: {', '.join(sorted(ALLOWED_BITRATES))}"
        )
        return

    await state.update_data(bitrate=bitrate)
    await state.set_state(None)
    await state.update_data(bitrate=bitrate)

    data = await state.get_data()
    await message.answer(
        f"✅ Бітрейт: <b>{bitrate}</b>",
        reply_markup=settings_kb(
            duration_sec=float(data.get("duration_sec", 60)),
            bitrate=bitrate,
        ),
    )

