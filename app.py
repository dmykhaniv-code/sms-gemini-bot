import os
from flask import Flask, request
from google import genai
import vonage # <--- Новый импорт для отправки SMS

# Инициализация Flask
app = Flask(__name__)

# Инициализация Gemini (ключ берется из Render Environment Variables)
client_gemini = genai.Client(api_key=os.environ.get("GEMINI_API_KEY")) 

# Инициализация Vonage (ключи берутся из Render Environment Variables)
# Используем API Key и API Secret, которые вы сохранили
client_vonage = vonage.Client(
    key=os.environ.get("VONAGE_API_KEY"),
    secret=os.environ.get("VONAGE_API_SECRET")
)

@app.route("/sms", methods=['POST'])
def sms_reply():
    # 1. Получение входящего SMS от Vonage
    incoming_msg = request.values.get('text', 'Привет', type=str)
    
    # 2. Получение номера отправителя и номера Vonage (ВАЖНО для ответа)
    # Vonage использует поле 'msisdn' для номера отправителя
    from_number = request.values.get('msisdn', None) 
    # Vonage использует поле 'to' для номера Vonage
    to_number_vonage = request.values.get('to', None) 

    print(f"Получено сообщение от {from_number}: {incoming_msg}")

    # 3. Запрос к Gemini
    try:
        response_gemini = client_gemini.models.generate_content(
            model='gemini-2.5-flash',
            contents=incoming_msg
        )
        ai_response_text = response_gemini.text
    except Exception as e:
        ai_response_text = "Извините, произошла ошибка AI. Попробуйте позже."
        print(f"Ошибка Gemini: {e}")

    # 4. Отправка ответного SMS через Vonage API
    if from_number and to_number_vonage:
        try:
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

    # 5. Возвращаем HTTP 200 OK для Vonage
    return "", 200

if __name__ == "__main__":
    app.run(port=5000, debug=True)

