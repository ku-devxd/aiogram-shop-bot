from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from sqlalchemy.orm import joinedload
from sqlalchemy import select, delete
from models.cart_model import CartItem
from models.product_model import Product
from models.user_model import User
from database import async_session

from yookassa import Payment
from config import YOOKASSA_SECRET_KEY, YOOKASSA_SHOP_ID

Payment.account_id = YOOKASSA_SHOP_ID
Payment.secret_key = YOOKASSA_SECRET_KEY

router = Router()


# --- Функция для экранирования Markdown ---
def escape_md(text: str) -> str:
    escape_chars = r"\*_`["
    for ch in escape_chars:
        text = text.replace(ch, f"\\{ch}")
    return text


# --- Мультиязычные тексты ---
TEXTS = {
    "choose_category": {"en": "Choose a category:", "ru": "Выберите категорию:"},
    "cart_empty": {"en": "Your cart is empty 🛒", "ru": "Корзина пуста 🛒"},
    "added_to_cart": {"en": "✅ Added to cart", "ru": "✅ Добавлено в корзину"},
    "checkout_msg": {"en": "Pay for your items:", "ru": "Оплатить товары:"},
    "language_set": {"en": "✅ Language set: English", "ru": "✅ Язык установлен: Русский"},
    "start_msg": {"en": "Please select your language:", "ru": "Пожалуйста, выберите язык:"},
    "no_products": {"en": "No products in this category", "ru": "В этой категории нет товаров"}
}


def get_text(lang: str, key: str, **kwargs):
    return TEXTS[key][lang].format(**kwargs)


# --- Работа с языком пользователя ---
async def get_user_lang(user_id: int) -> str:
    async with async_session() as session:
        result = await session.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if user and user.lang:
            return user.lang
    return "en"





# --- Клавиатура главного меню ---
def main_menu_keyboard(lang: str) -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🛍 Товары" if lang == "ru" else "🛍 Products")],
            [KeyboardButton(text="📂 Категории" if lang == "ru" else "📂 Categories")],
            [KeyboardButton(text="🛒 Моя корзина" if lang == "ru" else "🛒 My cart")],
            [KeyboardButton(text="📦 Мои заказы" if lang == "ru" else "📦 My orders")]
        ],
        resize_keyboard=True
    )


# --- Сервис корзины ---
class CartService:
    @staticmethod
    async def get_items(user_id: int) -> list[CartItem]:
        async with async_session() as session:
            result = await session.execute(
                select(CartItem)
                .options(joinedload(CartItem.product))
                .where(CartItem.user_id == user_id)
            )
            return result.scalars().all()

    @staticmethod
    async def add_item(user_id: int, product_id: int):
        async with async_session() as session:
            result = await session.execute(
                select(CartItem).where(CartItem.user_id == user_id, CartItem.product_id == product_id)
            )
            item = result.scalar_one_or_none()
            if item:
                item.quantity += 1
            else:
                session.add(CartItem(user_id=user_id, product_id=product_id, quantity=1))
            await session.commit()

    @staticmethod
    async def clear_cart(user_id: int):
        async with async_session() as session:
            await session.execute(delete(CartItem).where(CartItem.user_id == user_id))
            await session.commit()

    @staticmethod
    def format_cart(cart_items: list[CartItem], lang: str) -> tuple[str, int]:
        if not cart_items:
            return get_text(lang, "cart_empty"), 0

        total = 0
        text = f"🛒 {'Your cart:' if lang == 'en' else 'Твоя корзина:'}\n\n"
        for item in cart_items:
            name = escape_md(item.product.name)
            item_total = item.product.price * item.quantity
            text += f"• {name} — {item.quantity} шт. — {item_total} ₽\n"
            total += item_total

        total_text = f"\nTotal: {total} ₽" if lang == "en" else f"\nИтого: {total} ₽"
        return text + total_text, total


# --- Выбор языка ---
@router.message(Command("start"))
async def cmd_start(message: types.Message):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🇷🇺 Русский", callback_data="lang_ru")],
        [InlineKeyboardButton(text="🇬🇧 English", callback_data="lang_en")]
    ])
    await message.answer(get_text("en", "start_msg") + " / " + get_text("ru", "start_msg"), reply_markup=keyboard)


@router.callback_query(F.data.startswith("lang_"))
async def set_language(call: types.CallbackQuery):
    lang = call.data.split("_")[1]
    async with async_session() as session:
        result = await session.execute(select(User).where(User.id == call.from_user.id))
        user = result.scalar_one_or_none()
        if not user:
            session.add(User(id=call.from_user.id, lang=lang))
        else:
            user.lang = lang
        await session.commit()

    await call.message.answer(get_text(lang, "language_set"))
    await call.message.answer(
        "Главное меню:" if lang == "ru" else "Main menu:",
        reply_markup=main_menu_keyboard(lang)
    )
    await call.answer()


# --- Главное меню ---
@router.message(F.text.in_([
    "🛍 Товары", "🛍 Products",
    "📂 Категории", "📂 Categories",
    "🛒 Моя корзина", "🛒 My cart",
    "📦 Мои заказы", "📦 My orders"
]))
async def main_menu_handler(message: types.Message):
    user_id = message.from_user.id
    lang = await get_user_lang(user_id)
    text = message.text

    if text in ["🛍 Товары", "🛍 Products", "📂 Категории", "📂 Categories"]:
        await message.answer(
            get_text(lang, "choose_category"),
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🛍 All Products", callback_data="cat_all")],
                [InlineKeyboardButton(text="👕 Men", callback_data="cat_men")],
                [InlineKeyboardButton(text="👗 Women", callback_data="cat_women")],
                [InlineKeyboardButton(text="📱 Electronics", callback_data="cat_electronics")]
            ])
        )

    elif text in ["🛒 Моя корзина", "🛒 My cart"]:
        await show_cart(message)

    elif text in ["📦 Мои заказы", "📦 My orders"]:
        await message.answer(
            "Здесь будут ваши заказы" if lang == "ru" else "Your orders will be here"
        )
# --- Показ корзины ---
async def show_cart(message: types.Message):
    user_id = message.from_user.id
    lang = await get_user_lang(user_id)
    cart_items = await CartService.get_items(user_id)
    text, _ = CartService.format_cart(cart_items, lang)

    if not cart_items:
        await message.answer(text)
        return

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Checkout" if lang == "en" else "✅ Оформить заказ", callback_data="checkout")],
        [InlineKeyboardButton(text="🗑 Clear cart" if lang == "en" else "🗑 Очистить корзину", callback_data="clear_cart")]
    ])
    await message.answer(text, parse_mode="Markdown", reply_markup=keyboard)


# --- Добавление в корзину ---
@router.callback_query(F.data.startswith("add_to_cart_"))
async def add_to_cart(callback: types.CallbackQuery):
    product_id = int(callback.data.split("_")[-1])
    user_id = callback.from_user.id
    lang = await get_user_lang(user_id)

    await CartService.add_item(user_id, product_id)
    await callback.answer(get_text(lang, "added_to_cart"), show_alert=False)


# --- Очистка корзины ---
@router.callback_query(F.data == "clear_cart")
async def clear_cart(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    lang = await get_user_lang(user_id)

    await CartService.clear_cart(user_id)
    await callback.message.edit_text("🗑 " + ("Cart cleared" if lang == "en" else "Корзина очищена"))
    await callback.answer()


# --- Показ товаров по категории ---
async def show_category(call: types.CallbackQuery, category: str):
    lang = await get_user_lang(call.from_user.id)

    async with async_session() as session:
        result = await session.execute(select(Product).where(Product.category == category))
        products = result.scalars().all()

    if not products:
        await call.message.answer(get_text(lang, "no_products"))
        return

    for p in products:
        name = escape_md(p.name)
        desc = escape_md(p.description) if p.description else ""
        caption = f"*{name}*\n{desc}\nЦена: {p.price} ₽"

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(
                text="🛒 Add to cart" if lang == "en" else "🛒 Добавить в корзину",
                callback_data=f"add_to_cart_{p.id}"
            )]
        ])
        await call.message.answer_photo(photo=p.photo_url, caption=caption, parse_mode="Markdown", reply_markup=keyboard)


# --- Обработчик для callback от категорий (cat_*) ---
@router.callback_query(F.data.startswith("cat_"))
async def category_callback(call: types.CallbackQuery):
    # callback_data имеет вид "cat_<category>" — получим категорию
    category = call.data.split("_", 1)[1]
    await show_category(call, category)
    await call.answer()


# --- Покупка отдельного товара ---
@router.callback_query(F.data.startswith("buy_"))
async def buy_product(callback: types.CallbackQuery):
    product_id = int(callback.data.split("_")[1])
    lang = await get_user_lang(callback.from_user.id)

    async with async_session() as session:
        result = await session.execute(select(Product).where(Product.id == product_id))
        product = result.scalar_one_or_none()

    if not product:
        await callback.message.answer("❌ Product not found" if lang == "en" else "❌ Товар не найден")
        return

    payment = Payment.create({
        "amount": {"value": str(product.price), "currency": "RUB"},
        "confirmation": {"type": "redirect", "return_url": "https://t.me/your_bot"},
        "capture": True,
        "description": product.name
    })

    await callback.message.answer(
        f"🛒 {product.name}\n💰 {product.price} ₽\n\nPay: {payment.confirmation.confirmation_url}"
        if lang == "en" else f"🛒 {product.name}\n💰 {product.price} ₽\n\nОплатить: {payment.confirmation.confirmation_url}"
    )
    await callback.answer()


# --- Checkout корзины ---
@router.callback_query(F.data == "checkout")
async def checkout(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    lang = await get_user_lang(user_id)
    cart_items = await CartService.get_items(user_id)

    if not cart_items:
        await callback.message.answer(get_text(lang, "cart_empty"))
        await callback.answer()
        return

    _, total = CartService.format_cart(cart_items, lang)
    description = ", ".join(f"{item.product.name} x{item.quantity}" for item in cart_items)

    payment = Payment.create({
        "amount": {"value": str(total), "currency": "RUB"},
        "confirmation": {"type": "redirect", "return_url": "https://t.me/your_bot"},
        "capture": True,
        "description": description
    })

    await callback.message.answer(
        f"💳 {get_text(lang, 'checkout_msg')}\n\nTotal: {total} ₽\nPay: {payment.confirmation.confirmation_url}"
        if lang == "en" else f"💳 {get_text(lang, 'checkout_msg')}\n\nИтого: {total} ₽\nОплатить: {payment.confirmation.confirmation_url}"
    )

    await CartService.clear_cart(user_id)
    await callback.answer()





@router.message()
async def fallback(message: types.Message):
    lang = await get_user_lang(message.from_user.id)
    await message.answer(
        "Выберите опцию из меню" if lang == "ru" else "Please choose an option from the menu\n",
        reply_markup=main_menu_keyboard(lang)
    )

