import asyncio
import logging
import os
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Получаем токен из переменных окружения
API_TOKEN = os.getenv("BOT_TOKEN")
if not API_TOKEN:
    logger.error("❌ ОШИБКА: BOT_TOKEN не найден!")
    exit(1)

# Список ID админов
ADMIN_IDS = [5084915945, 1762671580]

# Инициализация бота
bot = Bot(token=API_TOKEN)
dp = Dispatcher()

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

# ==================== ЗАПУСК БОТА ====================
async def main():
    logger.info("🤖 Бот-предложка запускается...")
    
    # Получаем информацию о боте
    bot_info = await bot.get_me()
    logger.info(f"Бот: @{bot_info.username}")
    
    # Уведомляем админов (если не получится - не страшно)
    for admin_id in ADMIN_IDS:
        try:
            await bot.send_message(
                chat_id=admin_id,
                text=f"🤖 <b>Бот-предложка @{bot_info.username} запущен!</b>"
            )
        except:
            pass
    
    logger.info("✅ Бот запущен. Ожидание сообщений...")
    
    # Запускаем поллинг
    await dp.start_polling(bot)

# ==================== ТОЧКА ВХОДА ====================
if __name__ == "__main__":
    # Простой запуск без сложных манипуляций
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("👋 Бот остановлен")
    except Exception as e:
        logger.error(f"💀 Фатальная ошибка: {e}")