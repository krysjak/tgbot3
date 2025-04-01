import logging
import asyncio
import random
from datetime import datetime
from aiogram import Bot, Dispatcher, Router, F
from aiogram.types import Message, CallbackQuery, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, \
    InlineKeyboardButton
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from config import BOT_TOKEN
from data import (
    biography_text,
    facts_list,
    audio_archive,
    quiz_questions,
    memorial_places,
    quotes,
    timeline_events,
    photo_archive,
    operas,
    quest_stages,
    museum_exhibits,
    museum_facts,
    museum_directions,
    museum_events
)

# Configure logging
logging.basicConfig(level=logging.INFO)

# Initialize bot and dispatcher
bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)
router = Router()


# Define state classes
class QuizStates(StatesGroup):
    waiting_for_answer = State()


class QuestStates(StatesGroup):
    current_stage = State()


# Start command
@router.message(CommandStart())
async def cmd_start(message: Message):
    kb = [
        [KeyboardButton(text="📖 Біографія"), KeyboardButton(text="🎭 Цікаві факти")],
        [KeyboardButton(text="🎧 Аудіоархів"), KeyboardButton(text="❓ Вікторина")],
        [KeyboardButton(text="🗺 Карта пам'ятних місць"), KeyboardButton(text="📝 Цитати")],
        [KeyboardButton(text="📅 Хронологія життя"), KeyboardButton(text="📸 Фотоархів")],
        [KeyboardButton(text="🎶 Опера дня")],
        [KeyboardButton(text="🏛 Будинок-музей")]
    ]
    keyboard = ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

    await message.answer(
        f"Вітаю! Я бот, присвячений життю та творчості видатної української оперної співачки Соломії Крушельницької.\n\n"
        f"Оберіть розділ, який вас цікавить:",
        reply_markup=keyboard
    )


# Biography handler
@router.message(F.text == "📖 Біографія")
async def biography_handler(message: Message):
    await message.answer(biography_text)


# Facts handler
@router.message(F.text == "🎭 Цікаві факти")
async def facts_handler(message: Message):
    fact = random.choice(facts_list)

    # Create keyboard for "Next fact" button
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="Наступний факт", callback_data="next_fact")]]
    )

    await message.answer(fact, reply_markup=keyboard)


# main.py - updated next_fact_callback handler
    from aiogram.exceptions import TelegramBadRequest

    @router.callback_query(F.data == "next_fact")
    async def next_fact_callback(callback: CallbackQuery):
        fact = random.choice(facts_list)
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="Наступний факт", callback_data="next_fact")]]
        )
        try:
            await callback.message.edit_text(fact, reply_markup=keyboard)
        except TelegramBadRequest as exc:
            if "message is not modified" in str(exc):
                await callback.answer("This fact is already displayed.", show_alert=True)
            else:
                raise
        await callback.answer()


# Audio archive handler
@router.message(F.text == "🎧 Аудіоархів")
async def audio_handler(message: Message):
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=audio["title"], callback_data=f"audio_{i}")]
            for i, audio in enumerate(audio_archive)
        ]
    )

    await message.answer("Оберіть запис для прослуховування:", reply_markup=keyboard)


# main.py - updated audio_callback handler
from aiogram.types import FSInputFile

@router.callback_query(F.data.startswith("audio_"))
async def audio_callback(callback: CallbackQuery):
    audio_index = int(callback.data.split("_")[1])
    audio = audio_archive[audio_index]
    local_audio_path = audio.get("local_path")

    if local_audio_path:
        await bot.send_audio(
            chat_id=callback.from_user.id,
            audio=FSInputFile(local_audio_path),
            caption=f"Title: {audio['title']}\nDescription: {audio['description']}"
        )
    else:
        await bot.send_audio(
            chat_id=callback.from_user.id,
            audio=audio["file_id"],
            caption=f"Title: {audio['title']}\nDescription: {audio['description']}"
        )
    await callback.answer()

# in main.py

@router.message(F.text == "❓ Вікторина")
async def quiz_handler(message: Message, state: FSMContext):
    question_index = random.randrange(len(quiz_questions))
    question = quiz_questions[question_index]

    # Save question data for checking the answer later
    await state.set_state(QuizStates.waiting_for_answer)
    await state.update_data(
        current_question_index=question_index,
        correct_answer=question["correct_answer"]
    )

    # Create keyboard with answer options
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=option, callback_data=f"quiz_answer_{i}")]
            for i, option in enumerate(question["options"])
        ]
    )

    await message.answer(f"Питання: {question['question']}", reply_markup=keyboard)


@router.callback_query(F.data.startswith("quiz_answer_"), QuizStates.waiting_for_answer)
async def quiz_answer_callback(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    correct_answer = data["correct_answer"]
    question_index = data["current_question_index"]
    current_question = quiz_questions[question_index]

    answer_index = int(callback.data.split("_")[2])
    selected_answer = current_question["options"][answer_index]

    if selected_answer == correct_answer:
        await callback.message.answer("✅ Правильно! Молодець!")
    else:
        await callback.message.answer(f"❌ Неправильно. Правильна відповідь: {correct_answer}")

    # Reset state
    await state.clear()

    # Offer another question
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="Ще питання", callback_data="more_quiz")]]
    )
    await callback.message.answer("Бажаєте продовжити вікторину?", reply_markup=keyboard)
    await callback.answer()


@router.callback_query(F.data == "more_quiz")
async def more_quiz_callback(callback: CallbackQuery, state: FSMContext):
    await quiz_handler(callback.message, state)
    await callback.answer()


# Memorial places handler
@router.message(F.text == "🗺 Карта пам'ятних місць")
async def places_handler(message: Message):
    text = "Пам'ятні місця, пов'язані з Соломією Крушельницькою:\n\n"

    for place in memorial_places:
        text += f"📍 {place['name']}\n"
        text += f"    {place['description']}\n"
        text += f"    Адреса: {place['address']}\n\n"

    await message.answer(text)


# Quotes handler
@router.message(F.text == "📝 Цитати")
async def quotes_handler(message: Message):
    quote = random.choice(quotes)

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="Наступна цитата", callback_data="next_quote")]]
    )

    await message.answer(f"«{quote['text']}»\n\n— {quote['source']}", reply_markup=keyboard)


@router.callback_query(F.data == "next_quote")
async def next_quote_callback(callback: CallbackQuery):
    quote = random.choice(quotes)
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="Наступна цитата", callback_data="next_quote")]]
    )

    await callback.message.edit_text(f"«{quote['text']}»\n\n— {quote['source']}", reply_markup=keyboard)
    await callback.answer()


# Timeline handler
@router.message(F.text == "📅 Хронологія життя")
async def timeline_handler(message: Message):
    text = "Хронологія життя Соломії Крушельницької:\n\n"

    for event in timeline_events:
        text += f"{event['date']}: {event['description']}\n\n"

    await message.answer(text)


# Photo archive handler
@router.message(F.text == "📸 Фотоархів")
async def photo_handler(message: Message):
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=photo["title"], callback_data=f"photo_{i}")]
            for i, photo in enumerate(photo_archive)
        ]
    )

    await message.answer("Оберіть фотографію для перегляду:", reply_markup=keyboard)


# main.py - update photo_callback handler
# main.py - updated photo_callback handler
from aiogram.types import FSInputFile

@router.callback_query(F.data.startswith("photo_"))
async def photo_callback(callback: CallbackQuery):
    photo_index = int(callback.data.split("_")[1])
    photo = photo_archive[photo_index]
    local_photo_path = photo.get("local_path")
    if local_photo_path:
        await bot.send_photo(
            chat_id=callback.from_user.id,
            photo=FSInputFile(local_photo_path),
            caption=f"Назва: {photo['title']}\nОпис: {photo['description']}"
        )
    else:
        await callback.message.answer(
            f"Назва: {photo['title']}\nОпис: {photo['description']}"
        )
    await callback.answer()

# Opera of the day handler
@router.message(F.text == "🎶 Опера дня")
async def opera_handler(message: Message):
    today = datetime.now().strftime("%Y-%m-%d")
    # Use the date to deterministically select an opera for the day
    day_number = sum(int(c) for c in today.replace("-", ""))
    opera_index = day_number % len(operas)

    opera = operas[opera_index]

    text = f"Опера дня: {opera['title']}\n\n"
    text += f"Композитор: {opera['composer']}\n"
    text += f"Роль Соломії Крушельницької: {opera['role']}\n\n"
    text += f"Історія: {opera['history']}\n\n"
    text += f"Цікавий факт: {opera['fact']}"

    await message.answer(text)


# Quest handler
@router.message(F.text == "🕵️ Квест «Подорож Соломії»")
async def quest_handler(message: Message, state: FSMContext):
    # Start the quest from the first stage
    await state.set_state(QuestStates.current_stage)
    await state.update_data(current_stage=0)

    first_stage = quest_stages[0]

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=option, callback_data=f"quest_option_{i}")]
            for i, option in enumerate(first_stage["options"])
        ]
    )

    await message.answer(
        f"Квест «Подорож Соломії» - Етап 1\n\n{first_stage['description']}",
        reply_markup=keyboard
    )


@router.callback_query(F.data.startswith("quest_option_"), QuestStates.current_stage)
async def quest_option_callback(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    current_stage = data["current_stage"]

    option_index = int(callback.data.split("_")[2])
    stage = quest_stages[current_stage]

    if option_index == stage["correct_option"]:
        # Correct answer, move to the next stage
        current_stage += 1

        if current_stage < len(quest_stages):
            # Next stage
            await state.update_data(current_stage=current_stage)
            next_stage = quest_stages[current_stage]

            keyboard = InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text=option, callback_data=f"quest_option_{i}")]
                    for i, option in enumerate(next_stage["options"])
                ]
            )

            await callback.message.answer(
                f"✅ Правильно!\n\nКвест «Подорож Соломії» - Етап {current_stage + 1}\n\n{next_stage['description']}",
                reply_markup=keyboard
            )
        else:
            # Quest completed
            await callback.message.answer(
                "🎉 Вітаємо! Ви успішно завершили квест «Подорож Соломії»!\n\n"
                "Ви прекрасно знаєте життя та творчість видатної української співачки."
            )
            await state.clear()
    else:
        # Wrong answer
        await callback.message.answer(
            f"❌ Неправильна відповідь. {stage['feedback'][option_index]}\n\nСпробуйте ще раз."
        )

    await callback.answer()


# Museum section
@router.message(F.text == "🏛 Будинок-музей")
async def museum_handler(message: Message):
    kb = [
        [KeyboardButton(text="🏠 Факти про будинок")],
        [KeyboardButton(text="📍 Маршрут до музею"), KeyboardButton(text="🎭 Афіша заходів")],
        [KeyboardButton(text="↩️ Назад до головного меню")]
    ]
    keyboard = ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

    await message.answer(
        "Ласкаво просимо до розділу про Будинок-музей Соломії Крушельницької у Львові!\n\n"
        "Оберіть підрозділ для отримання інформації:",
        reply_markup=keyboard
    )





@router.message(F.text == "🏠 Факти про будинок")
async def museum_facts_handler(message: Message):
    text = "Історія та факти про будинок Соломії Крушельницької:\n\n"

    for fact in museum_facts:
        text += f"• {fact}\n\n"

    await message.answer(text)


@router.message(F.text == "📍 Маршрут до музею")
async def museum_directions_handler(message: Message):
    text = "Як дістатися до будинку-музею:\n\n"
    text += f"Адреса: {museum_directions['address']}\n\n"
    text += f"Графік роботи: {museum_directions['hours']}\n\n"
    text += "Маршрут громадським транспортом:\n"

    for route in museum_directions["public_transport"]:
        text += f"• {route}\n"

    text += f"\nКонтактний телефон: {museum_directions['phone']}"

    # Here you would send a location
    # await bot.send_location(
    #     message.from_user.id,
    #     latitude=museum_directions["location"]["latitude"],
    #     longitude=museum_directions["location"]["longitude"]
    # )

    await message.answer(text)


@router.message(F.text == "🎭 Афіша заходів")
async def museum_events_handler(message: Message):
    if not museum_events:
        await message.answer("На даний момент немає запланованих заходів у музеї. Будь ласка, перевірте пізніше.")
        return

    text = "Найближчі події у будинку-музеї Соломії Крушельницької:\n\n"

    for event in museum_events:
        text += f"{event['date']} - {event['title']}\n"
        text += f"{event['description']}\n\n"

    await message.answer(text)


@router.message(F.text == "↩️ Назад до головного меню")
async def back_to_main_menu(message: Message):
    await cmd_start(message)


# Register all handlers
dp.include_router(router)


# Start polling
async def main():
    logging.info("Starting bot")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())