import asyncio
import logging
import os
import threading
import time
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart
from aiogram.enums import ParseMode

# ==================== НАСТРОЙКА ЛОГИРОВАНИЯ ====================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ==================== ПОЛУЧАЕМ ТОКЕН ====================
API_TOKEN = os.getenv("BOT_TOKEN")
if not API_TOKEN:
    logger.error("❌ ОШИБКА: BOT_TOKEN не найден!")
    exit(1)

# Список ID админов
ADMIN_IDS = [5084915945, 1762671580]

# ==================== ИНИЦИАЛИЗАЦИЯ БОТА ====================
bot = Bot(token=API_TOKEN, parse_mode=ParseMode.HTML)
dp = Dispatcher()

# ==================== ПРОСТОЙ HTTP СЕРВЕР ДЛЯ RENDER ====================
def start_health_server():
    """Запускает простой HTTP сервер в отдельном потоке"""
    try:
        import socket
        
        def run_server():
            port = int(os.getenv('PORT', 10000))
            logger.info(f"🌐 Запуск HTTP сервера на порту {port}")
            
            try:
                server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                server.bind(('0.0.0.0', port))
                server.listen(5)
                
                while True:
                    client, addr = server.accept()
                    try:
                        # Читаем запрос
                        client.recv(1024)
                        # Отправляем простой ответ
                        response = (
                            b'HTTP/1.1 200 OK\r\n'
                            b'Content-Type: text/plain\r\n'
                            b'Content-Length: 19\r\n'
                            b'\r\n'
                            b'Bot is running'
                        )
                        client.sendall(response)
                    except:
                        pass
                    finally:
                        client.close()
            except Exception as e:
                logger.error(f"❌ Ошибка HTTP сервера: {e}")
        
        # Запускаем в отдельном потоке
        thread = threading.Thread(target=run_server, daemon=True)
        thread.start()
        return thread
        
    except Exception as e:
        logger.error(f"❌ Не удалось запустить HTTP сервер: {e}")
        return None

# Запускаем HTTP сервер
start_health_server()

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

# ==================== ПЕРЕСЫЛКА СООБЩЕНИЙ ====================
@dp.message()
async def handle_all_messages(message: types.Message):
    # Пропускаем команду /start
    if message.text and message.text.startswith('/'):
        return
    
    user = message.from_user
    
    # Формируем информацию о пользователе
    user_info = f"📨 <b>НОВАЯ ПРЕДЛОЖКА</b>\n\n"
    user_info += f"👤 <b>От:</b> {user.first_name}"
    if user.username:
        user_info += f" (@{user.username})"
    user_info += f"\n🆔 <b>ID:</b> {user.id}\n"
    
    # Добавляем текст или подпись
    if message.text:
        user_info += f"\n📝 <b>Сообщение:</b>\n{message.text}"
    elif message.caption:
        user_info += f"\n📝 <b>Подпись:</b>\n{message.caption}"
    
    # Отправляем всем админам
    success_count = 0
    for admin_id in ADMIN_IDS:
        try:
            if message.photo or message.video or message.document or message.voice or message.audio or message.animation or message.sticker:
                # Для медиа используем copy_message
                await bot.copy_message(
                    chat_id=admin_id,
                    from_chat_id=message.chat.id,
                    message_id=message.message_id,
                    caption=user_info[:1024] if user_info else None
                )
            else:
                # Для текста просто отправляем
                await bot.send_message(chat_id=admin_id, text=user_info)
            success_count += 1
        except Exception as e:
            logger.error(f"❌ Ошибка отправки админу {admin_id}: {e}")
    
    # Ответ пользователю
    if success_count > 0:
        await message.answer("✅ Сообщение отправлено админам!")
    else:
        await message.answer("❌ Не удалось отправить. Попробуйте позже.")

# ==================== ОСНОВНАЯ ФУНКЦИЯ БОТА ====================
async def run_bot():
    """Запускает бота"""
    logger.info("🚀 Бот-предложка запускается...")
    
    # Получаем информацию о боте
    bot_info = await bot.get_me()
    logger.info(f"🤖 Бот: @{bot_info.username}")
    
    # Уведомляем админов
    for admin_id in ADMIN_IDS:
        try:
            await bot.send_message(
                chat_id=admin_id,
                text=f"🤖 <b>Бот-предложка @{bot_info.username} запущен!</b>\n\n"
                     f"📍 <b>Сервер:</b> Render\n"
                     f"⏰ <b>Статус:</b> 24/7"
            )
            logger.info(f"📢 Уведомление отправлено админу {admin_id}")
        except Exception as e:
            logger.error(f"❌ Не удалось отправить админу {admin_id}: {e}")
    
    logger.info("✅ Бот запущен. Ожидание сообщений...")
    
    # Запускаем поллинг
    await dp.start_polling(bot, skip_updates=True)

# ==================== ГЛАВНАЯ ТОЧКА ВХОДА ====================
def main():
    """Главная функция с обработкой перезапусков"""
    max_restarts = 5
    restart_count = 0
    
    while restart_count < max_restarts:
        try:
            logger.info(f"🔄 Запуск бота (попытка {restart_count + 1}/{max_restarts})")
            
            # Создаем новый event loop для каждой попытки
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            # Запускаем бота
            loop.run_until_complete(run_bot())
            
        except KeyboardInterrupt:
            logger.info("👋 Бот остановлен пользователем")
            break
        except Exception as e:
            restart_count += 1
            logger.error(f"💀 Ошибка №{restart_count}: {e}")
            
            if restart_count < max_restarts:
                wait_time = 10 * restart_count
                logger.info(f"🔄 Перезапуск через {wait_time} секунд...")
                time.sleep(wait_time)
            else:
                logger.error(f"🚫 Достигнут лимит перезапусков ({max_restarts})")

if __name__ == "__main__":
    main()