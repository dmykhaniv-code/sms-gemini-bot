import os
from flask import Flask, request
from google import genai
import vonage # <--- КОНФИГУРАЦИЯ: Правильный импорт Vonage

# Инициализация Flask
app = Flask(__name__)

# Инициализация Gemini
client_gemini = genai.Client(api_key=os.environ.get("GEMINI_API_KEY")) 

# Инициализация Vonage (использует переменные окружения VONAGE_API_KEY и VONAGE_API_SECRET)
client_vonage = vonage.Client( 
    key=os.environ.get("VONAGE_API_KEY"),
    secret=os.environ.get("VONAGE_API_SECRET")
)

@app.route("/sms", methods=['POST'])
def sms_reply():
    # 1. Получение входящего SMS от Vonage
    # Vonage использует 'text' для сообщения, 'msisdn' для отправителя, 'to' для номера Vonage
    incoming_msg = request.values.get('text', 'Привет', type=str)
    from_number = request.values.get('msisdn', None) 
    to_number_vonage = request.values.get('to', None) 

    print(f"Получено сообщение от {from_number}: {incoming_msg}")

    # 2. Запрос к Gemini
    try:
        response_gemini = client_gemini.models.generate_content(
            model='gemini-2.5-flash',
            contents=incoming_msg
        )
        ai_response_text = response_gemini.text
    except Exception as e:
        ai_response_text = "Вибачте, сталася внутрішня помилка AI. Спробуйте пізніше."
        print(f"Ошибка Gemini: {e}")

    # 3. Отправка ответного SMS через Vonage API
    if from_number and to_number_vonage:
        try:
            # Отправка сообщения с использованием Vonage Messages API
            client_vonage.messages.send_message(
                {
                    "from": to_number_vonage,   # Ваш номер Vonage
                    "to": from_number,          # Номер, на который нужно ответить
                    "text": ai_response_text,   # Ответ от Gemini
                }
            )
            print(f"Ответ успешно отправлен на {from_number}")
        except Exception as e:
            print(f"Ошибка отправки SMS Vonage: {e}")

    # 4. Возвращаем HTTP 200 OK, чтобы Vonage не повторял запрос
    return "", 200

if __name__ == "__main__":
    app.run(port=5000, debug=True)
