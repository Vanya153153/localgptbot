from telebot import TeleBot
from telebot.types import ReplyKeyboardMarkup, KeyboardButton
import logging
from GPT import GPT
from database import *
from peremen import *

bot = TeleBot(API)



# Словарик для хранения задач пользователей и ответов GPT
users_history = {}

#Формат логов
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    filename="log.txt",
    filemode="w",
)

# Функция для создания клавиатуры с нужными кнопочками
def create_keyboard(buttons_list):
    logging.info("Создание разных кнопок")
    keyboard = ReplyKeyboardMarkup(row_width=2, resize_keyboard=True, one_time_keyboard=True)
    keyboard.add(*buttons_list)
    return keyboard


# Приветственное сообщение /start
@bot.message_handler(commands=['start'])
def start(message):
    logging.info("Отправка приветственного сообщения")
    user_name = message.from_user.first_name
    user_id = message.from_user.id
    bot.send_message(message.chat.id,
                     text=f"Привет, {user_name}! Я бот-помощник для решения задач по программированию на python и математике!\n"
                          f"Ты можешь прислать условие задачи, а я постараюсь её решить.\n"
                          "Иногда ответы получаются слишком длинными - в этом случае ты можешь попросить продолжить.",
                     reply_markup=create_keyboard(["/help_with_math", "/help_with_python", '/help']))

# Команда /help
@bot.message_handler(commands=['help'])
def support(message):
    logging.info("Отправка вспомогательного сообщения")
    bot.send_message(message.from_user.id,
                     text="Чтобы приступить к решению задачи: нажми /help_with_math или /help_with_python, затем "
                          "выбери уровень, и после написать условие",
                     reply_markup=create_keyboard(["/help_with_math", "/help_with_python"]))

@bot.message_handler(commands=['help_with_math'])
def math(message):
    logging.info("Пользователь выбрал математику")
    logging.info("Отправка сообщения просящего условия для задачи")
    global he
    he = "математике"
    bot.send_message(message.chat.id, "Вы выбрали математику, теперь выберите уровень задачи: ",
                     reply_markup=create_keyboard(["beqinner", "advanced"]))
    bot.register_next_step_handler(message, choise_level)

@bot.message_handler(commands=['help_with_python'])
def python(message):
    logging.info("Пользователь выбрал python")
    logging.info("Отправка сообщения просящего условия для задачи")
    global he
    he = "програмированию на python"
    bot.send_message(message.chat.id, "Вы выбрали программирование на python, теперь выберите уровень для задачи: ",
                     reply_markup=create_keyboard(["beqinner", "advanced"]))
    bot.register_next_step_handler(message, choise_level)


def choise_level(message):
    logging.info("Отправка сообщения просящего условия для задачи")
    global chl
    if message.text == "beqinner":
        chl = 'начальном'
        bot.send_message(message.chat.id, "Напиши условие новой задачи:")
        bot.register_next_step_handler(message, get_promt)
    elif message.text == "advanced":
        chl = "продвинутом"
        bot.send_message(message.chat.id, "Напиши условие новой задачи:")
        bot.register_next_step_handler(message, get_promt)
    else:
        bot.send_message(message.chat.id, "Нужно выбрать уровень - \"beqinner\" или \"advanced\"",
                         reply_markup=create_keyboard(["beqinner", "advanced"]))
        bot.register_next_step_handler(message, choise_level)

def solve_task(message):
    user_id = message.from_user.first_name
    logging.info("Отправка сообщения повторного сообщения для соствления нового условия задачи")
    bot.send_message(message.chat.id, "Выберите предмет:",
                     reply_markup=create_keyboard(["/help_with_math", "/help_with_python"]))



# Фильтр для обработки кнопочки "Продолжить решение"
def continue_filter(message):
    logging.info("Отправка сообщения просящего условия для задачи")
    button_text = 'Продолжить решение'
    return message.text == button_text


# Получение задачи от пользователя или продолжение решения
@bot.message_handler(func=continue_filter)
def get_promt(message):
    global chl, he
    logging.debug(f"Полученный текст от пользователя: {message.text}")
    user_id = message.from_user.id
    if message.content_type != "text":
        logging.warning("Получено пустое текстовое сообщение")
        bot.send_message(user_id, "Необходимо отправить именно текстовое сообщение")
        bot.register_next_step_handler(message, get_promt)
        return

    # Получаем текст сообщения от пользователя
    user_request = message.text
    if len(user_request) > MAX_LETTERS:
        logging.warning("Полученое текстовое сообщение превышает максимальную возможную длину")
        bot.send_message(user_id, "Запрос превышает количество символов\nИсправь запрос")
        bot.register_next_step_handler(message, get_promt)
        return


    if user_id not in users_history or users_history[user_id] == {}:
        logging.info("Сохраняем промт пользователя и начало ответа GPT в словарик users_history")
        users_history[user_id] = {
            'system_content': f"Ты - дружелюбный помощник для решения задач по {he}. Давай ответ с кратким решением на {chl} уровне на русском языке",
            'user_content': user_request,
            'assistant_content': "Решим задачу по шагам: "

        }

    logging.info(f"Создаём запрос")
    promt = GPT().make_promt(users_history[user_id])
    resp = GPT().send_request(promt)
    logging.info(f"Проверяем есть ли пользователь в базе данных")
    if len(str(is_value_in_table("users", "user_id", user_id))) != 0:
        logging.info(f"Если есть, то удаляем его чтобы для каждого пользователя было только последняя и единственная запись")
        delete_user(user_id)
    answer = ""
    logging.info(f"Проверяем код")
    answer = GPT().process_resp(resp)
    logging.info(f"Создаём лист из значений и добавляем его в базу данных")
    list_for_db = [user_id, he, chl, user_request, answer[1]]
    insert_row(list_for_db)

    logging.debug(f"Прибавляем ответ в users_history[user_id]['assistant_content'] для будующей команды Продолжить")
    users_history[user_id]['assistant_content'] += str(answer)
    logging.info(f"Отправляем полученный ответ пользователю")
    bot.send_message(user_id, users_history[user_id]['assistant_content'],
                     reply_markup=create_keyboard(["Продолжить решение", "Завершить решение"]))

def end_filter(message):
    button_text = 'Завершить решение'
    return message.text == button_text


@bot.message_handler(content_types=['text'], func=end_filter)
def end_task(message):
    user_id = message.from_user.id
    bot.send_message(user_id, "Текущие решение завершено")
    users_history[user_id] = {}
    solve_task(message)
    if (user_id not in users_history or users_history[user_id] == {}) and message.text == "/Продолжить решение":
        bot.send_message(user_id, "Чтобы продолжить решение, сначала нужно отправить текст задачи")
        bot.send_message(user_id, "Напиши условие новой задачи:")
        bot.register_next_step_handler(message, get_promt)
        return

@bot.message_handler(commands=['debug'])
def send_logs(message):
    logging.info("Выдаём логи")
    with open("log.txt", "rb") as f:
        bot.send_document(message.chat.id, f)


@bot.message_handler(content_types=['text'])
def another_task(message):
    user_id = message.from_user.id
    logging.info("Бот реагирует на сообщение не являющеся командой")
    bot.send_message(user_id, 'Я не знаю что это значит, что я могу можно через команду /help')



if __name__ == "__main__":
    logging.info("Бот запущен")
    bot.infinity_polling()