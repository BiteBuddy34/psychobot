import telebot
import pymysql
from telebot import types

TOKEN = "7787046553:AAGL5wvAhfpXyC5fzG5guNCoFMc_ATzWOIw" 
bot = telebot.TeleBot(TOKEN)

print("Бот запущен")

# Словарь для хранения состояний пользователей
user_states = {}

# декоратор для проверки блокировки пользователя
def check_blocked(func):
    def wrapper(message):
        user_id = message.from_user.id
        if is_user_blocked(user_id):
            bot.send_message(user_id, "Ваш аккаунт был заблокирован! Вы не можете пользоваться ботом.")
            return
        return func(message)
    return wrapper

connection = pymysql.connect(
    host='127.0.0.1', 
    user='root',  
    password='1234', 
    database= 'psychobot'
)

try:
    with connection.cursor() as cursor:
        #создание таблицы для учащихся
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS Students(
        StudentID INT AUTO_INCREMENT PRIMARY KEY,
        FirstName VARCHAR(100),
        LastName VARCHAR(100),
        TelegramID VARCHAR(100) UNIQUE
        )
        ''')
        #создание таблицы для психологов
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS Psychologists(
        PsychologistID INT AUTO_INCREMENT PRIMARY KEY,
        FirstName VARCHAR(100),
        LastName VARCHAR(100),
        TelegramID VARCHAR(100) UNIQUE
                       )
                       ''')
        #создание таблицы для администраторов
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS Admins(
        AdminID INT AUTO_INCREMENT PRIMARY KEY,
        FirstName VARCHAR(100),
        LastName VARCHAR(100),
        TelegramID VARCHAR(100) UNIQUE
                       )
                       ''')
        #создание таблицы для контента
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS Content(
        ContentID INT AUTO_INCREMENT PRIMARY KEY,
        ContentData TEXT
        )
        ''')
        #создание таблицы для блокированных пользователей
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS Block(
        blockID INT AUTO_INCREMENT PRIMARY KEY,
        blockuser_id INT UNIQUE
        );
        ''')
        #создание таблицы для анонимных сообщений
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS AnonymousMessages (
        MessageID INT AUTO_INCREMENT PRIMARY KEY,
        StudentID INT,
        PsychologistID INT DEFAULT NULL,
        MessageText TEXT,
        ResponseText TEXT DEFAULT NULL,
        CreatedAt TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        CONSTRAINT fk_student FOREIGN KEY (StudentID) REFERENCES Students(StudentID),
        CONSTRAINT fk_psychologist FOREIGN KEY (PsychologistID) REFERENCES Psychologists(PsychologistID)
        )
        ''')
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS questionnaires (
        id INT AUTO_INCREMENT PRIMARY KEY,
        title VARCHAR(255),
        question TEXT NULL, 
        published BOOLEAN DEFAULT FALSE
        )
        ''')
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS answers (
        id INT AUTO_INCREMENT PRIMARY KEY,
        questionnaire_id INT,
        student_id INT,
        answer TEXT,
        FOREIGN KEY (questionnaire_id) REFERENCES questionnaires(id)
        )
        ''')
        # Создание таблицы для вопросов анкет
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS questions (
        id INT AUTO_INCREMENT PRIMARY KEY,
        questionnaire_id INT,
        question TEXT,
        FOREIGN KEY (questionnaire_id) REFERENCES questionnaires(id)
        )
''')
        connection.commit()
        print("Успешное подключение к БД! Все таблицы инициализированы..")
except Exception as ex:
    print("Ошибка при подключении к БД!")
    print(ex)
 

# Функция добавления пользователя в БД в зависимости от роли
def add_user(first_name, last_name, telegram_id, role):
    try:
        with connection.cursor() as cursor:
            sql_check = f"SELECT * FROM {role} WHERE TelegramID = %s"
            cursor.execute(sql_check, (telegram_id,))
            result = cursor.fetchone()

            if result:
                return "exists", result[1], result[2]  # Возвращаем имя и фамилию

            else:
                sql = f"INSERT INTO {role} (FirstName, LastName, TelegramID) VALUES (%s, %s, %s)"
                cursor.execute(sql, (first_name, last_name, telegram_id))
                connection.commit()
                return "added", first_name, last_name

    except Exception as ex:
        print("Ошибка при добавлении пользователя!")
        print(ex)
        return "error", None, None

    
# Обработчик команды /start
@bot.message_handler(commands=["start"])
@check_blocked
def start_bot(message):
    telegram_id = str(message.chat.id)
    role = None
    user_info = None
 
    try:
        with connection.cursor() as cursor:
            for table in ["Students", "Psychologists", "Admins"]:
                sql_check = f"SELECT FirstName, LastName FROM {table} WHERE TelegramID = %s"
                cursor.execute(sql_check, (telegram_id,))
                result = cursor.fetchone()
                if result:
                    role = table
                    user_info = result
                    break

    except Exception as ex:
        print("Ошибка при проверке пользователя!")
        print(ex)
        bot.send_message(message.chat.id, "Произошла ошибка при обработке. Попробуйте позже.")
        return

    # Если пользователь найден
    if role:
        first_name, last_name = user_info
        bot.send_message(
            message.chat.id,
            f"Добро пожаловать обратно, {first_name} {last_name}! Вы зарегистрированы под ролью {role}.",
            reply_markup=get_role_keyboard(role)
        )
    else:
        keyboard_roles = types.ReplyKeyboardMarkup(resize_keyboard=True)
        keyboard_roles.add(
            types.KeyboardButton("Я ученик"),
            types.KeyboardButton("Я психолог"),
            types.KeyboardButton("Я администратор")
        )
        bot.send_message(
            message.chat.id,
            "Добро пожаловать в Кабинет Школьного Психолога!\nДля продолжения выберите свою роль:",
            reply_markup=keyboard_roles
        )


# Функция для получения клавиатуры в зависимости от роли
def get_role_keyboard(role):
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    if role == "Students":
        keyboard.add("Пройти психологический тест", "Анкеты от психолога", "Получить анонимную помощь", "Контент")
    elif role == "Psychologists":
        keyboard.add("Опубликовать статью", "Ответить на анонимное сообщение", "Опубликовать анкету")
    elif role == "Admins":
        keyboard.add("Заблокировать пользователя", "Разблокировать пользователя")
    return keyboard

#функция для получения клавиатуры учащегося
def get_student_keyboard():
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add("Пройти психологический тест", "Анкеты от психолога", "Получить анонимную помощь", "Контент")
    return keyboard


# Обработчик для ролей
@bot.message_handler(func=lambda message: message.text in ["Я ученик", "Я психолог", "Я администратор"])
def handle_role(message):
    if message.text == "Я ученик":
        user_states[message.chat.id] = "Students"
    elif message.text == "Я психолог":
        user_states[message.chat.id] = "Psychologists"
    elif message.text == "Я администратор":
        user_states[message.chat.id] = "Admins"

    # Запрашиваем имя и фамилию
    bot.send_message(message.chat.id, "Пожалуйста, введите ваше имя и фамилию через пробел.")


# Для обработки регистрации
@bot.message_handler(func=lambda message: isinstance(user_states.get(message.chat.id), str))
def handle_name(message):
    try:
        first_name, last_name = message.text.split()
    except ValueError:
        bot.send_message(message.chat.id, "Пожалуйста, введите имя и фамилию через пробел.")
        return

    if not (first_name.isalpha() and last_name.isalpha()):
        bot.send_message(message.chat.id, "Имя и фамилия должны содержать только буквы. Пожалуйста, попробуйте снова.")
        return

    # Телеграмм айди пользователя
    telegram_id = str(message.chat.id)

    # Получаем роль пользователя
    role = user_states[message.chat.id]

    # Добавляем пользователя в БД и получаем статус
    status, first_name_db, last_name_db = add_user(first_name, last_name, telegram_id, role)

    if status == "exists":
        welcome_message = f"Добро пожаловать обратно, {first_name_db} {last_name_db}! Чем я могу помочь Вам сегодня?"
    elif status == "added":
        welcome_message = f"Добро пожаловать, {first_name} {last_name}! Чем я могу помочь Вам сегодня?"
    else:
        bot.send_message(message.chat.id, "Произошла ошибка при добавлении пользователя.")
        return

    # Удаляем роль из состояния
    user_states.pop(message.chat.id)

    # Создание клавиатуры в зависимости от роли
    bot.send_message(message.chat.id, welcome_message, reply_markup=get_role_keyboard(role))
    


# Вопросы для тестов

tests = {
    "Тест на уровень стресса": [
        "Часто ли вы чувствуете напряжение?",
        "Трудно ли вам расслабиться даже после отдыха?",
        "Бывают ли у вас головные боли из-за стресса?",
        "Чувствуете ли вы себя подавленным?",
        "Сложно ли вам сосредоточиться на задачах?"
    ],

    "Тест на уровень тревожности": [
        "Часто ли вы беспокоитесь о будущем?",
        "Легко ли вас вывести из равновесия?",
        "Чувствуете ли вы себя нервным в новых ситуациях?",
        "Сложно ли вам расслабиться в общественных местах?",
        "Часто ли вы испытываете физические симптомы тревоги (например, потливость)?"
    ],

    "Тест на уровень депрессии": [
        "Чувствуете ли вы себя подавленным большую часть времени?",
        "Потеряли ли вы интерес к вещам, которые раньше приносили радость?",
        "Чувствуете ли вы себя безнадежным?",
        "Сложно ли вам вставать с постели по утрам?",
        "Чувствуете ли вы себя уставшим даже после сна?"
    ]
}


# Обработчик для выбора теста
@bot.message_handler(func=lambda message: message.text == "Пройти психологический тест")
@check_blocked
def choose_test(message):
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    for test_name in tests.keys():
        keyboard.add(test_name)
    bot.send_message(message.chat.id, "Выберите тест:", reply_markup=keyboard)

# Обработчик для начала теста
@bot.message_handler(func=lambda message: message.text in tests.keys())
def start_test(message):
    test_name = message.text
    questions = tests[test_name]
    answers = ["Нет", "Иногда", "Часто"]

    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(*answers)

    question_index = 0
    user_states[message.chat.id] = {"test_name": test_name, "question_index": question_index, "score": 0}
    bot.send_message(message.chat.id, questions[question_index], reply_markup=keyboard)


# Обработчик для ответов на вопросы теста
@bot.message_handler(func=lambda message: message.chat.id in user_states)
def handle_test_question(message):
    test_name = user_states[message.chat.id]["test_name"]
    questions = tests[test_name]
    answers = ["Нет", "Иногда", "Часто"]
    user_answer = message.text


    if user_answer in answers:
        # Обновляем счет в зависимости от ответа
        if user_answer == "Часто":
            user_states[message.chat.id]["score"] += 3
        elif user_answer == "Иногда":
            user_states[message.chat.id]["score"] += 2
        else:  # "Нет"
            user_states[message.chat.id]["score"] += 1


        # Переход к следующему вопросу
        user_states[message.chat.id]["question_index"] += 1

        if user_states[message.chat.id]["question_index"] < len(questions):
            question_index = user_states[message.chat.id]["question_index"]
            bot.send_message(message.chat.id, questions[question_index], reply_markup=types.ReplyKeyboardMarkup(resize_keyboard=True).add(*answers))

        else:
            # Завершение теста и вывод результата
            score = user_states[message.chat.id]["score"]
            result = "Низкий" if score <= 10 else "Средний" if score <= 15 else "Высокий"
            bot.send_message(message.chat.id, f"Ваш уровень: {result}", reply_markup=get_student_keyboard())

            del user_states[message.chat.id]  # Удаляем состояние пользователя после завершения теста


    else:
        # Если ответ не распознан, отправим сообщение об ошибке
        bot.send_message(message.chat.id, "Пожалуйста, выберите один из предложенных вариантов: 'Нет', 'Иногда' или 'Часто'.")


@bot.message_handler(func=lambda message: message.text == "Анкеты от психолога")
@check_blocked
def take_questionnaire(message):
    with connection.cursor() as cursor:
        # Получаем все анкеты
        cursor.execute("SELECT id, title FROM questionnaires")
        questionnaires = cursor.fetchall()
        connection.commit()

    if not questionnaires:
        bot.send_message(message.chat.id, "На данный момент нет доступных анкет!")
    else:
        response_message = "Доступные анкеты:\n"
        for q in questionnaires:
            response_message += f"{q[0]}: {q[1]}\n"  # Формируем сообщение с ID и названием анкеты
        bot.send_message(message.chat.id, response_message + "Введите ID анкеты, чтобы начать.")

        bot.register_next_step_handler(message, process_selected_questionnaire)

def process_selected_questionnaire(message):
    try:
        questionnaire_id = int(message.text)  # Пробуем преобразовать текст в ID анкеты
    except ValueError:
        bot.send_message(message.chat.id, "Пожалуйста, введите корректный ID анкеты.")
        return

    with connection.cursor() as cursor:
        cursor.execute("SELECT id, question FROM questions WHERE questionnaire_id = %s", (questionnaire_id,))
        questionnaire = cursor.fetchall()
        connection.commit()

    if questionnaire:
        # Сохраняем выбранную анкету в состоянии пользователя
        user_states[message.chat.id] = {
            "questionnaire_id": questionnaire_id,
            "current_question_index": 0,
            "questionnaire": questionnaire  # Сохраняем саму анкету
        }
        send_question(message.chat.id, questionnaire)
    else:
        bot.send_message(message.chat.id, "Анкета не найдена.")

def send_question(chat_id, questionnaire):
    current_index = user_states[chat_id]["current_question_index"]

    if current_index < len(questionnaire):
        question = questionnaire[current_index][1]  # Получаем текст вопроса

        # Проверка на пустой вопрос
        if not question:
            bot.send_message(chat_id, "Вопрос отсутствует. Пожалуйста, проверьте анкету.")
            return

        bot.send_message(chat_id, question)
        bot.register_next_step_handler_by_chat_id(chat_id, process_answer)
    else:
        bot.send_message(chat_id, "Вы ответили на все вопросы анкеты.")
        del user_states[chat_id]  # Удаляем состояние пользователя после завершения

def process_answer(message):
    chat_id = message.chat.id
    questionnaire_id = user_states[chat_id]["questionnaire_id"]  # Получаем ID выбранной анкеты

    # Получаем student_id из базы данных
    with connection.cursor() as cursor:
        cursor.execute("SELECT StudentID FROM Students WHERE TelegramID = %s", (chat_id,))
        student_id = cursor.fetchone()
        
        if student_id is None:
            bot.send_message(chat_id, "Ошибка: пользователь не найден.")
            return
        
        student_id = student_id[0]  # Получаем значение StudentID

        # Сохранение ответа
        cursor.execute("INSERT INTO answers (questionnaire_id, student_id, answer) VALUES (%s, %s, %s)",
                       (questionnaire_id, student_id, message.text))
        connection.commit()

    # Переход к следующему вопросу
    user_states[chat_id]["current_question_index"] += 1
    send_question(chat_id, user_states[chat_id]["questionnaire"])  # Отправляем следующий вопрос



@bot.message_handler(func=lambda message: message.text == "Получить анонимную помощь")
@check_blocked
def anonymous_help(message):
    user_id = message.chat.id #айди пользователя, которому нужна анонимная помощь
    bot.send_message(user_id, "Похоже что вы нуждаетесь в анонимной помощи\n Пришлите анонимное сообщение, и психолог ответит на него")
    bot.register_next_step_handler(message, handle_anon_response)

# функция обработки анонимных обращений
def handle_anon_response(message):
    user_id = message.chat.id
    anon_message_text = message.text

    try:
        with connection.cursor() as cursor:
            sqlInsertAnonMessage = "INSERT INTO AnonymousMessages (StudentID, MessageText) VALUES ((SELECT StudentID FROM Students WHERE TelegramID = %s), %s)"
            cursor.execute(sqlInsertAnonMessage, (user_id, anon_message_text))
            connection.commit()
            bot.send_message(user_id, "Ваше сообщение отправлено, психолог скоро на него ответит")
    except Exception as ex:
        bot.send_message(user_id, f"Произошла ошибка: {ex}\n Попробуйте повторить позже!")


@bot.message_handler(func=lambda message: message.text == "Ответить на анонимное сообщение")
def list_anonymous_messages(message):
    user_id = message.chat.id
    try:
        with connection.cursor() as cursor:
            sql = """
            SELECT MessageID, MessageText FROM AnonymousMessages
            WHERE PsychologistID IS NULL OR PsychologistID = (SELECT PsychologistID FROM Psychologists WHERE TelegramID = %s)
            """
            cursor.execute(sql, (user_id,))
            messages = cursor.fetchall()

            if messages:
                for msg in messages:
                    bot.send_message(user_id, f"Сообщение ID {msg[0]}: {msg[1]}")
                    bot.send_message(user_id, "Введите ответ на это сообщение, указав его ID.")
                bot.register_next_step_handler(message, respond_to_message)
            else:
                bot.send_message(user_id, "Нет новых анонимных сообщений.")
    except Exception as ex:
        bot.send_message(user_id, "Произошла ошибка.")
        print(ex)

def respond_to_message(message):
    try:
        response = message.text.split(" ", 1)
        message_id, response_text = int(response[0]), response[1]

        user_id = message.chat.id
        with connection.cursor() as cursor:
            sql = """
            UPDATE AnonymousMessages
            SET ResponseText = %s, PsychologistID = (SELECT PsychologistID FROM Psychologists WHERE TelegramID = %s)
            WHERE MessageID = %s
            """
            cursor.execute(sql, (response_text, user_id, message_id))
            connection.commit()

        bot.send_message(user_id, "Ответ отправлен.")
        notify_student(message_id)  # Уведомляем ученика об ответе
    except Exception as ex:
        bot.send_message(message.chat.id, "Произошла ошибка. Убедитесь, что вы правильно указали ID сообщения и текст ответа.")
        print(ex)


# Уведомление ученика об ответе психолога
def notify_student(message_id):
    try:
        with connection.cursor() as cursor:
            sql = """
            SELECT s.TelegramID, am.ResponseText
            FROM AnonymousMessages am
            JOIN Students s ON am.StudentID = s.StudentID
            WHERE am.MessageID = %s
            """
            cursor.execute(sql, (message_id,))
            student_data = cursor.fetchone()

            if student_data:
                student_id, response_text = student_data
                bot.send_message(student_id, f"Психолог ответил на ваше сообщение:\n{response_text}")
    except Exception as ex:
        print(ex)


# Обработчик для показа контента
@bot.message_handler(func=lambda message: message.text == "Контент")
@check_blocked
def show_content(message):
    with connection.cursor() as cursor:
        sql_getContent = "SELECT * FROM Content"
        cursor.execute(sql_getContent)
        content = cursor.fetchall()
        
        if content:
            response_message = "Вот ваш контент на сегодня:\n\n"
            for item in content:
                # item[0] - это ID, а item[1] - это текст контента
                content_text = item[1]
                if content_text:  # Проверяем, что содержание не None и не пустое
                    response_message += f"ID: {item[0]}\nСодержание: {content_text}\n"
                    response_message += "--------------------\n"  # Разделитель между записями
            
            if response_message == "Вот ваш контент на сегодня:\n\n":
                response_message = "На сегодня контента нет."
                
            bot.send_message(message.chat.id, response_message)
        else:
            bot.send_message(message.chat.id, "На сегодня контента нету и точка.")



@bot.message_handler(func=lambda message: message.text == 'Опубликовать статью')
def start_article(message):
    bot.send_message(message.chat.id, "Пожалуйста, введите содержание статьи:")
    bot.register_next_step_handler(message, receive_message)
    
def receive_message(message):
        # Психолог вводит содержимое статьи
        article_content = message.text

        with connection.cursor() as cursor:
            sql_inputContent = "INSERT INTO Content (ContentData) VALUES (%s)"
            cursor.execute(sql_inputContent, (article_content,))
            connection.commit()

        bot.send_message(message.chat.id, "Статья успешно опубликована!")

current_questionnaire = []
question_count = 0
current_question_index = 0  # Индекс текущего вопроса
questionnaire_title = ""  # Название анкеты

@bot.message_handler(func=lambda message: message.text == "Опубликовать анкету")
def posting_anket(message):
    bot.send_message(message.chat.id, "Введите название анкеты:")
    bot.register_next_step_handler(message, process_questionnaire_title)

def process_questionnaire_title(message):
    global questionnaire_title
    questionnaire_title = message.text  # Сохраняем название анкеты
    bot.send_message(message.chat.id, "Сколько вопросов будет в анкете?")
    bot.register_next_step_handler(message, process_question_count)

def process_question_count(message):
    global question_count, current_question_index
    try:
        question_count = int(message.text)
        current_questionnaire.clear()
        current_question_index = 0  # Сброс индекса
        bot.send_message(message.chat.id, f"Введите вопрос {current_question_index + 1} из {question_count}:")
        bot.register_next_step_handler(message, process_question)
    except ValueError:
        bot.send_message(message.chat.id, "Пожалуйста, введите число.")
        bot.register_next_step_handler(message, process_question_count)

def process_question(message):
    global current_question_index
    current_questionnaire.append(message.text)
    current_question_index += 1  # Увеличиваем индекс на 1

    if current_question_index < question_count:
        bot.send_message(message.chat.id, f"Введите вопрос {current_question_index + 1} из {question_count}:")
        bot.register_next_step_handler(message, process_question)
    else:
        with connection.cursor() as cursor:
            # Сохраняем название анкеты и вопросы в базе данных
            cursor.execute("INSERT INTO questionnaires (title) VALUES (%s)", (questionnaire_title,))
            questionnaire_id = cursor.lastrowid  # Получаем ID последней вставленной записи
            for question in current_questionnaire:
                cursor.execute("INSERT INTO questions (questionnaire_id, question) VALUES (%s, %s)", (questionnaire_id, question))
        connection.commit()
        bot.send_message(message.chat.id, "Анкета опубликована!")


# Блокировка пользователя
@bot.message_handler(func=lambda message: message.text == 'Заблокировать пользователя')
def block_user(message):
    bot.send_message(message.chat.id, "Похоже, кто-то нарушает правила пользования ботом..")
    bot.send_message(message.chat.id, "Введите ID нарушителя, которого хотите заблокировать: ")

    bot.register_next_step_handler(message, block)

#логика блокировки пользователя
def block(message):
    try:
        idblockuser = int(message.text)  # переменная хранит id пользователя, которого нужно заблокировать
    except ValueError:
        bot.send_message(message.chat.id, "Пожалуйста, введите ID пользователя корректно!")
        return

    with connection.cursor() as cursor:
        # Проверяем, заблокирован ли уже пользователь
        sql_checkBlockedUser  = "SELECT blockuser_id FROM Block WHERE blockuser_id = %s"
        cursor.execute(sql_checkBlockedUser , (idblockuser,))
        if cursor.fetchone() is not None:
            bot.send_message(message.chat.id, f"Пользователь с ID: {idblockuser} уже заблокирован!")
            return 

        # Если пользователь не заблокирован, выполняем блокировку
        try:
            sql_inputIDBlockUser  = "INSERT INTO Block (blockuser_id) VALUES (%s)"
            cursor.execute(sql_inputIDBlockUser , (idblockuser,))
            connection.commit()
            bot.send_message(message.chat.id, f"Пользователь с ID: {idblockuser} был заблокирован.")
        except Exception as e:
            bot.send_message(message.chat.id, "Произошла ошибка при блокировке пользователя.")
            bot.send_message(message.chat.id, f"Ошибка: {e}")  # Отправляем сообщение с ошибкой

    bot.send_message(message.chat.id, f"Пользователь с ID: {idblockuser} был заблокирован")


# проверка, заблокирован ли пользователь
def is_user_blocked(user_id):
    with connection.cursor() as cursor:
        sql_checkBlockedUser  = "SELECT blockuser_id FROM Block WHERE blockuser_id = %s"
        cursor.execute(sql_checkBlockedUser , (user_id,))
        result = cursor.fetchone()  # Получаем результат запроса
        return result is not None  # Если результат не None, значит пользователь заблокирован

# Разблокировка пользователя
@bot.message_handler(func=lambda message: message.text == 'Разблокировать пользователя')
def unblock_user(message):
    bot.send_message(message.chat.id, "Введите ID пользователя, которого хотите разблокировать: ")
    bot.register_next_step_handler(message, remove_block)

# логика разблокировки пользователей
def remove_block(message):
    try:
        unblockUserID = int(message.text) #id пользователя которого нужно разблокировать
    except ValueError:
        bot.send_message(message.chat.id, "Пожалуйста, введите корректный ID пользователя!")
        return

    with connection.cursor() as cursor:
        sql_removeBlockUser = "DELETE FROM Block WHERE blockuser_id = %s"
        try:
            cursor.execute(sql_removeBlockUser, (unblockUserID,))
            connection.commit()
            if cursor.rowcount > 0:
                bot.send_message(message.chat.id, f"Пользователь с ID: {unblockUserID} был разблокирован.")
            else:
                bot.send_message(message.chat.id, f"Пользователь с ID: {unblockUserID} не найден в списке заблокированных!")

        except Exception as e:
            bot.send_message(message.chat.id, "Произошла ошибка при разблокировке пользователя.")
            print(f"Ошибка: {e}")  # Логируем ошибку для отладки


@bot.message_handler(func=lambda message: message.text == "Список заблокированных пользователей")
def block_users(message):
    bot.send_message(message.chat.id, "Вот список заблокированных пользователей: ")
    
    bot.register_next_step_handler(message, show_block_users)

def show_block_users(message):
    with connection.cursor() as cursor:
        sql_BlockUsers = "SELECT * FROM Block"
        cursor.execute(sql_BlockUsers)
        block_users = cursor.fetchall()
        connection.commit()

    if block_users:
        response = "Заблокированные пользователи:\n"
        for user in block_users:
            response += f"ID: {user[0]}"
    else:
        response = "Нет заблокированных пользователей"

    bot.send_message(message.chat.id, response)



bot.infinity_polling()
connection.close()