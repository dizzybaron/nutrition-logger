
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

    if photos:
        file_id = photos[-1]["file_id"]
        image_url = get_photo_url(file_id)
        send_telegram_message(chat_id, "🧠 分析圖片中，請稍候 5 秒...")
        food_query = vision_describe_image(image_url)
        send_telegram_message(chat_id, f"📷 Vision 辨識結果：\n{food_query}")

    if not food_query:
        send_telegram_message(chat_id, "⚠️ 請提供食物描述文字或圖片。")
        return jsonify({"status": "no_query"}), 200

    nutrition = call_nutritionix(food_query)

    summary_lines = []
    total_calories = 0
    for item in nutrition["foods"]:
        name = item["food_name"]
        kcal = item["nf_calories"]
        protein = item["nf_protein"]
        fat = item["nf_total_fat"]
        carb = item["nf_total_carbohydrate"]
        sodium = item["nf_sodium"]
        total_calories += kcal
        summary_lines.append(f"{name}：{round(kcal)} kcal，蛋白質 {round(protein)}g，脂肪 {round(fat)}g，碳水 {round(carb)}g")

    reply_text = f"✅ 餐別：{meal_type}
" +                  "
".join(summary_lines) +                  f"

總熱量：約 {round(total_calories)} kcal"

    send_telegram_message(chat_id, reply_text)

    for item in nutrition["foods"]:
        requests.post(GSHEET_WEBHOOK_URL, json={
            "date": "",
            "meal_type": meal_type,
            "food_name": item["food_name"],
            "serving": f"{item['serving_qty']} {item['serving_unit']}",
            "calories": item["nf_calories"],
            "protein": item["nf_protein"],
            "fat": item["nf_total_fat"],
            "carbs": item["nf_total_carbohydrate"],
            "sodium": item["nf_sodium"],
            "source": "GPT Vision + Nutritionix",
            "note": "由照片估算"
        })

    return jsonify({"status": "ok"}), 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
