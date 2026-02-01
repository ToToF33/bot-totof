import os
import re
import json
import base64
import requests
import discord

import gspread
from oauth2client.service_account import ServiceAccountCredentials
from PIL import Image

# ========================================
# ✅ Secrets Fly.io
# ========================================
TOKEN = os.getenv("DISCORD_TOKEN")
OCR_KEY = os.getenv("OCR_API_KEY")
GOOGLE_CREDS_B64 = os.getenv("GOOGLE_CREDS")

if not TOKEN:
    print("❌ DISCORD_TOKEN manquant !")
    exit()

if not OCR_KEY:
    print("❌ OCR_API_KEY manquante !")
    exit()

if not GOOGLE_CREDS_B64:
    print("❌ GOOGLE_CREDS manquant !")
    exit()

# ========================================
# ✅ Google Sheets Auth
# ========================================
creds_json = base64.b64decode(GOOGLE_CREDS_B64).decode("utf-8")
creds_dict = json.loads(creds_json)

scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive",
]

creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
gc = gspread.authorize(creds)

# ✅ Ton Google Sheet ID (meilleur que le nom)
SHEET_ID = "1KKMo1wqs25g61YGTF73ybqR-9n1uuLS5hvJVGjkxCOI"
sheet = gc.open_by_key(SHEET_ID).sheet1

# ========================================
# ✅ Discord Setup
# =======================
