import asyncio
from aiogram import Bot, Dispatcher
from config import TOKEN
from database import init_db


from handlers.user_handlers import router as user_router
from handlers.admin_handlers import router as admin_router

async def main():
    
    await init_db()
    print("Database initialized!")

    
    bot = Bot(token=TOKEN)
    dp = Dispatcher()

    
    dp.include_router(admin_router)
    dp.include_router(user_router)

    print("Bot is running...")
    
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
