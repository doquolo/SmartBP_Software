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
from discord.ext import commands, tasks

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix='!', intents=intents)

@bot.command(pass_content = True)
async def clearMessage(ctx, limit:str):
    limit = int(limit)
    dmchannel = await ctx.author.create_dm()
    async for message in dmchannel.history(limit=100):
        if limit == 0: break
        if message.author == bot.user: 
            await message.delete()
            limit -= 1


@bot.command(pass_content = True)
async def fetchData(ctx, deviceID: str, date: str, month: str, year: str):
    user = ctx.message.author
    try:
        ref = db.reference(f"/{deviceID}/")
        data = ref.get()
        dayData = []
        for i in data:
            timeObj = localtime(int(i))
            if (int(date) == timeObj.tm_mday and int(month) == timeObj.tm_mon and int(year) == timeObj.tm_year):
                dayData.append({"timestamp": i, "content": data[i]})
        if (len(dayData) != 0):
            embed = discord.Embed(title=f"Máy #{deviceID} đã thực hiện đo {len(dayData)} lần trong ngày {int(date)}/{int(month)}/{int(year)}")
            for i in dayData:
                dataPoint = ""
                dataPoint += f'+) Huyết áp tâm thu (sys): {i["content"].split(";")[0]} (mmHg)\n'
                dataPoint += f'+) Huyết áp tâm truơng (dias): {i["content"].split(";")[1]} (mmHg)\n'
                dataPoint += f'+) Nhịp tim: {i["content"].split(";")[0]} (nhịp/phút)\n'
                embed.add_field(name=f'Vào lúc {strftime("%H:%M:%S", localtime(int(i["timestamp"])))}', value=dataPoint,inline=False)
            await ctx.send(embed=embed)
        else:
            embed = discord.Embed(title=f"Máy #{deviceID} đã không thực hiện đo trong ngày {int(date)}/{int(month)}/{int(year)}!")
            await ctx.send(embed=embed)

    except Exception as e:
        await ctx.send(f"Đã xảy ra lỗi! {e}")
        
@bot.command(pass_content = True)
async def register(ctx, id: str):
    user = ctx.message.author
    if (id in idList):
        embed = discord.Embed(description=f"Đã có người dùng theo dõi máy này {id}")
        await ctx.send(embed=embed)
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
        embed = discord.Embed(title="", description=f"Đã đăng kí cho {user.mention} theo dõi máy #{id}")
        await ctx.send(embed=embed)

@tasks.loop(seconds=1)
async def scanForMessage():
    # print(len(pendingMessage))
    while (len(pendingMessage) != 0):
        message = pendingMessage.pop()
        user = await bot.fetch_user(message["id"])
        embed = discord.Embed(title=f'Máy #{message["machineID"]} đã thực hiện đo!', description=user.mention)
        embed.add_field(name=f'Thời gian: {strftime("%Y-%m-%d %H:%M:%S", localtime(message["timestamp"]))}', value="", inline=False)
        embed.add_field(name=f"Huyết áp tâm thu (sys)", value=f'{message["content"]["sys"]} (mmHg)', inline=True)
        embed.add_field(name=f"Huyết áp tâm trương (dias)", value=f'{message["content"]["dias"]} (mmHg)', inline=True)
        embed.add_field(name=f"Nhịp tim", value=f'{message["content"]["pulse"]} (nhịp/phút)', inline=True)
        embed.add_field(name=f"Nhận xét", value=f'''{getGPTresponse(f'Sys: {message["content"]["sys"]} (mmHg) Dias: {message["content"]["dias"]} (mmHg) Pulse: {message["content"]["pulse"]} (bpm)')}''', inline=False)
        await user.send(embed=embed)

@bot.listen()
async def on_ready():
    scanForMessage.start() # important to start the loop

bot.run(str(os.getenv("DISCORD_BOT_TOKEN")))
