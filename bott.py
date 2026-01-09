import asyncio
import logging
import os
import sys
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

# ==================== ПОЛУЧАЕМ ТОКЕН ИЗ НАСТРОЕК RAILWAY ====================
API_TOKEN = os.getenv("BOT_TOKEN")
if not API_TOKEN:
    logger.error("❌ ОШИБКА: BOT_TOKEN не найден!")
    logger.error("Добавьте BOT_TOKEN в настройках Railway:")
    logger.error("Settings → Variables → Add Variable")
    sys.exit(1)

# Список ID админов (получателей предложок)
ADMIN_IDS = [5084915945, 1762671580]

# ==================== ИНИЦИАЛИЗАЦИЯ БОТА ====================
bot = Bot(token=API_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()

# ==================== КОМАНДА /START ====================
@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    """Обработчик команды /start"""
    welcome_text = (
        "Привет, ты можешь предложить что-то свое, а мы это выложим. Не забудь указать автора (учше скинуть на него ссылку). Имей ввиду, что, если не указан автор или предложенный тобой пост содержит контент оскорбительного характера, он автоматически не будет нами принят. "
    )
    await message.answer(welcome_text)
    logger.info(f"✅ Пользователь {message.from_user.id} запустил бота")

# ==================== ПЕРЕСЫЛКА ТЕКСТОВЫХ СООБЩЕНИЙ ====================
@dp.message(lambda message: message.text and not message.text.startswith('/'))
async def forward_text_message(message: types.Message):
    """Пересылает текстовые сообщения админам"""
    user = message.from_user
    
    # Формируем сообщение для админов
    user_info = f"📨 <b>НОВАЯ ПРЕДЛОЖКА (ТЕКСТ)</b>\n\n"
    user_info += f"👤 <b>От:</b> {user.first_name}"
    if user.username:
        user_info += f" (@{user.username})"
    user_info += f"\n🆔 <b>ID:</b> {user.id}\n"
    user_info += f"📅 <b>Время:</b> {message.date.strftime('%H:%M %d.%m.%Y')}\n"
    user_info += f"\n📝 <b>Сообщение:</b>\n{message.text}"
    
    # Отправляем всем админам
    success_count = 0
    for admin_id in ADMIN_IDS:
        try:
            await bot.send_message(
                chat_id=admin_id,
                text=user_info
            )
            success_count += 1
            logger.info(f"✅ Текст отправлен админу {admin_id}")
        except Exception as e:
            logger.error(f"❌ Ошибка отправки админу {admin_id}: {e}")
    
    # Подтверждение пользователю
    if success_count > 0:
        await message.answer("✅ Сообщение отправлено админам!")
    else:
        await message.answer("❌ Не удалось отправить. Попробуйте позже.")

# ==================== ПЕРЕСЫЛКА МЕДИА-СООБЩЕНИЙ ====================
@dp.message(lambda message: message.photo or message.video or message.document or 
                       message.voice or message.audio or message.animation or message.sticker)
async def forward_media_message(message: types.Message):
    """Пересылает медиа-сообщения админам"""
    user = message.from_user
    
    # Формируем подпись
    caption = f"📎 <b>НОВАЯ ПРЕДЛОЖКА (МЕДИА)</b>\n\n"
    caption += f"👤 <b>От:</b> {user.first_name}"
    if user.username:
        caption += f" (@{user.username})"
    caption += f"\n🆔 <b>ID:</b> {user.id}\n"
    caption += f"📅 <b>Время:</b> {message.date.strftime('%H:%M %d.%m.%Y')}"
    
    if message.caption:
        caption += f"\n\n📝 <b>Подпись:</b>\n{message.caption}"
    
    # Отправляем всем админам
    success_count = 0
    for admin_id in ADMIN_IDS:
        try:
            await bot.copy_message(
                chat_id=admin_id,
                from_chat_id=message.chat.id,
                message_id=message.message_id,
                caption=caption[:1024]  # Telegram ограничение
            )
            success_count += 1
            logger.info(f"✅ Медиа отправлено админу {admin_id}")
        except Exception as e:
            logger.error(f"❌ Ошибка отправки медиа админу {admin_id}: {e}")
    
    # Подтверждение пользователю
    if success_count > 0:
        await message.answer("✅ Медиа отправлено админам!")
    else:
        await message.answer("❌ Не удалось отправить медиа. Попробуйте позже.")

# ==================== УВЕДОМЛЕНИЕ О ЗАПУСКЕ ====================
async def on_startup():
    """Отправляет уведомление админам при запуске бота"""
    logger.info("=" * 50)
    logger.info("🚀 БОТ-ПРЕДЛОЖКА ЗАПУСКАЕТСЯ НА RAILWAY")
    logger.info("=" * 50)
    
    # Получаем информацию о боте
    bot_info = await bot.get_me()
    logger.info(f"🤖 Бот: @{bot_info.username}")
    logger.info(f"🆔 ID бота: {bot_info.id}")
    logger.info(f"👑 Админов: {len(ADMIN_IDS)}")
    
    # Отправляем уведомление админам
    for admin_id in ADMIN_IDS:
        try:
            await bot.send_message(
                chat_id=admin_id,
                text=f"🤖 <b>Бот-предложка @{bot_info.username} запущен!</b>\n\n"
                     f"📍 <b>Сервер:</b> Railway\n"
                     f"⏰ <b>Статус:</b> 24/7\n"
                     f"👥 <b>Админы:</b> {len(ADMIN_IDS)}\n\n"
                     f"✅ Готов принимать предложки!"
            )
            logger.info(f"📢 Уведомление отправлено админу {admin_id}")
        except Exception as e:
            logger.error(f"❌ Не удалось отправить уведомление админу {admin_id}: {e}")

# ==================== ОСНОВНАЯ ФУНКЦИЯ ЗАПУСКА ====================
async def main():
    """Основная функция запуска бота"""
    await on_startup()
    logger.info("⏳ Бот запущен. Ожидание сообщений...")
    
    try:
        await dp.start_polling(bot)
    except Exception as e:
        logger.error(f"💥 Критическая ошибка: {e}")
        raise

# ==================== БЕСКОНЕЧНЫЙ ЦИКЛ ДЛЯ RAILWAY ====================
if __name__ == "__main__":
    # Бесконечный цикл с автоперезапуском при ошибках
    restart_count = 0
    max_restarts = 100  # Максимум 100 перезапусков
    
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
                import time
                time.sleep(10)
            else:
                logger.error(f"🚫 Достигнут лимит перезапусков. Бот остановлен.")
                break