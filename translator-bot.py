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
from Helpers.Translator import TranslateText
from Helpers.YandexIAM import CreateIAMToken

lg.basicConfig(level=lg.INFO, format="%(asctime)s - %(levelname)s - %(name)s - %(message)s")

storage = MemoryStorage()
bot = Bot(os.getenv("BOT_TOKEN"), default=DefaultBotProperties(parse_mode='HTML'))
dp: Dispatcher = Dispatcher(storage=storage)

def extract_message_text(message):
    if message.forward_origin:
        origin = message.forward_origin
        
        # if hasattr(origin, 'sender_user'):
        #     # Forwarded from a user
        #     sender = origin.sender_user
        #     # sender_name = f"{sender.first_name or ''} {sender.last_name or ''}".strip()
        #     # sender_info = f"👤 {sender_name}"
        #
        # elif hasattr(origin, 'sender_chat'):
        #     # Forwarded from a chat/channel
        #     sender_chat = origin.sender_chat
        #     sender_info = f"💬 {sender_chat.title}"
        #
        # elif hasattr(origin, 'hidden_user'):
        #     # Forwarded from a user who hides their account
        #     hidden_user = origin.hidden_user
        #     sender_info = "👤 Anonymous"
        # else:
        #     sender_info = "ℹ️ Forwarded"
        
        # Extract the text content

        text_content = message.html_text or message.html_caption or ""
        return text_content
    
    return message.html_text or message.html_caption or "", None

async def reply_with_same_media_and_translation(message: Message, translation_html: str):
    """
    Если в сообщении есть медиа — отправляет то же медиа с caption=перевод.
    Если медиа нет — отправляет обычный текст.
    """
    caption = translation_html
    # if sender_info:
    #     caption = f"<i>{sender_info}</i>\n{caption}"

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

@dp.message(Command("lang"))
async def change_language(message: Message):
    global TARGET_LANGUAGE
    try:
        lang_code = message.text.split()[1].lower()
        TARGET_LANGUAGE = lang_code
        await message.reply(f"✅ Target language changed to: {lang_code}")
    except (IndexError, AttributeError):
        await message.reply("⚠️ Please specify a language code. Example: <code>/lang es</code>")

@dp.message(aiogram.F.text | aiogram.F.caption | aiogram.F.photo | aiogram.F.video | aiogram.F.document | aiogram.F.audio | aiogram.F.voice | aiogram.F.animation | aiogram.F.video_note | aiogram.F.sticker)
async def handle_any(message: Message):
    text_content = extract_message_text(message)

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

    Token = CreateIAMToken()
    translation_html = await TranslateText("ru", "en", text_content, Token)
    if not translation_html:
        await message.reply("Не получилось перевести.")
        return

    await reply_with_same_media_and_translation(message, translation_html)

async def main():
    try:
        await dp.start_polling(bot)
    except Exception as e:
        logging.error("An error occurred:")
        traceback.print_exc()
if __name__ == "__main__":
    asyncio.run(main())
