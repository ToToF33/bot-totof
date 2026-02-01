import os
import json
import base64
import discord
import aiohttp

import gspread
from oauth2client.service_account import ServiceAccountCredentials

# ========================================
# ✅ Secrets Fly.io
# ========================================
TOKEN = os.getenv("DISCORD_TOKEN")
OCR_KEY = os.getenv("OCR_API_KEY")
GOOGLE_CREDS_B64 = os.getenv("GOOGLE_CREDS")

# ========================================
# ✅ Google Auth
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
# ✅ OCR Async Stable
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

    if "ParsedResults" not in data:
        return "❌ Aucun texte détecté."

    return data["ParsedResults"][0]["ParsedText"]

# ========================================
# ✅ Ready
# ========================================
@client.event
async def on_ready():
    print("✅ Bot connecté et prêt !")

# ========================================
# ✅ Messages
# ========================================
@client.event
async def on_message(message):

    if message.author.bot:
        return

    # ✅ Commande PRIX
    if message.content.startswith("!prix"):

        parts = message.content.split()

        if len(parts) != 3:
            await message.channel.send("❌ Utilisation : `!prix copper 1`")
            return

        item = parts[1].strip().lower()
        tier = parts[2].strip()

        if tier not in ["1", "2", "3", "4", "5", "6"]:
            await message.channel.send("❌ Tier invalide (1 à 6).")
            return

        try:
            rows = sheet.get_all_records()

            for row in rows:
                if row["item"].lower() == item and str(row["tier"]) == tier:

                    await message.channel.send(
                        f"🪙 **{item.upper()} — Tier {tier}**\n\n"
                        f"📌 Prix actuel : **{row['prix_actuel']}**\n"
                        f"📉 Ancien prix : **{row['prix_ancien']}**"
                    )
                    return

            await message.channel.send("❌ Item ou tier introuvable.")

        except Exception as e:
            await message.channel.send(f"❌ Erreur : {e}")

        return

    # ✅ OCR Image
    if message.attachments:

        attachment = message.attachments[0]

        if attachment.filename.endswith(("png", "jpg", "jpeg")):

            await message.channel.send("📸 Image reçue, OCR en cours...")

            image_path = "image.png"
            await attachment.save(image_path)

            try:
                text = await ocr_image_async(image_path)
                await message.channel.send(f"✅ Texte détecté :\n```{text}```")

            except Exception as e:
                await message.channel.send(f"❌ Erreur OCR : {e}")

# ========================================
# ✅ Run
# ========================================
client.run(TOKEN)
