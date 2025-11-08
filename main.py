import asyncio
from aiogram import Bot, Dispatcher
from config import TOKEN
from database import init_db

# Роутеры
from handlers.user_handlers import router as user_router
from handlers.admin_handlers import router as admin_router

async def main():
    # Инициализация базы данных
    await init_db()
    print("✅ Database initialized")

    # Создание бота и диспетчера
    bot = Bot(token=TOKEN)
    dp = Dispatcher()

    # Подключение роутеров
    dp.include_router(admin_router)
    dp.include_router(user_router)

    print("Bot is running...")
    # Запуск polling
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
