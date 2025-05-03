
import os
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

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
    resp = requests.post(
        f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
        json={"chat_id": chat_id, "text": text}
    )
    print("📬 Telegram response:", resp.status_code, resp.text)

@app.route('/webhook', methods=['POST'])
def telegram_webhook():
    data = request.json
    message = data.get("message", {})
    chat_id = message.get("chat", {}).get("id")
    text = message.get("text", "")

    if not text or "：" not in text:
        send_telegram_message(chat_id, "⚠️ 請輸入餐別與食物內容，例如：早餐：炒飯、煎蛋")
        return jsonify({"status": "missing_text"}), 200

    meal_type, food_query = text.split("：", 1)
    nutrition = call_nutritionix(food_query)

    if "foods" not in nutrition:
        send_telegram_message(chat_id, f"❌ Nutritionix 查詢失敗。\n\n系統訊息：{nutrition.get('message', '未知錯誤')}")
        return jsonify({"status": "nutritionix_error"}), 200

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

    reply_text = f"✅ 餐別：{meal_type}\n" +                  "\n".join(summary_lines) +                  f"\n\n總熱量：約 {round(total_calories)} kcal"

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
            "source": "Nutritionix",
            "note": "由使用者輸入文字估算"
        })

    return jsonify({"status": "ok"}), 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
