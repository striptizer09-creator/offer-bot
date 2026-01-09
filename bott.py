import asyncio
import logging
import os
import sys
import threading
import time
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties

# ==================== НАСТРОЙКА ЛОГИРОВАНИЯ ====================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ==================== ПОЛУЧАЕМ ТОКЕН ИЗ НАСТРОЕК RENDER ====================
API_TOKEN = os.getenv("BOT_TOKEN")
if not API_TOKEN:
    logger.error("❌ ОШИБКА: BOT_TOKEN не найден!")
    logger.error("Добавьте BOT_TOKEN в настройках Render:")
    logger.error("Environment → Add Environment Variable")
    sys.exit(1)

# Список ID админов
ADMIN_IDS = [5084915945, 1762671580]

# ==================== ИНИЦИАЛИЗАЦИЯ БОТА ====================
bot = Bot(token=API_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()

# ==================== HTTP СЕРВЕР ДЛЯ RENDER ====================
def start_http_server():
    """Простой HTTP сервер для проверки портов Render"""
    try:
        # Импортируем Flask внутри функции, чтобы не было предупреждений
        from flask import Flask
        
        app = Flask('telegram_bot_health')
        
        @app.route('/')
        def home():
            return "🤖 Telegram Bot is running on Render", 200
        
        @app.route('/health')
        def health():
            return {
                "status": "healthy",
                "service": "telegram-offer-bot",
                "timestamp": time.time()
            }, 200
        
        @app.route('/ping')
        def ping():
            return "pong", 200
        
        # Получаем порт из переменных окружения или используем 10000
        port = int(os.getenv('PORT', 10000))
        
        # Запускаем в отдельном потоке
        def run():
            app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)
        
        thread = threading.Thread(target=run, daemon=True)
        thread.start()
        logger.info(f"🌐 HTTP сервер запущен на порту {port} для Render")
        
    except ImportError:
        logger.warning("⚠️ Flask не установлен, HTTP сервер не запущен. Установите: pip install flask")
    except Exception as e:
        logger.error(f"❌ Ошибка запуска HTTP сервера: {e}")

# Запускаем HTTP сервер
start_http_server()

# ==================== КОМАНДА /START ====================
@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    welcome_text = (
        "Привет, ты можешь предложить что-то свое, а мы это выложим. Не забудь указать автора (лучше указать на него ссылку). Имей ввиду, что, если не указан автор или предложенный тобой пост содержит контент оскорбительного характера, он автоматически не будет нами принят."
    )
    await message.answer(welcome_text)
    logger.info(f"✅ Пользователь {message.from_user.id} запустил бота")

# ==================== ПЕРЕСЫЛКА СООБЩЕНИЙ ====================
@dp.message(lambda message: message.text and not message.text.startswith('/'))
async def forward_text_message(message: types.Message):
    user = message.from_user
    
    user_info = f"📨 <b>НОВАЯ ПРЕДЛОЖКА (ТЕКСТ)</b>\n\n"
    user_info += f"👤 <b>От:</b> {user.first_name}"
    if user.username:
        user_info += f" (@{user.username})"
    user_info += f"\n🆔 <b>ID:</b> {user.id}\n"
    user_info += f"\n📝 <b>Сообщение:</b>\n{message.text}"
    
    success_count = 0
    for admin_id in ADMIN_IDS:
        try:
            await bot.send_message(chat_id=admin_id, text=user_info)
            success_count += 1
        except Exception as e:
            logger.error(f"❌ Ошибка отправки админу {admin_id}: {e}")
    
    if success_count > 0:
        await message.answer("✅ Сообщение отправлено админам!")
    else:
        await message.answer("❌ Не удалось отправить. Попробуйте позже.")

@dp.message(lambda message: message.photo or message.video or message.document or 
                      message.voice or message.audio or message.animation or message.sticker)
async def forward_media_message(message: types.Message):
    user = message.from_user
    
    caption = f"📎 <b>НОВАЯ ПРЕДЛОЖКА (МЕДИА)</b>\n\n"
    caption += f"👤 <b>От:</b> {user.first_name}"
    if user.username:
        caption += f" (@{user.username})"
    caption += f"\n🆔 <b>ID:</b> {user.id}"
    
    if message.caption:
        caption += f"\n\n📝 <b>Подпись:</b>\n{message.caption}"
    
    success_count = 0
    for admin_id in ADMIN_IDS:
        try:
            await bot.copy_message(
                chat_id=admin_id,
                from_chat_id=message.chat.id,
                message_id=message.message_id,
                caption=caption[:1024]
            )
            success_count += 1
        except Exception as e:
            logger.error(f"❌ Ошибка отправки медиа админу {admin_id}: {e}")
    
    if success_count > 0:
        await message.answer("✅ Медиа отправлено админам!")
    else:
        await message.answer("❌ Не удалось отправить медиа.")

# ==================== ЗАПУСК БОТА ====================
async def main():
    logger.info("=" * 50)
    logger.info("🚀 БОТ-ПРЕДЛОЖКА ЗАПУСКАЕТСЯ НА RENDER")
    logger.info("=" * 50)
    
    bot_info = await bot.get_me()
    logger.info(f"🤖 Бот: @{bot_info.username}")
    
    # Уведомление админам
    for admin_id in ADMIN_IDS:
        try:
            await bot.send_message(
                chat_id=admin_id,
                text=f"🤖 <b>Бот-предложка @{bot_info.username} запущен!</b>\n\n"
                     f"📍 <b>Сервер:</b> Render\n"
                     f"⏰ <b>Статус:</b> 24/7\n"
                     f"✅ Готов принимать предложки!"
            )
            logger.info(f"📢 Уведомление отправлено админу {admin_id}")
        except Exception as e:
            logger.error(f"❌ Не удалось отправить уведомление админу {admin_id}: {e}")
    
    logger.info("⏳ Бот запущен. Ожидание сообщений...")
    await dp.start_polling(bot)

# ==================== БЕСКОНЕЧНЫЙ ЦИКЛ ====================
if __name__ == "__main__":
    # Бесконечный цикл с перезапуском
    restart_count = 0
    max_restarts = 50
    
    while restart_count < max_restarts:
        try:
            asyncio.run(main())
        except KeyboardInterrupt:
            logger.info("👋 Бот остановлен пользователем")
            break
        except Exception as e:
            restart_count += 1
            logger.error(f"💀 Ошибка №{restart_count}/{max_restarts}: {e}")
            
            if restart_count < max_restarts:
                logger.info(f"🔄 Перезапуск через 10 секунд...")
                time.sleep(10)
            else:
                logger.error(f"🚫 Достигнут лимит перезапусков. Бот остановлен.")
                break