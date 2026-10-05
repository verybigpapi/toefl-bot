import discord
from discord.ext import tasks, commands
import google.generativeai as genai
import datetime
import os
from flask import Flask
from threading import Thread
from zoneinfo import ZoneInfo

# === 改成從雲端主機的「保險箱」拿鑰匙 ===
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')
DISCORD_TOKEN = os.environ.get('DISCORD_TOKEN')
CHANNEL_ID = 1555854044457865357 # <--- 記得把這串數字換成你自己的頻道ID！

genai.configure(api_key=GEMINI_API_KEY)
# ==========================================

# 建立迷你網頁守衛 (讓雲端主機知道我們醒著)
app = Flask(__name__)
@app.route('/')
def home():
    return "機器人24小時運作中！"
def run():
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))
def keep_alive():
    t = Thread(target=run)
    t.start()

intents = discord.Intents.default()
bot = commands.Bot(command_prefix='!', intents=intents)
model = genai.GenerativeModel('gemini-1.5-flash')

@bot.event
async def on_ready():
    print("單字機器人已在雲端成功啟動！")
    send_daily_vocab.start()

# 嚴格指定使用台灣時區 (Asia/Taipei) 的晚上 9 點 15 分
tz_taipei = ZoneInfo("Asia/Taipei")
send_time = datetime.time(hour=21, minute=15, tzinfo=tz_taipei)

@tasks.loop(time=send_time)
async def send_daily_vocab():
    today = datetime.datetime.today().weekday()
    if today < 5:
        channel = bot.get_channel(CHANNEL_ID)
        if channel:
            prompt = """
            請為準備申請國外建築研究所的考生，產生今天份的 10 個托福單字。
            分為以下兩大類：
            【一般托福核心單字】(5個)
            【建築與設計專業單字】(5個)

            格式請嚴格依照此排版：
            👉 **[英文單字]** ([詞性]) [中文解釋]
            📝 例句：[英文例句 (請結合建築理論、都市計畫或留學生活)]
            💡 翻譯：[中文翻譯]
            """
            try:
                response = model.generate_content(prompt)
                await channel.send(f"今天的 10 個專屬單字來了！\n\n{response.text}")
                print("今日單字已成功發送！")
            except Exception as e:
                print(f"發送失敗: {e}")
    else:
        print("今天是週末，自動休息一天！")

keep_alive() 
bot.run(DISCORD_TOKEN)
