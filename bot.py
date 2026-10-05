import discord
from discord.ext import tasks, commands
import datetime
import os
import requests
from flask import Flask
from threading import Thread

# === 1. 抓取金庫密碼 ===
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')
DISCORD_TOKEN = os.environ.get('DISCORD_TOKEN')
CHANNEL_ID = 1555854044457865357  # 你的正確頻道 ID

# === 2. 雲端防休眠守衛 ===
app = Flask(__name__)
@app.route('/')
def home():
    return "Bot is running!"
def run():
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))
Thread(target=run).start()

# === 3. Discord 權限開啟 ===
intents = discord.Intents.default()
intents.message_content = True  
bot = commands.Bot(command_prefix='!', intents=intents)

# === 4. 單字產生核心引擎 (使用直接聯絡 Google API 方式) ===
async def generate_words(channel):
    prompt = """
    為準備出國讀建築研究所的考生，產生5個托福核心單字與5個建築設計專業單字。
    格式：
    👉 **[英文單字]** ([詞性]) [中文解釋]
    📝 例句：[英文例句]
    💡 翻譯：[中文翻譯]
    """
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}"
    headers = {'Content-Type': 'application/json'}
    data = {
        "contents": [{"parts": [{"text": prompt}]}]
    }
    
    try:
        response = requests.post(url, headers=headers, json=data)
        res_json = response.json()
        text = res_json['candidates'][0]['content']['parts'][0]['text']
        await channel.send(f"楊建築師，你的專屬單字來了：\n\n{text}")
    except Exception as e:
        print(f"發送失敗: {e}")
        await channel.send("AI 產生失敗，請確認 API Key 是否正確。")

# === 5. 機器人啟動與指令 ===
@bot.event
async def on_ready():
    print(f"機器人 {bot.user} 重新啟動成功！")

@bot.command(name='vocab')
async def test_vocab(ctx):
    await ctx.send("收到指令，正在呼叫 AI 產生單字中...")
    await generate_words(ctx.channel)

bot.run(DISCORD_TOKEN)
