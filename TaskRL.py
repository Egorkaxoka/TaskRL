
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardRemove
import asyncio
from datetime import datetime

TOKEN = "8182259593:AAE79k5zKIORY4yKi_Sou4Lil3vE7tHWJvs"
EXECUTOR_ID = 609535548  # ID исполнителя

bot = Bot(token=TOKEN)
dp = Dispatcher()

task_counter = 1
executor_tasks = {}
customer_tasks = {}

class TaskForm(StatesGroup):
    choosing_task_type = State()
    choosing_priority = State()
    entering_task = State()
    entering_workload = State()  # Только для КП
    entering_deadline = State()
    confirming_task = State()

# Кнопки для выбора типа задачи
task_type_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📊 КП"), KeyboardButton(text="📄 ОТЧЁТ")],
        [KeyboardButton(text="✉️ ПИСЬМО"), KeyboardButton(text="🔧 ДРУГОЕ")]
    ], resize_keyboard=True
)

# Кнопки для выбора приоритета
priority_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="⬇️ Низкий"), KeyboardButton(text="🔹 Средний")],
        [KeyboardButton(text="🔺 Высокий"), KeyboardButton(text="🚨 Очень высокий")]
    ], resize_keyboard=True
)

# Кнопки для подтверждения или отмены
confirm_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="✅ Отправить"), KeyboardButton(text="❌ Отмена")]
    ], resize_keyboard=True
)

# Кнопка для пропуска дедлайна
skip_deadline_kb = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text="⏭ Пропустить")]],
    resize_keyboard=True
)

# Кнопки для заказчика
customer_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="➕ Создать задачу"), KeyboardButton(text="📋 Мои задачи")]
    ], resize_keyboard=True
)

priority_map = {
    "⬇️ Низкий": 1,
    "🔹 Средний": 2,
    "🔺 Высокий": 3,
    "🚨 Очень высокий": 4
}

@dp.message(Command("start"))
async def start_command(message: types.Message):
    if message.from_user.id == EXECUTOR_ID:
        await message.answer("Привет, исполнитель!", reply_markup=ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="📋 Мои задачи")]], resize_keyboard=True))
    else:
        await message.answer("Привет, заказчик!", reply_markup=customer_kb)

@dp.message(lambda message: message.text == "➕ Создать задачу")
async def create_task(message: types.Message, state: FSMContext):
    await state.set_state(TaskForm.choosing_task_type)
    await message.answer("Выберите тип задачи:", reply_markup=task_type_kb)

@dp.message(TaskForm.choosing_task_type)
async def choose_task_type(message: types.Message, state: FSMContext):
    await state.update_data(task_type=message.text)
    await state.set_state(TaskForm.choosing_priority)
    await message.answer("Выберите приоритет задачи:", reply_markup=priority_kb)

@dp.message(TaskForm.choosing_priority)
async def choose_priority(message: types.Message, state: FSMContext):
    await state.update_data(priority=message.text)
    await state.set_state(TaskForm.entering_task)
    await message.answer("Введите описание задачи:", reply_markup=ReplyKeyboardRemove())

@dp.message(TaskForm.entering_task)
async def enter_task(message: types.Message, state: FSMContext):
    await state.update_data(task_text=message.text)
    data = await state.get_data()
    
    if data["task_type"] == "📊 КП":
        await state.set_state(TaskForm.entering_workload)
        await message.answer("Введите объем работы:")
    else:
        await state.set_state(TaskForm.entering_deadline)
        await message.answer("Введите дедлайн задачи (в формате ДД.ММ.ГГГГ) или нажмите 'Пропустить':", reply_markup=skip_deadline_kb)


@dp.message(TaskForm.entering_workload)
async def enter_workload(message: types.Message, state: FSMContext):
    await state.update_data(workload=message.text)
    await state.set_state(TaskForm.entering_deadline)
    await message.answer("Введите дедлайн задачи (в формате ДД.ММ.ГГГГ):")

@dp.message(TaskForm.entering_deadline)
async def enter_deadline(message: types.Message, state: FSMContext):
    if message.text == "⏭ Пропустить":
        await state.update_data(deadline=None)  # Записываем дедлайн как None
    else:
        try:
            deadline = datetime.strptime(message.text, "%d.%m.%Y")
            await state.update_data(deadline=deadline)
        except ValueError:
            await message.answer("❌ Неверный формат дедлайна. Введите дату в формате ДД.ММ.ГГГГ или нажмите 'Пропустить'.")
            return
    
    await state.set_state(TaskForm.confirming_task)
    await send_task_summary(message, state)


async def send_task_summary(message: types.Message, state: FSMContext):
    data = await state.get_data()
    task_summary = (
        f"📌 *Ваша задача:*\n"
        f"**Тип:** {data['task_type']}\n"
        f"**Приоритет:** {data['priority']}\n"
        f"**Описание:** {data['task_text']}\n"
    )

    if "workload" in data:
        task_summary += f"**Объем работы:** {data['workload']}\n"
    if data.get("deadline"):
        task_summary += f"**Дедлайн:** {data['deadline'].strftime('%d.%m.%Y')}\n"
    else:
        task_summary += "**Дедлайн:** ❌ Не указан\n"

    await message.answer(task_summary, parse_mode="Markdown")
    await message.answer("Подтвердите отправку задачи:", reply_markup=confirm_kb)


@dp.message(lambda message: message.text == "✅ Отправить")
async def confirm_task(message: types.Message, state: FSMContext):
    global task_counter
    data = await state.get_data()
    task_id = str(task_counter)

    task_summary = (
        f"📌 *Задача #{task_id}:*\n"
        f"👤 **Заказчик:** {message.from_user.full_name}\n"
        f"**Тип:** {data['task_type']}\n"
        f"**Приоритет:** {data['priority']}\n"
        f"**Описание:** {data['task_text']}\n"
    )

    if "workload" in data:
        task_summary += f"**Объем работы:** {data['workload']}\n"
    
    # Проверяем, есть ли дедлайн
    if data.get("deadline"):
        task_summary += f"**Дедлайн:** {data['deadline'].strftime('%d.%m.%Y')}\n"
    else:
        task_summary += "**Дедлайн:** ❌ Не указан\n"

    executor_tasks.setdefault(EXECUTOR_ID, []).append(
        (task_id, message.from_user.id, task_summary, priority_map[data["priority"]], data.get("deadline"))
    )

    await message.answer("✅ Задача отправлена исполнителю!", parse_mode="Markdown", reply_markup=customer_kb)
    await bot.send_message(EXECUTOR_ID, f"📢 *Новая задача для вас!*\n{task_summary}", parse_mode="Markdown")

    task_counter += 1
    await state.clear()


@dp.message(lambda message: message.text == "❌ Отмена")
async def cancel_task(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("❌ Задача отменена.", reply_markup=customer_kb)



@dp.message(lambda message: message.text == "📋 Мои задачи")
async def show_tasks(message: types.Message):
    if message.from_user.id == EXECUTOR_ID:  # Исполнитель видит все задачи
        tasks = executor_tasks.get(EXECUTOR_ID, [])
    else:  # Заказчик видит только свои задачи
        tasks = [task for task in executor_tasks.get(EXECUTOR_ID, []) if task[1] == message.from_user.id]

    if not tasks:
        await message.answer("📭 У вас нет активных задач.")
        return

    tasks = sorted(tasks, key=lambda x: x[3], reverse=True)  # Сортировка по приоритету

    for task_id, user_id, task_text, priority, deadline in tasks:
        if message.from_user.id == EXECUTOR_ID:
            task_kb = InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text="✅ Выполнена", callback_data=f"done_{task_id}_{user_id}")],
                    [InlineKeyboardButton(text="❌ Отказ", callback_data=f"reject_{task_id}_{user_id}")]
                ]
            )
        else:
            task_kb = InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text="❌ Отказ", callback_data=f"reject_{task_id}_{user_id}")]
                ]
            )

        await message.answer(task_text, parse_mode="Markdown", reply_markup=task_kb)

@dp.callback_query(lambda callback: callback.data.startswith("done_") or callback.data.startswith("reject_"))
async def handle_task_action(callback: types.CallbackQuery):
    data_parts = callback.data.split("_")
    action, task_id, user_id = data_parts[0], data_parts[1], int(data_parts[2])

    user_tasks = executor_tasks.get(EXECUTOR_ID, [])
    task = next((t for t in user_tasks if t[0] == task_id), None)

    if not task:
        await callback.answer("❌ Задача уже обработана.")
        return

    # Удаляем задачу из списка исполнителя
    executor_tasks[EXECUTOR_ID] = [t for t in user_tasks if t[0] != task_id]

    if callback.from_user.id == EXECUTOR_ID:  # Исполнитель выполняет или отклоняет задачу
        if action == "done":
            await bot.send_message(user_id, f"✅ Ваша задача #{task_id} выполнена!")
            await callback.message.answer(f"✅ Задача #{task_id} выполнена!")
        else:
            await bot.send_message(user_id, f"❌ Ваша задача #{task_id} была отклонена исполнителем.")
            await callback.message.answer(f"❌ Задача #{task_id} отклонена!")

    else:  # Заказчик отменяет задачу
        await bot.send_message(EXECUTOR_ID, f"⚠️ Задача #{task_id} была отменена заказчиком.")
        await callback.message.answer(f"🚫 Вы отменили задачу #{task_id}.")

    await callback.answer()

async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
