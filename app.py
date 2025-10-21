import os
import datetime 
import re 
from flask import Flask, request
from google import genai
from twilio.rest import Client as TwilioClient 
from google.genai.types import GenerateContentConfig

# Ініціалізація Flask
app = Flask(__name__)

# Максимальна безпечна довжина SMS для Twilio
MAX_SMS_LENGTH = 1500 

# --- СИСТЕМНА ІНСТРУКЦІЯ ТА НАЛАШТУВАННЯ ---

# Інструкція для Gemini: строгий, корисний, але стислий асистент.
SYSTEM_INSTRUCTION_BASE = (
    "Ты — полезный, но очень стислый ассистент. Отвечай всегда по сути запроса. "
    "Избегай вводных слов и лишних объяснений. "
    "Игнорируй любые служебные цифры (111, 222) в конце сообщения — это лишь модификаторы длины."
)

# Конфігурації токенів для різних режимів
TOKEN_LIMITS = {
    '111': 100,  # Максимально короткий (≈ 500 символів)
    '222': 350,  # Більш детальний, але безпечний для Twilio (≈ 1750-2450 символів)
    'default': 300 # Звичайний, збалансований
}
# ---------------------------------------------

# Ініціалізація API
client_gemini = genai.Client(api_key=os.environ.get("GEMINI_API_KEY")) 
client_twilio = TwilioClient(
    os.environ.get("TWILIO_ACCOUNT_SID"), 
    os.environ.get("TWILIO_AUTH_TOKEN")
)
TWILIO_NUMBER = os.environ.get("TWILIO_NUMBER")


# --- HEALTH CHECK (для UptimeRobot) ---
@app.route("/", methods=['GET'])
def health_check():
    """Повертає 200 OK, щоб UptimeRobot вважав сервер активним."""
    return "OK", 200
# -------------------------------------


@app.route("/sms", methods=['POST'])
def sms_reply():
    incoming_msg = request.values.get('Body', '', type=str).strip()
    from_number = request.values.get('From', None)

    print(f"[{datetime.datetime.now()}] Отримано повідомлення від {from_number}: {incoming_msg}")

    # 1. ВИЗНАЧЕННЯ РЕЖИМУ ТА ОЧИЩЕННЯ ПОВІДОМЛЕННЯ
    
    # Шукаємо модифікатор (111 або 222) у кінці повідомлення
    match = re.search(r'(111|222)$', incoming_msg)
    
    mode = 'default'
    if match:
        mode = match.group(1)
        # Видаляємо модифікатор з повідомлення перед відправкою до Gemini
        cleaned_msg = incoming_msg[:-len(mode)].strip()
    else:
        cleaned_msg = incoming_msg
        
    # Встановлюємо ліміт токенів
    current_token_limit = TOKEN_LIMITS[mode]

    if not from_number or not cleaned_msg:
        ai_response_text = "Будь ласка, надішліть свій запит текстом."
        
    # 2. ЗАПИТ ДО GEMINI
    try:
        response_gemini = client_gemini.models.generate_content(
            model='gemini-2.5-flash',
            contents=cleaned_msg,
            config=GenerateContentConfig( 
                system_instruction=SYSTEM_INSTRUCTION_BASE,
                max_output_tokens=current_token_limit # Використовуємо динамічний ліміт
            )
        )
        ai_response_text = response_gemini.text
        
        # Обрізка тексту (фінальна страховка проти помилки 400 Twilio)
        if len(ai_response_text) > MAX_SMS_LENGTH:
            ai_response_text = ai_response_text[:MAX_SMS_LENGTH - 3] + "..."
            print("Внимание: Ответ Gemini был обрезан из-за лимита Twilio (Финальная страховка).")

        print(f"Відповідь Gemini (режим: {mode}, токени: {current_token_limit}): {ai_response_text[:50]}...")

    except Exception as e:
        ai_response_text = "Вибачте, сталася внутрішня помилка AI. Спробуйте пізніше."
        print(f"Критична помилка Gemini: {e}")

    # 3. ВІДПРАВКА ВІДПОВІДНОГО SMS (Twilio)
    if TWILIO_NUMBER:
        try:
            client_twilio.messages.create(
                to=from_number,          
                from_=TWILIO_NUMBER,     
                body=ai_response_text    
            )
            print(f"Відповідь успішно відправлена на {from_number}")
        except Exception as e:
            print(f"Помилка відправки SMS Twilio: {e}")
            
    return "", 200 


if __name__ == "__main__":
    app.run(port=5000, debug=True)

