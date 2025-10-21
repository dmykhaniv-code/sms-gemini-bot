import os
from flask import Flask, request
from google import genai
from vonage.client import Client # <--- ВИПРАВЛЕНО: Клієнт імпортується явно з підмодуля

# Ініціалізація Flask
app = Flask(__name__)

# Ініціалізація Gemini 
# Ключ береться з змінних оточення Render (GEMINI_API_KEY)
client_gemini = genai.Client(api_key=os.environ.get("GEMINI_API_KEY")) 

# Ініціалізація Vonage 
# Ключі беруться з змінних оточення Render (VONAGE_API_KEY, VONAGE_API_SECRET)
client_vonage = Client( 
    key=os.environ.get("VONAGE_API_KEY"),
    secret=os.environ.get("VONAGE_API_SECRET")
)

@app.route("/sms", methods=['POST'])
def sms_reply():
    # 1. Отримання вхідного SMS від Vonage
    # 'text' — це вміст повідомлення
    # 'msisdn' — це номер відправника
    # 'to' — це ваш віртуальний номер Vonage
    incoming_msg = request.values.get('text', 'Привіт', type=str)
    from_number = request.values.get('msisdn', None) 
    to_number_vonage = request.values.get('to', None) 

    print(f"Отримано повідомлення від {from_number}: {incoming_msg}")

    # 2. Запит до Gemini
    try:
        response_gemini = client_gemini.models.generate_content(
            model='gemini-2.5-flash',
            contents=incoming_msg
        )
        ai_response_text = response_gemini.text
    except Exception as e:
        ai_response_text = "Вибачте, сталася внутрішня помилка AI. Спробуйте пізніше."
        print(f"Помилка Gemini: {e}")

    # 3. Відправка відповідного SMS через Vonage API
    if from_number and to_number_vonage:
        try:
            # Виклик функції відправки повідомлень
            client_vonage.messages.send_message(
                {
                    "from": to_number_vonage,   # З номера Vonage
                    "to": from_number,          # На номер, з якого надійшло SMS
                    "text": ai_response_text,   # Відповідь від Gemini
                }
            )
            print(f"Відповідь успішно відправлена на {from_number}")
        except Exception as e:
            print(f"Помилка відправки SMS Vonage: {e}")

    # 4. Повертаємо HTTP 200 OK, щоб Vonage знав, що запит успішно оброблено
    return "", 200

if __name__ == "__main__":
    # Gunicorn використовуватиме цей файл, але для локального тестування це також працює
    app.run(port=5000, debug=True)
