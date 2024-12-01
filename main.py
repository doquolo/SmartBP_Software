import requests
from time import strftime, localtime
import os
from dotenv import load_dotenv, dotenv_values

load_dotenv()

# chatGPT
def getGPTresponse(ques: str):
    headers = {
        "Content-Type": "application/json",
        "x-rapidapi-host": "chatgpt-api8.p.rapidapi.com",
        "x-rapidapi-key": str(os.getenv("CHATGPT_API_KEY"))
    }
    url = "https://chatgpt-api8.p.rapidapi.com/"
    body = [
        {
            "content": "Xin chào, tôi là chatbot dựa trên chatGPT 3, sử dụng để cho lời khuyên về kết quả đo từ máy đo huyết áp. Bạn hãy cho tôi kết quả đo!",
            "role": "system"
        },
        {
            "content": str(ques),
            "role": "user"
        }
    ]

    res = requests.post(headers=headers, url=url, json=body)
    return res.json()['text']

# firebase part
import firebase_admin
from firebase_admin import db 

cred_obj = firebase_admin.credentials.Certificate('creds.json')
default_app = firebase_admin.initialize_app(cred_obj, {
    'databaseURL': str(os.getenv("RTDB_TOKEN"))
})

# data
idList = []
pendingMessage = []

# bot
# requires the 'message_content' intent.
import discord
from discord.ext import commands
from discord.ext import tasks

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix='!', intents=intents)

@bot.command(pass_content = True)
async def register(ctx, id: str):
    user = ctx.message.author
    if (id in idList):
        await ctx.send(f"Đã có người dùng theo dõi máy này {id}")
    else:
        exec(f'''count{id} = 1
def func{id}(event):
    global count{id}, pendingMessage
    if (count{id} == 0):
        machineID = {id}
        userid = {ctx.message.author.id}
        data = event.data.split(";")
        timestamp = event.path[1:]
        pendingMessage.append({{"id": userid, "machineID": machineID, "timestamp": int(timestamp), "content": {{"sys": data[0], "dias": data[1], "pulse": data[2]}}}})
        print(pendingMessage)
        print("done")
    else: count{id} = 0
firebase_admin.db.reference('/{id}/').listen(func{id})
        ''')
        idList.append(id)
        await ctx.send(f"Đã đăng kí cho {user.mention} theo dõi máy #{id}")

@tasks.loop(seconds=1)
async def scanForMessage():
    # print(len(pendingMessage))
    while (len(pendingMessage) != 0):
        message = pendingMessage.pop()
        user = await bot.fetch_user(message["id"])
        await user.send(f'''Người dùng đã thực hiện đo trên máy #{message["machineID"]} !
Thời gian: {strftime('%Y-%m-%d %H:%M:%S', localtime(message["timestamp"]))}
Huyết áp tâm thu (sys): {message["content"]["sys"]} (mmHg)
Huyết áp tâm trương (dias): {message["content"]["dias"]} (mmHg)
Nhịp tim: {message["content"]["pulse"]} (bpm)
Nhận xét: {getGPTresponse(f'Sys: {message["content"]["sys"]} (mmHg) Dias: {message["content"]["dias"]} (mmHg) Pulse: {message["content"]["pulse"]} (bpm)')}
''')
        
@bot.listen()
async def on_ready():
    scanForMessage.start() # important to start the loop

bot.run(str(os.getenv("DISCORD_BOT_TOKEN")))
