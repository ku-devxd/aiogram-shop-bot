from aiogram import Router, F, types
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy import select

from database import async_session
from models.product_model import Product
from models.user_model import get_user_lang
from config import ADMIN_ID

router = Router()


# ------- FSM
class AddProductFSM(StatesGroup):
    name = State()
    price = State()
    description = State()
    category = State()
    image = State()


# ------- MULTILANG TEXTS 
TEXTS = {
    "en": {
        "send_name": "✏ Send product name:",
        "send_price": "💲 Send price:",
        "send_description": "📝 Send description:",
        "send_category": "Enter category (men / women / electronics / etc):",
        "send_image": "📸 Send image URL or photo:",
        "added": "Product successfully added!"
    },
    "ru": {
        "send_name": "✏ Отправьте название товара:",
        "send_price": "💲 Отправьте цену:",
        "send_description": "📝 Отправьте описание:",
        "send_category": "Введите категорию (men / women / electronics / etc):",
        "send_image": "📸 Отправьте фото или ссылку на изображение:",
        "added": "Товар успешно добавлен!"
    }
}


async def t(user_id: int, key: str) -> str:
    lang = await get_user_lang(user_id)  # "en" или "ru"
    return TEXTS.get(lang, TEXTS["en"]).get(key, key)


# ------- ADD PRODUCT
@router.message(F.text == "/add_product")
async def add_start(message: Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        return await message.answer("You are not admin.")
    await state.set_state(AddProductFSM.name)
    await message.answer(await t(message.from_user.id, "send_name"))


@router.message(AddProductFSM.name)
async def add_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text)
    await state.set_state(AddProductFSM.price)
    await message.answer(await t(message.from_user.id, "send_price"))


@router.message(AddProductFSM.price)
async def add_price(message: Message, state: FSMContext):
    await state.update_data(price=message.text)
    await state.set_state(AddProductFSM.description)
    await message.answer(await t(message.from_user.id, "send_description"))


@router.message(AddProductFSM.description)
async def add_desc(message: Message, state: FSMContext):
    await state.update_data(description=message.text)
    await state.set_state(AddProductFSM.category)
    await message.answer(await t(message.from_user.id, "send_category"))


@router.message(AddProductFSM.category)
async def add_category(message: Message, state: FSMContext):
    category = message.text.strip().lower()
    valid_categories = ["men", "women", "electronics", "other"]
    if category not in valid_categories:
        category = "other"
    await state.update_data(category=category)
    await state.set_state(AddProductFSM.image)
    await message.answer(await t(message.from_user.id, "send_image"))


@router.message(AddProductFSM.image)
async def add_finish(message: Message, state: FSMContext):
    data = await state.get_data()
    if message.photo:
        photo_url = message.photo[-1].file_id
    else:
        photo_url = message.text

    async with async_session() as session:
        product = Product(
            name=data["name"],
            price=float(data["price"]),
            description=data["description"],
            category=data["category"],
            photo_url=photo_url
        )
        session.add(product)
        await session.commit()

    await state.clear()
    await message.answer(await t(message.from_user.id, "added"))
