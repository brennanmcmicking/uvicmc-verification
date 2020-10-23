import secrets
import discord
from discord.ext import tasks, commands
from datetime import datetime
import requests
import queue
import threading
import asyncio

import flask
from flask import request

# THIS IS NOT THE UVICMC GUILD ID! THIS IS THE DEDOTATED WHAM GUILD ID!! CHANGE IT BEFORE DEPLOYING THIS
UVICMC_GUILDID = 219649098989568000

client = discord.Client()

@client.event
async def on_ready():
    print(f'Logged in as \n{client.user.name}\n{client.user.id}\n')


@client.event
async def on_message(message):
    if message.author != client.user:
        if message.content.startswith("!link"):
            discorduuid = message.author.id
            mcusername = message.content.split(' ')[1]
            await message.channel.send(f"bot working. username: {mcusername}")
            '''
            res = await requests.get(f"https://api.uvicmc.net/v1/discord/link?username={mcusername}&discorduuid={discorduuid}")
            if res.status_code == 200:
                message.author.send("An email has been sent to the netlink account associated with that Minecraft username. If you are not a UVic student and have been referred, please tell your referrer to check their email.")
            else:
                message.author.send(res["error"])
            '''

class DiscordBot(threading.Thread):
    def __init__(self, client):
        self.client = client
        super(DiscordBot, self).__init__()

    def run(self):
        self.client.run(secrets.get_bot_token())
    
    async def send_message(self, message):
        print(f"[BRENNAN] got the callback with message: {message}")
        # server = self.client.get_guild(219649098989568000)
        # print(server.name)
        channel = self.client.get_channel(734131788779356300)
        print(channel.name)
        try:
            await channel.send(f"retrieved message from api: {message}")
            print("sent message")
        except Exception as e:
            print("exception in discord bot callback")
            print(e)
    
    def callback(self, message):
        loop = asyncio.new_event_loop()
        loop.run_until_complete(send_message(message))


class CallbackHandler(commands.Cog):
    def receive_success(self, discorduuid, roleuid):
        uvicmc = client.get_guild(UVICMC_GUILDID)
        member = uvicmc.get_member(discorduuid)
        role = uvicmc.get_role(roleuid)
        member.add_roles(role)

    def __init__(self, client, discordbot):
        threading.Thread.__init__(self)
        self.q = queue.Queue()
        self.timeout = 1.0/60
        self.discordbot = discordbot
        self.check_for_message.start()

    def OnThread(self, message):
        print(f"got {message} on the thread")
        self.discordbot.q.put(message)

    @tasks.loop(seconds=5.0)
    async def check_for_message(self):
        print("starting while loop")
        while True:
            try:
                message = self.q.get(timeout=self.timeout)
                print(f"popped {message} off queue")
                # asyncio.run_coroutine_threadsafe(self.discordbot.callback(message), self.discordbot.loop)
                # asyncio.run(self.callback(message))
                self.discordbot.callback(message)
            except Exception as e:
                if str(e) != "":
                    print("exception in callback handler")
                    print(e)



async def log(eventmsg):
    await client.wait_until_ready()

    if not client.is_closed():
        try:
            with open("log.txt", "a") as f:
                f.write(f"[{datetime.now()}]: {eventmsg}\n")
        except Exception as e:
            print(str(e))
            

# threading.Thread(target=client.run(secrets.get_bot_token()), daemon=True)

discordbot = DiscordBot(client)
discordbot.start()

handler = CallbackHandler(client, discordbot)
handler.start()

'''
            # the user wants to link their discord to their netlink id in the database; we must send another verification email
            mcusername = message.content.split(' ')[1]
            await log(f"Received minecraft username: {mcusername}")
            res = requests.get(
                f"https://api.mojang.com/users/profiles/minecraft/{mcusername}").json()
            mcuuid = res['id']
            await log(f"Got uuid of {mcusername}: {mcuuid}")
            # now we find the associated netlink email in the database, as well as the "referred" flag
            netlink = "brennanmcmicking@uvic.ca"  # for now we just hardcode it
            referred = False  # this is hardcoded ONLY FOR NOW as well
            await log(f"Got netlink email associated with {mcusername}: {netlink}")
            discordid = message.author.id
            await log(f"Got discord id: {discordid}")
            encoded_jwt = jwt.encode(
                {'mcuuid': mcuuid, 'discordid': discordid, 'referred': referred}, secrets.get_jwt_secret(), algorithm='HS256')
            await log("Encoded payload")
            s = SMTP(host='smtp.gmail.com', port=587)
            await log("Connected to SMTP server")
            s.starttls()
            s.login(secrets.get_email_username(), secrets.get_email_password())
            await log("logged into brennanbottester@gmail.com")
            msg = MIMEMultipart()
            msg['From'] = 'brennanbottester@gmail.com'
            msg['To'] = netlink
            msg['Subject'] = "UVicMC Discord-Minecraft Verification"

            body = f"""
                <html>
                    <head />
                    <body>
                        Please <a href=https://www.uvicmc.club/link?jwt={encoded_jwt}>click this link</a> to connect discord account {message.author} with Minecraft user {mcusername}
                    </body>
                </html>
            """
            msg.attach(MIMEText(body, 'html'))

            await log("Succesfully created message object")

            s.send_message(msg)
            if mcuuid in pending:
                await message.author.send(
                    "You are already pending for discord verification. The email has been sent again. Please check your netlink email (or tell your referrer to check their email)")
                await log(f"User {message.author.id} resent verification message; awaiting verificationd")
            else:
                pending.append(mcuuid)
                message.author.send(
                    "Sent verification email! Please check your netlink email (or tell your referrer to check their email) (webmail.uvic.ca)")
                await log("Sent message; awaiting verification")
'''

app = flask.Flask(__name__)
# app.config["DEBUG"] = True

@app.route('/api/v1/send_message', methods=['GET'])
def api_message():
    print("received api call")
    if 'message' in request.args:
        message = str(request.args['message'])
        # print(f"[BRENNAN] got the callback with message: {message}")
        handler.OnThread(message)
        # discordbot.callback(msg)
        return 'success'
    
    return 'failure'

print("attempting to start api")
app.run()

'''
threading.Thread(target=app.run())

print("running discord client")
client.run(secrets.get_bot_token())
'''