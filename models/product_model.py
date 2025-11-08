from sqlalchemy import Integer, String, Text
from base import Base
from sqlalchemy.orm import Mapped, mapped_column

class Product(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    price: Mapped[int] = mapped_column(Integer)
    description: Mapped[str] = mapped_column(Text)
    photo_url: Mapped[str] = mapped_column(String, nullable=True)

    category: Mapped[str] = mapped_column(String(50))  # ✅ новая строка
    # image_url: Mapped[str] = mapped_column(String, nullable=True)  # ✅ новая строка