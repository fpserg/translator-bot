import os
import traceback
from aiogram import Bot, Dispatcher
import aiogram
import asyncio
import logging as lg
from aiogram.client.default import DefaultBotProperties
from aiogram.filters import Command
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Message
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.filters.callback_data import CallbackData

from Helpers.Translator import TranslateText
from Helpers.YandexIAM import CreateIAMToken
from Helpers.Detector import detect_language, list_languages
from Helpers.user_settings import SettingsStore, PendingActions

lg.basicConfig(level=lg.INFO, format="%(asctime)s - %(levelname)s - %(name)s - %(message)s")

storage = MemoryStorage()
bot = Bot(os.getenv("BOT_TOKEN"), default=DefaultBotProperties(parse_mode='HTML'))
dp: Dispatcher = Dispatcher(storage=storage)

settings_store = SettingsStore(os.getenv("SETTINGS_PATH", "user_settings.json"))

pending = PendingActions()

_supported_langs: set[str] | None = None

YANDEX_FOLDER_ID = os.getenv("YANDEX_FOLDER_ID")


class SetLangCb(CallbackData, prefix="setlang"):
    lang: str


def extract_message_text(message: Message) -> str:
    """Return message text/caption as HTML string (empty if none)."""
    return message.html_text or message.html_caption or ""


async def _get_supported_langs() -> set[str]:
    global _supported_langs
    if _supported_langs is not None:
        return _supported_langs

    token = CreateIAMToken()
    langs = await list_languages(token=token, folder_id=YANDEX_FOLDER_ID)
    if not langs:
        langs = {"ru", "en"}
    _supported_langs = langs
    return langs


async def reply_with_same_media_and_translation(message: Message, translation_html: str):
    caption = translation_html

    # Фото
    if message.photo:
        await message.answer_photo(message.photo[-1].file_id, caption=caption)
        return

    # Видео
    if message.video:
        await message.answer_video(message.video.file_id, caption=caption)
        return

    # Документ
    if message.document:
        await message.answer_document(message.document.file_id, caption=caption)
        return

    # Аудио
    if message.audio:
        await message.answer_audio(message.audio.file_id, caption=caption)
        return

    # Голос
    if message.voice:
        await message.answer_voice(message.voice.file_id, caption=caption)
        return

    # Кружок
    if message.video_note:
        await message.answer_video_note(message.video_note.file_id)
        await message.answer(caption)
        return

    # Анимация (GIF)
    if message.animation:
        await message.answer_animation(message.animation.file_id, caption=caption)
        return

    # Стикеры
    if message.sticker:
        await message.answer_sticker(message.sticker.file_id)
        await message.answer(caption)
        return

    await message.answer(caption)


@dp.message(Command("start"))
async def send_welcome(message: Message):
    welcome_text = (
        "🌟 <b>Translation Bot</b> 🌟\n\n"
        "I translate messages using Yandex Translate!\n\n"
        "<b>How to use:</b>\n"
        "• Send me any text message\n"
        "• Forward a message to me\n"
        "• I'll translate it to English (default)\n\n"
        "<b>Commands:</b>\n"
        "/start - Show this message\n"
        "/lang <code> - Change target language (e.g., /lang es) </code>"
    )
    await message.reply(welcome_text)


@dp.message(Command("detect"))
async def cmd_detect(message: Message):
    """User enters /detect, then sends/forwards next message: we detect language."""
    if not message.from_user:
        return
    pending.set_detect(message.from_user.id)
    await message.reply("Ок. Теперь отправь или перешли текст/медиа с подписью — я определю язык.")


@dp.message(Command("setlang"))
async def cmd_setlang(message: Message):
    """Set per-user target language: /setlang en"""
    if not message.from_user:
        return

    parts = (message.text or "").split(maxsplit=1)
    if len(parts) < 2:
        await message.reply("Укажи код языка. Пример: <code>/setlang en</code>")
        return

    lang = parts[1].strip().lower()
    supported = await _get_supported_langs()
    if lang not in supported:
        await message.reply(
            "Неверный код языка. Нужен ISO-код вроде <code>en</code>, <code>ru</code>.\n"
            "Подсказка: можно сначала сделать <code>/detect</code>, а потом нажать кнопку."
        )
        return

    settings_store.set_target_language(message.from_user.id, lang)
    await message.reply(f"✅ Язык перевода для тебя установлен: <b>{lang}</b>")


@dp.callback_query(SetLangCb.filter())
async def cb_setlang(callback: aiogram.types.CallbackQuery, callback_data: SetLangCb):
    if not callback.from_user:
        return

    lang = (callback_data.lang or "").lower()
    supported = await _get_supported_langs()
    if lang not in supported:
        await callback.answer("Этот язык больше не поддерживается.", show_alert=True)
        return

    settings_store.set_target_language(callback.from_user.id, lang)
    await callback.answer(f"Язык установлен: {lang}")
    # Можно обновить сообщение
    if callback.message:
        await callback.message.reply(f"✅ Язык перевода установлен: <b>{lang}</b>")


@dp.message(
    aiogram.F.text
    | aiogram.F.caption
    | aiogram.F.photo
    | aiogram.F.video
    | aiogram.F.document
    | aiogram.F.audio
    | aiogram.F.voice
    | aiogram.F.animation
    | aiogram.F.video_note
    | aiogram.F.sticker
)
async def handle_any(message: Message):
    if not message.from_user:
        return

    text_content = extract_message_text(message)

    # 1) If user issued /detect ранее — выполняем detect и выходим
    if pending.pop_detect(message.from_user.id):
        if not text_content.strip():
            await message.reply("В этом сообщении нет текста/подписи для определения языка.")
            return

        token = CreateIAMToken()
        lang = await detect_language(text=text_content, token=token, folder_id=YANDEX_FOLDER_ID)
        if not lang:
            await message.reply("Не получилось определить язык (ошибка API).")
            return

        kb = InlineKeyboardBuilder()
        kb.button(text=f"Установить язык перевода: {lang}", callback_data=SetLangCb(lang=lang).pack())
        kb.adjust(1)

        await message.reply(
            f"Похоже, в тексте преобладает язык: <b>{lang}</b>",
            reply_markup=kb.as_markup(),
        )
        return

    # 2) Обычный режим перевода
    if not text_content.strip():
        if message.photo:
            await message.answer_photo(message.photo[-1].file_id)
            return
        if message.video:
            await message.answer_video(message.video.file_id)
            return
        if message.document:
            await message.answer_document(message.document.file_id)
            return
        if message.audio:
            await message.answer_audio(message.audio.file_id)
            return
        if message.voice:
            await message.answer_voice(message.voice.file_id)
            return
        if message.animation:
            await message.answer_animation(message.animation.file_id)
            return
        if message.video_note:
            await message.answer_video_note(message.video_note.file_id)
            return
        if message.sticker:
            await message.answer_sticker(message.sticker.file_id)
            return

        await message.reply("Нет текста/подписи для перевода.")
        return

    user_target = settings_store.get(message.from_user.id).target_language

    token = CreateIAMToken()
    translation_html = await TranslateText("ru", user_target, text_content, token)
    if not translation_html:
        await message.reply("Не получилось перевести.")
        return

    await reply_with_same_media_and_translation(message, translation_html)


async def main():
    try:
        await dp.start_polling(bot)
    except Exception:
        lg.error("An error occurred:\n%s", traceback.format_exc())


if __name__ == "__main__":
    asyncio.run(main())
