from sqlalchemy import Column, Integer, ForeignKey
from sqlalchemy.orm import relationship
from database import Base

class CartItem(Base):
    __tablename__ = "cart_items"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer)
    product_id = Column(Integer, ForeignKey("products.id"))
    quantity = Column(Integer, default=1)

    product = relationship("Product")
    # You can add more fields if necessary, such as timestamps or status indicators.