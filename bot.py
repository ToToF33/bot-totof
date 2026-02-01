import os
import json
import base64
import discord
import aiohttp
import asyncio

import gspread
from oauth2client.service_account import ServiceAccountCredentials

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

SHEET_ID = "1KKMo1wqs25g61YGTF73ybqR-9n1uuLS5hvJVGjkxCOI"
sheet = gc.open_by_key(SHEET_ID).sheet1

# ========================================
# ✅ Discord Setup
# ========================================
intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

# ========================================
# ✅ OCR ASYNC (VERSION PARFAITE)
# ========================================
async def ocr_image_async(image_path: str):

    url = "https://api.ocr.space/parse/image"

    form = aiohttp.FormData()
    form.add_field("apikey", OCR_KEY)
    form.add_field("language", "eng")

    with open(image_path, "rb") as f:
        form.add_field(
            "file",
            f,
            filename="image.png",
            content_type="image/png"
        )

        async with aiohttp.ClientSession() as session:
            async with session.post(url, data=form) as resp:
                data = await resp.json()

    # ✅ Vérification OCR
    if "ParsedResults" not in data:
        return "❌ Aucun texte détecté."

    return data["ParsedResults"][0]["ParsedText"]

# ========================================
# ✅ Bot Ready
# ========================================
@client.event
async def on_ready():
    print("✅ Bot connecté et prêt !")

# ========================================
# ✅ On Message
# ========================================
@client.event
async def on_message(message):

    if message.author.bot:
        return

    # ✅ Si image envoyée
    if message.attachments:

        attachment = message.attachments[0]

        if attachment.filename.endswith(("png", "jpg", "jpeg")):

            await message.channel.send("📸 Image reçue, OCR en cours...")

            image_path = "image.png"
            await attachment.save(image_path)

            try:
                # ✅ OCR async
                text = await ocr_image_async(image_path)

                # ✅ Envoi résultat Discord
                await message.channel.send(
                    f"✅ Texte détecté :\n```{text}```"
                )

                # ✅ Sauvegarde Google Sheets
                sheet.append_row([message.author.name, text])

                await message.channel.send("✅ Sauvegardé dans Google Sheets 📄")

            except Exception as e:
                await message.channel.send(f"❌ Erreur OCR : {e}")

            finally:
                if os.path.exists(image_path):
                    os.remove(image_path)

# ========================================
# ✅ Run Bot
# ========================================
client.run(TOKEN)
