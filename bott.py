import asyncio
import logging
import os
import socket
import threading
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

# ==================== HTTP СЕРВЕР ДЛЯ RENDER ====================
def start_http_server():
    """Простой HTTP сервер для Render"""
    def run():
        port = int(os.getenv('PORT', 10000))
        logger.info(f"🌐 HTTP сервер на порту {port}")
        
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind(('0.0.0.0', port))
        server.listen(5)
        
        while True:
            client, addr = server.accept()
            try:
                client.recv(1024)
                response = b'HTTP/1.1 200 OK\r\nContent-Type: text/plain\r\n\r\nBot is running'
                client.sendall(response)
            except:
                pass
            finally:
                client.close()
    
    thread = threading.Thread(target=run, daemon=True)
    thread.start()

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

# ==================== ОБРАБОТКА СООБЩЕНИЙ ====================
@dp.message()
async def handle_message(message: types.Message):
    # Пропускаем команды
    if message.text and message.text.startswith('/'):
        return
    
    # Просто пересылаем админам
    sent = False
    for admin_id in ADMIN_IDS:
        try:
            await message.forward(admin_id)
            sent = True
        except:
            pass
    
    # Ответ пользователю
    if sent:
        await message.answer("✅ Сообщение отправлено админам!")
    else:
        await message.answer("❌ Не удалось отправить. Попробуйте позже.")

# ==================== ЗАПУСК ====================
async def main():
    logger.info("🤖 Бот запущен")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())