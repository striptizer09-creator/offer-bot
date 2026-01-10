import asyncio
import logging
import os
import threading
import socket
import time
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Получаем токен
API_TOKEN = os.getenv("BOT_TOKEN")
if not API_TOKEN:
    logger.error("❌ BOT_TOKEN не найден!")
    exit(1)

ADMIN_IDS = [5084915945, 1762671580]
bot = Bot(token=API_TOKEN)
dp = Dispatcher()

# ==================== ПРОСТОЙ HTTP СЕРВЕР ====================
def start_http_server():
    """Запускает простой HTTP сервер для Render"""
    def run_server():
        port = int(os.getenv('PORT', 10000))
        try:
            server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server.bind(('0.0.0.0', port))
            server.listen(5)
            logger.info(f"🌐 HTTP сервер запущен на порту {port}")
            
            while True:
                client, addr = server.accept()
                try:
                    # Читаем запрос (нам не важно что в нем)
                    client.recv(1024)
                    # Отправляем ответ
                    response = b'HTTP/1.1 200 OK\r\nContent-Type: text/plain\r\n\r\nBot is running'
                    client.sendall(response)
                except:
                    pass
                finally:
                    client.close()
        except Exception as e:
            logger.error(f"❌ Ошибка HTTP сервера: {e}")
    
    thread = threading.Thread(target=run_server, daemon=True)
    thread.start()
    return thread

# Запускаем HTTP сервер
start_http_server()

# ==================== КОМАНДА /START ====================
@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    welcome_text = (
        "Привет, ты можешь предложить что-то свое, а мы это выложим. "
        "Не забудь указать автора (лучше указать на него ссылку). "
        "Имей ввиду, что, если не указан автор или предложенный тобой пост "
        "содержит контент оскорбительного характера, он автоматически не будет нами принят."
    )
    await message.answer(welcome_text)
    logger.info(f"✅ Пользователь {message.from_user.id} запустил бота")

# ==================== ОБРАБОТКА СООБЩЕНИЙ ====================
@dp.message()
async def handle_message(message: types.Message):
    # Пропускаем команды
    if message.text and message.text.startswith('/'):
        return
    
    user = message.from_user
    
    # Формируем сообщение для админов
    admin_message = f"📨 <b>НОВАЯ ПРЕДЛОЖКА</b>\n\n"
    admin_message += f"👤 От: {user.first_name}"
    if user.username:
        admin_message += f" (@{user.username})"
    admin_message += f"\n🆔 ID: {user.id}\n"
    
    if message.text:
        admin_message += f"\n📝 Сообщение:\n{message.text}"
    elif message.caption:
        admin_message += f"\n📝 Подпись:\n{message.caption}"
    
    # Отправляем админам
    sent = False
    for admin_id in ADMIN_IDS:
        try:
            if message.photo or message.video or message.document or message.sticker:
                await bot.copy_message(
                    chat_id=admin_id,
                    from_chat_id=message.chat.id,
                    message_id=message.message_id,
                    caption=admin_message[:1024] if admin_message else None
                )
            else:
                await bot.send_message(admin_id, admin_message)
            sent = True
        except Exception as e:
            logger.error(f"❌ Ошибка отправки админу {admin_id}: {e}")
    
    # Ответ пользователю
    if sent:
        await message.answer("✅ Сообщение отправлено админам!")
    else:
        await message.answer("❌ Не удалось отправить. Попробуйте позже.")

# ==================== ЗАПУСК БОТА ====================
async def main():
    logger.info("🚀 Бот запускается...")
    
    bot_info = await bot.get_me()
    logger.info(f"🤖 Бот: @{bot_info.username}")
    
    # Уведомление админам
    for admin_id in ADMIN_IDS:
        try:
            await bot.send_message(
                admin_id,
                f"🤖 <b>Бот-предложка @{bot_info.username} запущен!</b>"
            )
        except:
            pass
    
    logger.info("✅ Бот готов принимать сообщения")
    await dp.start_polling(bot, skip_updates=True)

# ==================== ОСНОВНОЙ ЦИКЛ ====================
if __name__ == "__main__":
    max_restarts = 3
    restart_count = 0
    
    while restart_count < max_restarts:
        try:
            asyncio.run(main())
            break
        except KeyboardInterrupt:
            logger.info("👋 Бот остановлен")
            break
        except Exception as e:
            restart_count += 1
            logger.error(f"💀 Ошибка {restart_count}/{max_restarts}: {e}")
            if restart_count < max_restarts:
                logger.info(f"🔄 Перезапуск через 10 секунд...")
                time.sleep(10)