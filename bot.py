import requests
import os
import discord
import pandas as pd

TOKEN = os.getenv("DISCORD_TOKEN")

SHEET_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQuSjmPkmLzo3ZBvmnsRi0oorXxmzJ55kxCjR3Cf_0s3e8I0epGKwRkeEhP5wq3FjJv13B32-_jODqB/pub?output=csv"

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

def format_money(copper):
    g = copper // 10000
    s = (copper % 10000) // 100
    c = copper % 100
    return f"{g}G {s}S {c}C"

def load_data():
    return pd.read_csv(SHEET_URL)

OCR_KEY = os.getenv("OCR_API_KEY")

def ocr_image(path):
    with open(path, "rb") as f:
        r = requests.post(
            "https://api.ocr.space/parse/image",
            files={"filename": f},
            data={
                "apikey": OCR_KEY,
                "language": "eng"
            }
        )

    result = r.json()

    if result.get("IsErroredOnProcessing"):
        return "❌ Erreur OCR."

    return result["ParsedResults"][0]["ParsedText"]

@client.event
async def on_ready():
    print("✅ Bot connecté et prêt !")

@client.event
async def on_message(message):
    if message.author == client.user:
        return

    # ✅ Commande OCR : !ocr + image jointe
    if message.content.startswith("!ocr"):

        if len(message.attachments) == 0:
            await message.channel.send("❌ Envoie une image avec la commande !ocr")
            return

        attachment = message.attachments[0]

        # Sauvegarder l’image envoyée
        await attachment.save("image.png")

        await message.channel.send("🔍 Lecture OCR en cours...")

        # OCR
        text = ocr_image("image.png")

        await message.channel.send(f"📷 Texte détecté :\n```{text}```")
        return

    if message.content.startswith("!pur"):
        parts = message.content.split()

        if len(parts) < 3:
            await message.channel.send("❌ Utilisation : !pur Iron 1")
            return

        minerai = parts[1]
        niveau = parts[2]
        col = f"PuR{niveau}"

        data = load_data()

        if col not in data.columns:
            await message.channel.send("❌ Niveau invalide (1 à 6).")
            return

        result = data[data["Minerai"].str.lower() == minerai.lower()]

        if result.empty:
            await message.channel.send("❌ Minerai introuvable.")
            return

        value = result[col].values[0]

        if pd.isna(value):
            await message.channel.send("⚠️ Prix non défini.")
            return

        # ✅ Cas 1 : déjà en format texte "0G 07S 77C"
        if isinstance(value, str) and "G" in value:
            await message.channel.send(f"💰 {minerai} {col} = {value}")
            return

        # ✅ Cas 2 : valeur cuivre numérique
        copper_price = int(value)

        await message.channel.send(
            f"💰 {minerai} {col} = {format_money(copper_price)}"
        )

client.run(TOKEN)
