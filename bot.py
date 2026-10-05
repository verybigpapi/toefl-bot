import os
import datetime
import requests
import discord
from discord.ext import commands, tasks
from flask import Flask
from threading import Thread

# === 1. 環境變數 ===
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
DISCORD_TOKEN = os.environ.get("DISCORD_TOKEN")
CHANNEL_ID = 1555854044457865357  # #toefl-daily

# 3.8 Flash 尖峰很容易 high demand。先打較穩的 lite，失敗再換。
MODELS = [
    "gemini-3.5-flash-lite",
    "gemini-3.1-flash-lite",
    "gemini-2.5-flash",
    "gemini-3.8-flash",
]

TZ = datetime.timezone(datetime.timedelta(hours=8))  # 台灣時間

# === 2. Render 防休眠（仍需要外部每 10 分鐘 ping 一次，免費方案才不會睡著）===
app = Flask(__name__)

@app.route("/")
def home():
    return "Bot is running!"

def run_web():
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))

Thread(target=run_web, daemon=True).start()

# === 3. Discord ===
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

PROMPT = """
你是托福單字教練。對象是準備出國讀建築研究所的考生（台灣，中文母語）。
請產生 5 個托福學術核心單字，以及 5 個建築／都市設計專業單字。不要重複常見初級字（important, beautiful, building）。
每個單字嚴格用這個格式，單字之間空一行：

👉 **英文單字** (詞性) 中文解釋
📝 例句：一句自然的英文，12–18 個字
💡 翻譯：對應中文

只輸出這 10 個單字，不要開場白、不要結語、不要編號清單以外的說明。
"""


def call_gemini():
    if not GEMINI_API_KEY:
        raise RuntimeError("環境變數 GEMINI_API_KEY 是空的")

    headers = {
        "Content-Type": "application/json",
        "x-goog-api-key": GEMINI_API_KEY,
    }
    payload = {
        "contents": [{"parts": [{"text": PROMPT}]}],
        "generationConfig": {
            "temperature": 0.8,
            "maxOutputTokens": 1200,
        },
    }

    errors = []
    for model in MODELS:
        url = (
            "https://generativelanguage.googleapis.com/v1beta/models/"
            f"{model}:generateContent"
        )
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=40)
        except requests.RequestException as exc:
            errors.append(f"{model}: 連線失敗 {exc}")
            continue

        try:
            body = response.json()
        except ValueError:
            errors.append(f"{model}: HTTP {response.status_code}，不是 JSON")
            continue

        if response.status_code != 200:
            message = body.get("error", {}).get("message", response.text[:180])
            errors.append(f"{model}: HTTP {response.status_code} {message}")
            continue

        candidates = body.get("candidates") or []
        parts = (
            candidates[0].get("content", {}).get("parts", [])
            if candidates else []
        )
        text = "".join(part.get("text", "") for part in parts).strip()
        if text:
            return text, model

        block = body.get("promptFeedback", {}).get("blockReason", "空回覆")
        errors.append(f"{model}: 沒有文字（{block}）")

    raise RuntimeError("；".join(errors) or "所有模型都失敗")


async def send_long(channel, text):
    chunk = ""
    for line in text.split("\n"):
        piece = line + "\n"
        if len(chunk) + len(piece) > 1900:
            if chunk.strip():
                await channel.send(chunk.strip())
            chunk = piece
        else:
            chunk += piece
    if chunk.strip():
        await channel.send(chunk.strip())


async def generate_words(channel, announce=True):
    if announce:
        await channel.send("收到指令，正在呼叫 AI 產生單字中...")
    try:
        text, model = call_gemini()
    except Exception as exc:
        print(f"發送失敗: {exc}")
        await channel.send(f"AI 產生失敗，錯誤原因: {exc}")
        return

    now = datetime.datetime.now(TZ).strftime("%Y-%m-%d %H:%M")
    header = f"Verybigpapi，{now} 的專屬單字（{model}）："
    await send_long(channel, f"{header}\n\n{text}")


# === 4. 每晚 22:30（台灣時間）===
@tasks.loop(time=datetime.time(hour=22, minute=30, tzinfo=TZ))
async def daily_vocab():
    channel = bot.get_channel(CHANNEL_ID)
    if channel is None:
        channel = await bot.fetch_channel(CHANNEL_ID)
    await generate_words(channel, announce=False)


@daily_vocab.before_loop
async def before_daily_vocab():
    await bot.wait_until_ready()


@bot.event
async def on_ready():
    print(f"機器人 {bot.user} 重新啟動成功！")
    if not daily_vocab.is_running():
        daily_vocab.start()
        print("已排程：每天 22:30（GMT+8）發送單字")


@bot.command(name="vocab")
async def test_vocab(ctx):
    await generate_words(ctx.channel, announce=True)


bot.run(DISCORD_TOKEN)
