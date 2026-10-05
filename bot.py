import discord
from discord.ext import tasks, commands
import google.generativeai as genai
import datetime
import os
from flask import Flask
from threading import Thread

# === 1. 抓取金庫密碼 ===
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')
DISCORD_TOKEN = os.environ.get('DISCORD_TOKEN')
CHANNEL_ID = 1555854044457865357  # 你的正確頻道 ID 已經填好！

# === 2. 啟動 AI ===
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')




# === 3. 雲端防休眠守衛 ===
app = Flask(__name__)
@app.route('/')
def home():
    return "Bot is running!"
def run():
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))
Thread(target=run).start()

# === 4. Discord 權限開啟 ===
intents = discord.Intents.default()
intents.message_content = True  
bot = commands.Bot(command_prefix='!', intents=intents)

# === 5. 單字產生核心引擎 ===
async def generate_words(channel):
    prompt = """
    為準備出國讀建築研究所的考生，產生5個托福核心單字與5個建築設計專業單字。
    格式：
    👉 **[英文單字]** ([詞性]) [中文解釋]
    📝 例句：[英文例句 (結合建築理論或留學生活)]
    💡 翻譯：[中文翻譯]
    """
    try:
        response = model.generate_content(prompt)
        await channel.send(f"楊建築師，你的專屬單字來了：\n\n{response.text}")
    except Exception as e:
        print(f"發送失敗: {e}")
        await channel.send("AI 產生失敗，請確認 API Key 是否正確。")

# === 6. 機器人啟動與排程 ===
@bot.event
async def on_ready():
    print(f"機器人 {bot.user} 重新啟動成功！")
    if not daily_task.is_running():
        daily_task.start()

# 手動測試開關：為了方便，改成輸入 !vocab 就會給單字
@bot.command(name='vocab')
async def test_vocab(ctx):
    await ctx.send("收到指令，正在呼叫 AI 產生單字中...")
    await generate_words(ctx.channel)

# 自動排程：設定今晚 10 點 30 分發送
tz_tw = datetime.timezone(datetime.timedelta(hours=8))
send_time = datetime.time(hour=22, minute=30, tzinfo=tz_tw)

@tasks.loop(time=send_time)
async def daily_task():
    channel = bot.get_channel(CHANNEL_ID)
    if channel:
        await generate_words(channel)

bot.run(DISCORD_TOKEN)
