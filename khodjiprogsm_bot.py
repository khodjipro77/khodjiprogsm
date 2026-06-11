import asyncio
import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

# =============================================
# SOZLAMALAR - shu yerlarni o'zgartiring
# =============================================
BOT_TOKEN = "8810469523:AAF1ywU5RQHdpgUbSa5V4SkiAa2NNmjpi-Q"
ADMIN_ID = 1856943653
# =============================================

logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# Holatlar
class OrderState(StatesGroup):
    choosing_service = State()
    entering_imei = State()
    entering_details = State()
    waiting_payment = State()

# Xizmatlar ro'yxati
SERVICES = {
    "icloud": {
        "name": "🍎 iCloud Unlock",
        "desc": "iPhone/iPad barcha modellari",
        "price": "$4.99 dan",
        "info": "IMEI raqamingizni kiriting (15 ta raqam)"
    },
    "frp_samsung": {
        "name": "🔓 Samsung FRP",
        "desc": "Android 13, 14, 15",
        "price": "$0.50 dan",
        "info": "IMEI raqamingizni kiriting"
    },
    "mdm": {
        "name": "🛡️ MDM Bypass",
        "desc": "Korporativ qurilmalar",
        "price": "$9.99 dan",
        "info": "IMEI va model nomini kiriting"
    },
    "network": {
        "name": "📡 Network Unlock",
        "desc": "Barcha operatorlar",
        "price": "$1.99 dan",
        "info": "IMEI va hozirgi operator nomini kiriting"
    },
    "firmware": {
        "name": "⚡ Firmware/Repair",
        "desc": "Flash, restore, repair",
        "price": "$2.99 dan",
        "info": "Model nomi va muammoni yozing"
    },
    "imei_check": {
        "name": "🔍 IMEI Check",
        "desc": "Blacklist, warranty tekshiruv",
        "price": "$0.10 dan",
        "info": "IMEI raqamingizni kiriting"
    },
}

# Til tanlash klaviaturasi
def lang_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🇺🇿 O'zbek", callback_data="lang_uz"),
            InlineKeyboardButton(text="🇷🇺 Русский", callback_data="lang_ru"),
            InlineKeyboardButton(text="🇬🇧 English", callback_data="lang_en"),
        ]
    ])

# Xizmatlar klaviaturasi
def services_keyboard():
    buttons = []
    items = list(SERVICES.items())
    for i in range(0, len(items), 2):
        row = []
        row.append(InlineKeyboardButton(
            text=items[i][1]["name"],
            callback_data=f"svc_{items[i][0]}"
        ))
        if i + 1 < len(items):
            row.append(InlineKeyboardButton(
                text=items[i+1][1]["name"],
                callback_data=f"svc_{items[i+1][0]}"
            ))
        buttons.append(row)
    buttons.append([InlineKeyboardButton(text="🏠 Bosh sahifa", callback_data="home")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

# To'lov klaviaturasi
def payment_keyboard(order_id):
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="💳 Click orqali to'lash", callback_data=f"pay_click_{order_id}"),
        ],
        [
            InlineKeyboardButton(text="💳 Payme orqali to'lash", callback_data=f"pay_payme_{order_id}"),
        ],
        [
            InlineKeyboardButton(text="✅ To'lov qildim", callback_data=f"paid_{order_id}"),
            InlineKeyboardButton(text="❌ Bekor qilish", callback_data="cancel"),
        ]
    ])

# Admin klaviaturasi
def admin_keyboard(user_id, order_id):
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Tasdiqlash", callback_data=f"admin_confirm_{user_id}_{order_id}"),
            InlineKeyboardButton(text="❌ Rad etish", callback_data=f"admin_reject_{user_id}_{order_id}"),
        ]
    ])

# /start komandasi
@dp.message(CommandStart())
async def start(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "🌟 <b>KHODJIPROGSM</b> ga xush kelibsiz!\n\n"
        "Professional GSM xizmatlar:\n"
        "• iCloud Unlock\n"
        "• Samsung FRP\n"
        "• MDM Bypass\n"
        "• Network Unlock\n"
        "• Firmware Repair\n"
        "• IMEI Check\n\n"
        "Tilni tanlang / Выберите язык / Choose language:",
        reply_markup=lang_keyboard(),
        parse_mode="HTML"
    )

# Til tanlash
@dp.callback_query(F.data.startswith("lang_"))
async def choose_lang(callback: CallbackQuery, state: FSMContext):
    lang = callback.data.split("_")[1]
    await state.update_data(lang=lang)

    texts = {
        "uz": "Xizmatni tanlang 👇",
        "ru": "Выберите услугу 👇",
        "en": "Choose a service 👇"
    }

    await callback.message.edit_text(
        f"✅ Til tanlandi!\n\n<b>{texts.get(lang, texts['uz'])}</b>",
        reply_markup=services_keyboard(),
        parse_mode="HTML"
    )

# Bosh sahifa
@dp.callback_query(F.data == "home")
async def go_home(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text(
        "🌟 <b>KHODJIPROGSM</b>\n\nXizmatni tanlang:",
        reply_markup=services_keyboard(),
        parse_mode="HTML"
    )

# Xizmat tanlash
@dp.callback_query(F.data.startswith("svc_"))
async def choose_service(callback: CallbackQuery, state: FSMContext):
    svc_key = callback.data.replace("svc_", "")
    svc = SERVICES.get(svc_key)

    if not svc:
        await callback.answer("Xizmat topilmadi!")
        return

    await state.update_data(service_key=svc_key, service_name=svc["name"])
    await state.set_state(OrderState.entering_imei)

    await callback.message.edit_text(
        f"<b>{svc['name']}</b>\n"
        f"📋 {svc['desc']}\n"
        f"💰 Narx: {svc['price']}\n\n"
        f"📝 {svc['info']}:",
        parse_mode="HTML"
    )

# IMEI kiritish
@dp.message(OrderState.entering_imei)
async def enter_imei(message: types.Message, state: FSMContext):
    imei = message.text.strip()
    data = await state.get_data()
    svc = SERVICES.get(data.get("service_key", ""))

    order_id = f"ORD{message.from_user.id}{int(asyncio.get_event_loop().time())}"
    await state.update_data(imei=imei, order_id=order_id)

    await message.answer(
        f"✅ <b>Buyurtma tayyor!</b>\n\n"
        f"🔖 Buyurtma: <code>{order_id}</code>\n"
        f"🛠 Xizmat: {svc['name'] if svc else 'N/A'}\n"
        f"📱 Ma'lumot: <code>{imei}</code>\n"
        f"💰 Narx: {svc['price'] if svc else 'N/A'}\n\n"
        f"To'lov usulini tanlang:",
        reply_markup=payment_keyboard(order_id),
        parse_mode="HTML"
    )
    await state.set_state(OrderState.waiting_payment)

# To'lov
@dp.callback_query(F.data.startswith("pay_"))
async def process_payment(callback: CallbackQuery, state: FSMContext):
    parts = callback.data.split("_")
    method = parts[1]
    
    if method == "click":
        await callback.answer("Click ilovasi orqali to'lash...", show_alert=True)
        await callback.message.answer(
            "💳 <b>Click orqali to'lash</b>\n\n"
            "Karta raqami: <code>8600 XXXX XXXX XXXX</code>\n"
            "Miqdor: Xizmat narxiga qarab\n\n"
            "To'lovdan so'ng '✅ To'lov qildim' tugmasini bosing.",
            parse_mode="HTML"
        )
    elif method == "payme":
        await callback.answer("Payme orqali to'lash...", show_alert=True)
        await callback.message.answer(
            "💳 <b>Payme orqali to'lash</b>\n\n"
            "Karta raqami: <code>8600 XXXX XXXX XXXX</code>\n"
            "Miqdor: Xizmat narxiga qarab\n\n"
            "To'lovdan so'ng '✅ To'lov qildim' tugmasini bosing.",
            parse_mode="HTML"
        )

# To'lov qilindi
@dp.callback_query(F.data.startswith("paid_"))
async def payment_done(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    order_id = data.get("order_id", "N/A")
    imei = data.get("imei", "N/A")
    svc_name = data.get("service_name", "N/A")

    await callback.message.edit_text(
        f"⏳ <b>To'lov tekshirilmoqda...</b>\n\n"
        f"Buyurtma: <code>{order_id}</code>\n"
        f"Admin tasdiqlashi kutilmoqda. 1-30 daqiqa ichida javob olasiz.",
        parse_mode="HTML"
    )

    # Admin ga xabar yuborish
    try:
        await bot.send_message(
            ADMIN_ID,
            f"🔔 <b>YANGI BUYURTMA!</b>\n\n"
            f"👤 Mijoz: @{callback.from_user.username or 'N/A'} (ID: {callback.from_user.id})\n"
            f"🔖 Buyurtma: <code>{order_id}</code>\n"
            f"🛠 Xizmat: {svc_name}\n"
            f"📱 Ma'lumot: <code>{imei}</code>\n"
            f"💰 To'lov: Amalga oshirildi (tekshirish kerak)",
            reply_markup=admin_keyboard(callback.from_user.id, order_id),
            parse_mode="HTML"
        )
    except Exception as e:
        logging.error(f"Admin ga xabar yuborishda xato: {e}")

    await state.clear()

# Admin - tasdiqlash
@dp.callback_query(F.data.startswith("admin_confirm_"))
async def admin_confirm(callback: CallbackQuery):
    parts = callback.data.split("_")
    user_id = int(parts[2])
    order_id = parts[3]

    await bot.send_message(
        user_id,
        f"✅ <b>Buyurtmangiz tasdiqlandi!</b>\n\n"
        f"Buyurtma: <code>{order_id}</code>\n"
        f"Xizmat bajarilmoqda... Natija 1-24 soat ichida yuboriladi.\n\n"
        f"Savollar uchun: @khodjipro",
        parse_mode="HTML"
    )
    await callback.message.edit_text(
        callback.message.text + "\n\n✅ TASDIQLANDI",
        parse_mode="HTML"
    )
    await callback.answer("Tasdiqlandi!")

# Admin - rad etish
@dp.callback_query(F.data.startswith("admin_reject_"))
async def admin_reject(callback: CallbackQuery):
    parts = callback.data.split("_")
    user_id = int(parts[2])
    order_id = parts[3]

    await bot.send_message(
        user_id,
        f"❌ <b>Buyurtma rad etildi.</b>\n\n"
        f"Buyurtma: <code>{order_id}</code>\n"
        f"To'lov qaytariladi. Savollar uchun: @khodjipro",
        parse_mode="HTML"
    )
    await callback.message.edit_text(
        callback.message.text + "\n\n❌ RAD ETILDI",
        parse_mode="HTML"
    )
    await callback.answer("Rad etildi!")

# Bekor qilish
@dp.callback_query(F.data == "cancel")
async def cancel_order(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text(
        "❌ Buyurtma bekor qilindi.\n\n"
        "Qaytadan boshlash uchun /start yozing."
    )

# Botni ishga tushirish
async def main():
    print("✅ KHODJIPROGSM Bot ishga tushdi!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
