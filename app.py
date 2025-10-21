import os
from flask import Flask, request
from google import genai
# 1. ІМПОРТ TWILIO
from twilio.rest import Client as TwilioClient 

# Ініціалізація Flask
app = Flask(__name__)

# Ініціалізація Gemini API
# Ключ береться зі змінної оточення GEMINI_API_KEY
client_gemini = genai.Client(api_key=os.environ.get("GEMINI_API_KEY")) 

# Ініціалізація Twilio КЛІЄНТА
# Ключі беруться зі змінних оточення TWILIO_ACCOUNT_SID та TWILIO_AUTH_TOKEN
client_twilio = TwilioClient(
    os.environ.get("TWILIO_ACCOUNT_SID"), 
    os.environ.get("TWILIO_AUTH_TOKEN")
)

# Отримуємо номер Twilio, який буде номером відправника
TWILIO_NUMBER = os.environ.get("TWILIO_NUMBER")


@app.route("/sms", methods=['POST'])
def sms_reply():
    # 1. ОТРИМАННЯ ВХІДНОГО SMS (Twilio використовує 'Body' та 'From')
    # request.values підходить для даних, надісланих Twilio (form-urlencoded)
    incoming_msg = request.values.get('Body', 'Який твій улюблений колір?', type=str)
    from_number = request.values.get('From', None)  # Номер, з якого надійшло SMS (ваш мобільний)

    print(f"[{datetime.datetime.now()}] Отримано повідомлення від {from_number}: {incoming_msg}")

    # Перевірка наявності номера відправника
    if not from_number:
        print("Помилка: Не отримано номер відправника (From).")
        return "ERROR: Missing From Number", 400

    # 2. ЗАПИТ ДО GEMINI
    try:
        response_gemini = client_gemini.models.generate_content(
            model='gemini-2.5-flash',
            contents=incoming_msg
        )
        ai_response_text = response_gemini.text
        print(f"Відповідь Gemini: {ai_response_text[:50]}...")

    except Exception as e:
        ai_response_text = "Вибачте, сталася внутрішня помилка AI. Спробуйте пізніше."
        print(f"Критична помилка Gemini: {e}")

    # 3. ВІДПРАВКА ВІДПОВІДНОГО SMS (Twilio)
    if TWILIO_NUMBER:
        try:
            client_twilio.messages.create(
                to=from_number,          # На номер, з якого надійшло SMS
                from_=TWILIO_NUMBER,     # З вашого КУПЛЕНОГО номера Twilio
                body=ai_response_text    # Відповідь від Gemini
            )
            print(f"Відповідь успішно відправлена на {from_number}")
        except Exception as e:
            print(f"Помилка відправки SMS Twilio: {e}")
            
    return "", 200 # Twilio очікує 200 OK

# Додаємо імпорт datetime для логів.
import datetime 

if __name__ == "__main__":
    app.run(port=5000, debug=True)
