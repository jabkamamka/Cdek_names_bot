import telebot
import requests
import sqlite3

API_TOKEN = '7246772852:AAEu1tZnBGw5mXHDJ8nskWSqud9AUqOLAJ8'
CDEK_AUTH_URL = 'https://api.cdek.ru/v2/oauth/token'
CDEK_CITY_URL = 'https://api.cdek.ru/v2/location/cities'
CDEK_PVZ_URL = 'https://api.cdek.ru/v2/deliverypoints'
CDEK_CLIENT_ID = 'Do41WL6PEhYlQojaH0MfueYDHpiukiMR'
CDEK_CLIENT_SECRET = 'kaWV5VkdNyWrJmWIvgvvePuGjPqzaX1Y'
user_ids = set()  # Множество для хранения ID всех пользователей
admin_id = 1543492175  # Замените на ваш ID (узнайте его через бота)

# Инициализация базы данных
conn = sqlite3.connect('users.db', check_same_thread=False)
cursor = conn.cursor()
cursor.execute('''CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY)''')
conn.commit()

# Функция для добавления пользователя в базу данных
def add_user(user_id):
    cursor.execute('INSERT OR IGNORE INTO users (id) VALUES (?)', (user_id,))
    conn.commit()

# Функция для получения всех ID пользователей
def get_all_users():
    cursor.execute('SELECT id FROM users')
    return [row[0] for row in cursor.fetchall()]


bot = telebot.TeleBot(API_TOKEN)

# Получение токена авторизации
def get_cdek_token():
    response = requests.post(CDEK_AUTH_URL, data={
        'grant_type': 'client_credentials',
        'client_id': CDEK_CLIENT_ID,
        'client_secret': CDEK_CLIENT_SECRET
    })
    response.raise_for_status()
    return response.json().get('access_token')


# Получение кода города
def get_city_code(city_name, token):
    headers = {'Authorization': f'Bearer {token}'}
    params = {'country_codes': 'RU', 'city': city_name}
    response = requests.get(CDEK_CITY_URL, headers=headers, params=params)
    response.raise_for_status()
    cities = response.json()
    if cities:
        return cities[0]['code']  # Возвращаем код первого найденного города
    return None

# Запрос списка ПВЗ
def get_delivery_points(city_code, token):
    headers = {'Authorization': f'Bearer {token}'}
    params = {'city_code': city_code}
    response = requests.get(CDEK_PVZ_URL, headers=headers, params=params)
    response.raise_for_status()
    return response.json()

# Обработчик команды /start
@bot.message_handler(commands=['start'])
def send_welcome(message):
    add_user(message.chat.id)
    bot.reply_to(message, "Привет! Напиши название города, чтобы я нашел пункты выдачи СДЭК.")


# Обработчик команды /send с текстом в одной строке
@bot.message_handler(commands=['send'])
def handle_send(message):
    if message.chat.id == admin_id:
        text_to_send = message.text.partition(' ')[2]  # Получает текст после команды
        if text_to_send:
            user_ids = get_all_users()
            for user_id in user_ids:
                try:
                    bot.send_message(user_id, text_to_send)
                except Exception as e:
                    print(f"Ошибка при отправке пользователю {user_id}: {e}")
            bot.reply_to(message, "Рассылка завершена.")
        else:
            bot.reply_to(message, "Пожалуйста, укажите текст для рассылки после команды /send.")
    else:
        bot.reply_to(message, "У вас нет прав для выполнения этой команды.")


# Обработчик команды /stats для администратора
@bot.message_handler(commands=['stats'])
def handle_stats(message):
    if message.chat.id == admin_id:
        user_count = len(get_all_users())
        bot.reply_to(message, f"Всего пользователей: {user_count}")
    else:
        bot.reply_to(message, "У вас нет прав для просмотра этой информации.")

# Обработчик текста
@bot.message_handler(func=lambda message: True)
def handle_city(message):
    city_name = message.text.strip()
    try:
        token = get_cdek_token()
        city_code = get_city_code(city_name, token)
        if city_code:
            points = get_delivery_points(city_code, token)
            if points:
                response = f"Пункты выдачи СДЭК в городе {city_name}:\n"
                for point in points:
                    address = point.get('location', {}).get('address')
                    latitude = point.get('location', {}).get('latitude')
                    longitude = point.get('location', {}).get('longitude')
                    if address and latitude and longitude:
                        # Добавляем ссылку на карту
                        map_link = f"https://www.google.com/maps?q={latitude},{longitude}"
                        response += f"- {address} [Карта]({map_link})\n"
                        if len(response) > 4000:
                            break
                bot.send_message(message.chat.id, response, parse_mode='Markdown')
            else:
                bot.reply_to(message, "Пункты выдачи не найдены.")
        else:
            bot.reply_to(message, "Код города не найден.")
    except Exception as e:
        bot.reply_to(message, "Ошибка при получении данных.")
        print(e)




# Запуск бота
if __name__ == '__main__':
    bot.polling(none_stop=True)
