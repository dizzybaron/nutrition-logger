import os
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.json
    print("✅ 收到 Telegram 訊息：", data)

    # 回傳 200 OK 給 Telegram
    return jsonify({"status": "received"}), 200


if __name__ == "__main__":
    # 讓 Flask 在 Render 指定的 port 上啟動（很重要）
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
