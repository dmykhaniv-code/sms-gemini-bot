import os
from flask import Flask, request
from google import genai

# Инициализация Flask
app = Flask(__name__)

# Инициализация Gemini (ключ берется из Render Environment Variables)
client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY")) 

@app.route("/sms", methods=['POST'])
def sms_reply():
    # 1. Получение входящего SMS от Vonage
    # Vonage использует поле 'text' для содержимого сообщения
    incoming_msg = request.values.get('text', 'Привет', type=str)

    # 2. Логирование 
    print(f"Получено сообщение: {incoming_msg}")

    # 3. Запрос к Gemini
    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=incoming_msg
        )
        ai_response_text = response.text
    except Exception as e:
        ai_response_text = "Извините, произошла ошибка AI. Попробуйте позже."
        print(f"Ошибка Gemini: {e}")

    # 4. Обработка ответа
    # Для целей тестирования Web-hook просто вернем пустой ответ (HTTP 200 OK)
    return "", 200

if __name__ == "__main__":
    app.run(port=5000, debug=True)
