import os
import requests
import re
import discord
import pandas as pd

import gspread
from oauth2client.service_account import ServiceAccountCredentials

# =========================
# ✅ Secrets Fly.io
# =========================
TOKEN = os.getenv("DISCORD_TOKEN")
OCR_KEY = os.getenv("OCR_API_KEY")

# Google Service Account JSON (base64 ou fichier)
GOOGLE_CREDS_FILE = "credentials.json"

# =========================
# ✅ Google Sheets Config
# =========================
SHEET_NAME = "prix"   # Nom exact de ton Google Sheet

scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive"
]

creds = ServiceAccountCredentials.from_json_keyfile_name(
    GOOGLE_CREDS_FILE, scope
)

gc = gspread.authorize(creds)
sheet = gc.open(SHEET_NAME).sheet1


# =========================
# ✅ Discord Bot Setup
# =========================
intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)


# =========================
# ✅ Qualités MMO
# =========================
def quality_label(level):
    qualities = {
        "1": "⚪ PuR1 (Common — no outline)",
        "2": "🟢 PuR2 (Uncommon — green outline)",
        "3": "🔵 PuR3 (Rare — blue outline)",
        "4": "🟡 PuR4 (Heroic — yellow outline)",
        "5": "🟣 PuR5 (Epic — purple outline)",
        "6": "🟠 PuR6 (Legendary — orange outline)"
    }
    return qualities.get(level, "❓ Qualité inconnue")


# =========================
# ✅ OCR Function
# =========================
def ocr_image(path):
    with open(path, "rb") as f:
        r = requests.post(
            "https://api.ocr.space/parse/image",
            files={"filename": f},
            data={
                "apikey": OCR_KEY,
                "language": "eng",
                "scale": True,
                "OCREngine": 2
            }
        )

    result = r.json()
    if result.get("IsErroredOnProcessing"):
        return None

    return result["ParsedResults"][0]["ParsedText"]


# =========================
# ✅ Extract Price Pattern
# =========================
def extract_price(text):
    match = re.search(r"(\d+)G\s*(\d+)S\s*(\d+)C", text)
    if match:
        return f"{match.group(1)}G {match.group(2)}S {match.group(3)}C"
    return None


# =========================
# ✅ Sheet Helpers
# =========================
def get_row(minerai):
    records = sheet.get_all_records()
    for i, row in enumerate(records, start=2):
        if row["Minerai"].lower() == minerai.lower():
            return i
    return None


def shift_history(row, col_base):
    """
    Décale automatiquement :
    PuR1 -> PuR1_1d -> PuR1_7d -> PuR1_30d
    """

    now_col = col_base
    d1_col = col_base + "_1d"
    w1_col = col_base + "_7d"
    m1_col = col_base + "_30d"

    headers = sheet.row_values(1)

    def col_index(name):
        return headers.index(name) + 1

    now_val = sheet.cell(row, col_index(now_col)).value

    # Shift down
    sheet.update_cell(row, col_index(m1_col),
                      sheet.cell(row, col_index(w1_col)).value)

    sheet.update_cell(row, col_index(w1_col),
                      sheet.cell(row, col_index(d1_col)).value)

    sheet.update_cell(row, col_index(d1_col), now_val)


def set_price(minerai, niveau, new_price):
    row = get_row(minerai)
    if not row:
        return False

    col_base = f"PuR{niveau}"

    # Shift history automatically
    shift_history(row, col_base)

    # Update NOW price
    headers = sheet.row_values(1)
    col_index = headers.index(col_base) + 1

    sheet.update_cell(row, col_index, new_price)
    return True


def get_prices(minerai, niveau):
    row = get_row(minerai)
    if not row:
        return None

    headers = sheet.row_values(1)

    col_base = f"PuR{niveau}"
    cols = [col_base, col_base+"_1d", col_base+"_7d", col_base+"_30d"]

    values = {}
    for c in cols:
        if c in headers:
            idx = headers.index(c) + 1
            values[c] = sheet.cell(row, idx).value
        else:
            values[c] = "—"

    return values


# =========================
# ✅ Events
# =========================
@client.event
async def on_ready():
    print("✅ Bot connecté et prêt !")


@client.event
async def on_message(message):
    if message.author == client.user:
        return

    # =========================
    # ✅ Command: !pur iron 1
    # =========================
    if message.content.startswith("!pur"):
        parts = message.content.split()
        if len(parts) < 3:
            await message.channel.send("❌ Utilisation : !pur Iron 1")
            return

        minerai = parts[1]
        niveau = parts[2]

        qual = quality_label(niveau)
        prices = get_prices(minerai, niveau)

        if not prices:
            await message.channel.send("❌ Minerai introuvable.")
            return

        msg = f"✨ **{qual}**\n"
        msg += f"💰 **{minerai} PuR{niveau}** = {prices[f'PuR{niveau}']}\n\n"
        msg += "📉 **Historique des prix :**\n"
        msg += f"- Now: {prices[f'PuR{niveau}']}\n"
        msg += f"- 1 day ago: {prices[f'PuR{niveau}_1d']}\n"
        msg += f"- 1 week ago: {prices[f'PuR{niveau}_7d']}\n"
        msg += f"- 1 month ago: {prices[f'PuR{niveau}_30d']}\n"

        await message.channel.send(msg)
        return

    # =========================
    # ✅ Command: !update iron 1 + image
    # =========================
    if message.content.startswith("!update"):
        parts = message.content.split()
        if len(parts) < 3:
            await message.channel.send("❌ Utilisation : !update Iron 1 + image")
            return

        if len(message.attachments) == 0:
            await message.channel.send("❌ Ajoute une image marketplace.")
            return

        minerai = parts[1]
        niveau = parts[2]

        attachment = message.attachments[0]
        await attachment.save("market.png")

        await message.channel.send("🔍 OCR en cours...")

        text = ocr_image("market.png")
        if not text:
            await message.channel.send("❌ OCR échoué.")
            return

        price = extract_price(text)
        if not price:
            await message.channel.send("❌ Prix non détecté.")
            return

        ok = set_price(minerai, niveau, price)
        if ok:
            await message.channel.send(
                f"✅ Prix mis à jour : **{minerai} PuR{niveau} = {price}**"
            )
        else:
            await message.channel.send("❌ Impossible de mettre à jour.")

        return


# ✅ Run Bot
client.run(TOKEN)
