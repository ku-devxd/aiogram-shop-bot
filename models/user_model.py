from sqlalchemy import Column, Integer, String
from base import Base  # <-- Base из base.py

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    lang = Column(String, default="en")

async def get_user_lang(user_id: int) -> str:
    from database import async_session  # импорт внутри функции

    async with async_session() as session:
        result = await session.get(User, user_id)
        if result:
            return result.lang
        new_user = User(id=user_id, lang="en")
        session.add(new_user)
        await session.commit()
        return "en"
