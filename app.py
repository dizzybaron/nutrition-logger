import os
import requests
import openai
from flask import Flask, request, jsonify

app = Flask(__name__)
openai.api_key = os.environ.get("OPENAI_API_KEY")
BOT_TOKEN = os.environ.get("BOT_TOKEN")
NUTRITIONIX_APP_ID = os.environ.get("NUTRITIONIX_APP_ID")
NUTRITIONIX_APP_KEY = os.environ.get("NUTRITIONIX_APP_KEY")
GSHEET_WEBHOOK_URL = os.environ.get("GOOGLE_SHEET_WEBHOOK_URL")

def call_nutritionix(query_text):
    url = "https://trackapi.nutritionix.com/v2/natural/nutrients"
    headers = {
        "x-app-id": NUTRITIONIX_APP_ID,
        "x-app-key": NUTRITIONIX_APP_KEY,
        "Content-Type": "application/json"
    }
    payload = {
        "query": query_text,
        "timezone": "Asia/Taipei"
    }
    response = requests.post(url, headers=headers, json=payload)
    return response.json()

def send_telegram_message(chat_id, text):
    requests.post(
        f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
        json={"chat_id": chat_id, "text": text}
    )

def get_photo_url(file_id):
    file_resp = requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getFile?file_id={file_id}")
    file_path = file_resp.json()["result"]["file_path"]
    return f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_path}"

def vision_describe_image(image_url):
    response = openai.chat.completions.create(
        model="gpt-4-vision-preview",
        messages=[
            {"role": "user", "content": [
                {"type": "text", "text": "請幫我看這張餐點照片，推估裡面有哪些食物與份量，用英文描述適合查詢營養資料的格式"},
                {"type": "image_url", "image_url": {"url": image_url}}
            ]}
        ],
        max_tokens=300
    )
    return response.choices[0].message.content

@app.route('/webhook', methods=['POST'])
def telegram_webhook():
    data = request.json
    message = data.get("message", {})
    chat_id = message.get("chat", {}).get("id")
    text = message.get("text", "")
    photos = message.get("photo", [])

    meal_type = "未知"
    food_query = ""

    if text and "：" in text:
        meal_type, food_query = text.split("：", 1)
    elif text:
        meal_type = text.strip()

    if
