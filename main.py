from time import strftime, localtime
import os

# firebase part
import firebase_admin
from firebase_admin import db 

cred_obj = firebase_admin.credentials.Certificate('creds.json')
default_app = firebase_admin.initialize_app(cred_obj, {
    'databaseURL': os.getenv("RTDB_TOKEN")
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
        await ctx.send(f"A user has been register for device {id}")
    else:
        exec(f'''count{id} = 1
def func{id}(event):
    global count{id}, pendingMessage
    if (count{id} == 0):
        userid = {ctx.message.author.id}
        data = event.data.split(";")
        timestamp = event.path[1:]
        pendingMessage.append({{"id": userid, "timestamp": int(timestamp), "content": {{"sys": data[0], "dias": data[1], "pulse": data[2]}}}})
        print(pendingMessage)
        print("done")
    else: count{id} = 0
firebase_admin.db.reference('/{id}/').listen(func{id})
        ''')
        idList.append(id)
        await ctx.send(f"Registered listener {user.mention} for device {id}")

@tasks.loop(seconds=5)
async def scanForMessage():
    print(len(pendingMessage))
    while (len(pendingMessage) != 0):
        message = pendingMessage.pop()
        user = await bot.fetch_user(message["id"])
        await user.send(f'''Thời gian: {strftime('%Y-%m-%d %H:%M:%S', localtime(message["timestamp"]))}
Sys: {message["content"]["sys"]}
Dias: {message["content"]["dias"]}
Pulse: {message["content"]["pulse"]}
''')
        
@bot.listen()
async def on_ready():
    scanForMessage.start() # important to start the loop

bot.run(os.getenv("DISCORD_BOT_TOKEN"))
