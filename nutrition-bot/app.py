
import os
import requests
from flask import Flask, request

app = Flask(__name__)

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.json
    # Log incoming data
    print("Received:", data)
    return 'OK'
