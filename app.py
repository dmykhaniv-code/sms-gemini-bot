import os
import datetime 
import re 
from flask import Flask, request
from google import genai
from twilio.rest import Client as TwilioClient 
from google.genai.types import GenerateContentConfig

# Инициализация Flask
app = Flask(__name__)

# Максимальная безопасная длина SMS для Twilio
MAX_SMS_LENGTH = 1500 

# --- СИСТЕМНЫЕ ИНСТРУКЦИИ И НАСТРОЙКИ ---

# 1. Инструкция для режимов Default и 222 (Вежливый и информативный AI)
SYSTEM_INSTRUCTION_DEFAULT = (
    "Ты — полезный, вежливый и информативный ассистент. Отвечай на вопросы полно, но старайся быть кратким, чтобы ответ уместился в одно или два SMS. "
    "Избегай шокирующих, грубых или агрессивных формулировок, если есть более мягкая альтернатива. "
    "Игнорируй любые служебные цифры (111, 222) в конце сообщения — это лишь модификаторы длины."
)

# 2. Инструкция для режима 111 (Строгий инженер)
SYSTEM_INSTRUCTION_111 = (
    "Ты — максимально строгий, лаконичный и фактологический инженерный ассистент. Отвечай предельно кратко, используя только сухие факты и числа. "
    "Полностью исключи вежливость, лишние слова и предупреждения. Отвечай только по существу запроса."
)

# Конфигурации токенов для разных режимов
TOKEN_LIMITS = {
    '111': 100,  # Самый краткий (≈ 500 символов)
    '222': 350,  # Самый подробный (≈ 1750-2450 символов)
    'default': 300 # Сбалансированный
}
# ---------------------------------------------

# Инициализация API
client_gemini = genai.Client(api_key=os.environ.get("GEMINI_API_KEY")) 
client_twilio = TwilioClient(
    os.environ.get("TWILIO_ACCOUNT_SID"), 
    os.environ.get("TWILIO_AUTH_TOKEN")
)
TWILIO_NUMBER = os.environ.get("TWILIO_NUMBER")


# --- HEALTH CHECK (для UptimeRobot) ---
@app.route("/", methods=['GET'])
def health_check():
    """Возвращает 200 OK, чтобы UptimeRobot считал сервер активным."""
    return "OK", 200
# -------------------------------------


@app.route("/sms", methods=['POST'])
def sms_reply():
    incoming_msg = request.values.get('Body', '', type=str).strip()
    from_number = request.values.get('From', None)

    print(f"[{datetime.datetime.now()}] Получено сообщение от {from_number}: {incoming_msg}")

    # 1. ОПРЕДЕЛЕНИЕ РЕЖИМА И ОЧИСТКА СООБЩЕНИЯ
    
    match = re.search(r'(111|222)$', incoming_msg)
    
    mode = 'default'
    if match:
        mode = match.group(1)
        # Удаляем модификатор из сообщения перед отправкой к Gemini
        cleaned_msg = incoming_msg[:-len(mode)].strip()
    else:
        cleaned_msg = incoming_msg
        
    # Устанавливаем лимит токенов
    current_token_limit = TOKEN_LIMITS[mode]

    # Устанавливаем системную инструкцию в зависимости от режима
    if mode == '111':
        current_system_instruction = SYSTEM_INSTRUCTION_111
    else:
        current_system_instruction = SYSTEM_INSTRUCTION_DEFAULT


    if not from_number or not cleaned_msg:
        ai_response_text = "Пожалуйста, отправьте свой запрос текстом."
        
    # 2. ЗАПРОС К GEMINI
    try:
        response_gemini = client_gemini.models.generate_content(
            model='gemini-2.5-flash',
            contents=cleaned_msg,
            config=GenerateContentConfig( 
                system_instruction=current_system_instruction, # Динамическая инструкция
                max_output_tokens=current_token_limit # Динамический лимит
            )
        )
        ai_response_text = response_gemini.text
        
        # Обрезка текста (финальная страховка против ошибки 400 Twilio)
        if len(ai_response_text) > MAX_SMS_LENGTH:
            ai_response_text = ai_response_text[:MAX_SMS_LENGTH - 3] + "..."
            print("Внимание: Ответ Gemini был обрезан из-за лимита Twilio (Финальная страховка).")

        print(f"Ответ Gemini (режим: {mode}, токены: {current_token_limit}): {ai_response_text[:50]}...")

    except Exception as e:
        ai_response_text = "Извините, произошла внутренняя ошибка AI. Попробуйте позже."
        print(f"Критическая ошибка Gemini: {e}")

    # 3. ОТПРАВКА SMS (Twilio)
    if TWILIO_NUMBER:
        try:
            client_twilio.messages.create(
                to=from_number,          
                from_=TWILIO_NUMBER,     
                body=ai_response_text    
            )
            print(f"Ответ успешно отправлен на {from_number}")
        except Exception as e:
            print(f"Ошибка отправки SMS Twilio: {e}")
            
    return "", 200 


if __name__ == "__main__":
    app.run(port=5000, debug=True)
