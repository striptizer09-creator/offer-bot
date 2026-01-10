import asyncio
import logging
import os
import sys
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

# ==================== УПРОЩЕННЫЙ HTTP СЕРВЕР ====================
def run_simple_http_server():
    """Простой HTTP сервер в отдельном процессе для Render"""
    import socket
    import threading
    
    def serve():
        port = int(os.getenv('PORT', 10000))
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                s.bind(('0.0.0.0', port))
                s.listen(5)
                logger.info(f"🌐 Health check сервер запущен на порту {port}")
                
                while True:
                    conn, addr = s.accept()
                    with conn:
                        # Читаем запрос
                        data = conn.recv(1024)
                        if data:
                            # Простой HTTP ответ
                            response = b'HTTP/1.1 200 OK\r\nContent-Type: text/plain\r\n\r\nBot is running'
                            conn.sendall(response)
        except Exception as e:
            logger.error(f"❌ Ошибка HTTP сервера: {e}")
    
    # Запускаем в отдельном потоке
    thread = threading.Thread(target=serve, daemon=True)
    thread.start()
    return thread

# Запускаем HTTP сервер
http_thread = run_simple_http_server()

# ==================== КОМАНДА /START ====================
@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    welcome_text = (
        "Привет, ты можешь предложить что-то свое, а мы это выложим. Не забудь указать автора (лучше указать на него ссылку). Имей ввиду, что, если не указан автор или предложенный тобой пост содержит контент оскорбительного характера, он автоматически не будет нами принят."
    )
    await message.answer(welcome_text)
    logger.info(f"✅ Пользователь {message.from_user.id} запустил бота")

# ==================== ПЕРЕСЫЛКА ТЕКСТОВЫХ СООБЩЕНИЙ ====================
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

# ==================== ПЕРЕСЫЛКА МЕДИА-СООБЩЕНИЙ ====================
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

# ==================== ОСНОВНАЯ ФУНКЦИЯ ====================
async def run_bot():
    """Основная функция для запуска бота"""
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

# ==================== ЗАПУСК ====================
if __name__ == "__main__":
    # Простой запуск без сложного перезапуска
    try:
        # Убедимся, что у нас правильный event loop
        loop = asyncio.get_event_loop()
        if loop.is_closed():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        # Запускаем бота
        loop.run_until_complete(run_bot())
    except KeyboardInterrupt:
        logger.info("👋 Бот остановлен пользователем")
    except Exception as e:
        logger.error(f"💀 Фатальная ошибка: {e}")
        # Попытка перезапуска один раз
        logger.info("🔄 Попытка перезапуска через 10 секунд...")
        time.sleep(10)
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(run_bot())
        except Exception as e2:
            logger.error(f"💀 Ошибка при перезапуске: {e2}")