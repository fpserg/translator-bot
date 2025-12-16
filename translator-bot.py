from googletrans import Translator
from telebot.async_telebot import AsyncTeleBot
import asyncio
import html
import re

# Initialize bot with your token (replace with your actual token)
bot = AsyncTeleBot("7974706119:AAHEl00bFRWD8qR5il7NMcFTx3huLbS1qN0", parse_mode="HTML")

# Initialize translator
translator = Translator()

# Define target language for translation
# Change 'en' to any other language code (e.g., 'es', 'fr', 'de')
TARGET_LANGUAGE = 'en'

def extract_message_text(message):
    """Extracts text from regular or forwarded messages."""
    if message.forward_origin:
        # Message is forwarded, handle based on origin type
        origin = message.forward_origin
        
        if hasattr(origin, 'sender_user'):
            # Forwarded from a user
            sender = origin.sender_user
            sender_name = f"{sender.first_name or ''} {sender.last_name or ''}".strip()
            sender_info = f"👤 {sender_name}"
            
        elif hasattr(origin, 'sender_chat'):
            # Forwarded from a chat/channel
            sender_chat = origin.sender_chat
            sender_info = f"💬 {sender_chat.title}"
            
        elif hasattr(origin, 'hidden_user'):
            # Forwarded from a user who hides their account
            hidden_user = origin.hidden_user
            sender_info = "👤 Anonymous"
        else:
            sender_info = "ℹ️ Forwarded"
        
        # Extract the text content
        text_content = message.text or message.caption or ""
        return text_content, sender_info
    
    # Regular (non-forwarded) message
    return message.text or message.caption or "", None

def translate_text(text, dest_lang):
    """Translates text to target language."""
    if not text or not text.strip():
        return None
    
    try:
        # 1. Extract ALL URLs from the original text and store them
        # This regex finds common URL patterns
        url_pattern = r'(https?://[^\s]+|www\.[^\s]+)'
        original_urls = re.findall(url_pattern, text)
        # Create a placeholder for each URL to hide it from translator
        placeholder = " @@URL_PLACEHOLDER@@ "
        for i, url in enumerate(original_urls):
            text = text.replace(url, f"{placeholder}{i}")

        # 2. Detect source language and translate
        detected = translator.detect(text)
        source_lang = detected.lang
        translated = translator.translate(text, src=source_lang, dest=dest_lang)
        
        # 3. Put the original URLs back into the translated text
        translated_text = translated.text
        for i, url in enumerate(original_urls):
            # Use the placeholder to find where to reinsert the URL
            search_pattern = re.escape(f"{placeholder}{i}")
            # Replace placeholder with the original, properly formatted URL
            translated_text = re.sub(search_pattern, url, translated_text)

          # 4. Escape only the non-URL parts for HTML safety
        # Simple approach: escape everything, then unescape the URLs
        safe_text = html.escape(translated_text)
        for url in original_urls:
            # Re-insert the raw URL (which should not be HTML-escaped)
            escaped_url = html.escape(url)
            safe_text = safe_text.replace(escaped_url, url)
        return {
            'original': text,
            'translated': safe_text,  # Now with working links
            'src_lang': source_lang,
            'dest_lang': dest_lang,
            'urls_found': original_urls  # Optional: for debugging
        }
    except Exception as e:
        print(f"Translation error: {e}")
        return None

@bot.message_handler(commands=['start', 'help'])
async def send_welcome(message):
    """Handles /start and /help commands."""
    welcome_text = (
        "🌟 <b>Translation Bot</b> 🌟\n\n"
        "I translate messages using Google Translate!\n\n"
        "<b>How to use:</b>\n"
        "• Send me any text message\n"
        "• Forward a message to me\n"
        "• I'll translate it to English (default)\n\n"
        "<b>Commands:</b>\n"
        "/start - Show this message\n"
        "/help - Show help\n"
        "/lang <code> - Change target language (e.g., /lang es)"
    )
    await bot.reply_to(message, welcome_text)

@bot.message_handler(commands=['lang'])
async def change_language(message):
    """Allows users to change target language."""
    global TARGET_LANGUAGE
    try:
        lang_code = message.text.split()[1].lower()
        # Simple validation - you could add more comprehensive checks
        TARGET_LANGUAGE = lang_code
        await bot.reply_to(message, f"✅ Target language changed to: {lang_code}")
    except (IndexError, AttributeError):
        await bot.reply_to(message, "⚠️ Please specify a language code. Example: <code>/lang es</code>")

@bot.message_handler(content_types=['text'])
async def handle_text(message):
    """Handles text messages and forwarded messages."""
    # Extract text and sender info
    text_content, sender_info = extract_message_text(message)
    
    if not text_content.strip():
        await bot.reply_to(message, "Please send or forward a message with text content.")
        return
    
      # Perform translation (with URL preservation)
    translation_result = translate_text(text_content, TARGET_LANGUAGE)
    if not translation_result:
        await bot.reply_to(message, "Sorry, I couldn't translate that message.")
        return
        
    # Prepare formatted response
    response_parts = []
    if sender_info:
        response_parts.append(f"<i>{sender_info}</i>\n")
    response_parts.append(f"<b>Translated ({translation_result['dest_lang']}):</b>")
    response_parts.append(f"{translation_result['translated']}\n")  # This now contains clickable links
    
    # Optional: Show original text (can be disabled)
    # response_parts.append(f"<i>Original ({translation_result['src_lang']}):</i>")
    # response_parts.append(f"<code>{html.escape(translation_result['original'][:200])}</code>")
    
    # Send the formatted response
    await bot.reply_to(message, "\n".join(response_parts))

@bot.message_handler(content_types=['photo', 'document', 'audio', 'voice'])
async def handle_media(message):
    """Handles media messages with captions."""
    caption_content, sender_info = extract_message_text(message)
    
    if not caption_content.strip():
        # No caption to translate
        await bot.reply_to(message, "This media doesn't have text to translate.")
        return
    
    # Translate the caption
    translation_result = translate_text(caption_content, TARGET_LANGUAGE)
    
    if not translation_result:
        return
    
    # Prepare response
    response = f"<b>Caption translation:</b>\n{translation_result['translated']}"
    
    if sender_info:
        response = f"<i>{sender_info}</i>\n{response}"
    
    await bot.reply_to(message, response)

# Start the bot
async def main():
    await bot.infinity_polling()

if __name__ == "__main__":
    asyncio.run(main())
