import secrets
import discord
from discord.ext import tasks, commands
import requests
import queue
import threading

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

    async def receive_success(self, discorduuid, roleuid):
        print(f"attempting to give user {discorduuid} role {roleuid}")
        uvicmc = client.get_guild(UVICMC_GUILDID)
        print(uvicmc.name)
        member = await uvicmc.fetch_member(discorduuid)
        print(member.name)
        role = uvicmc.get_role(int(roleuid))
        print(role)
        await member.add_roles(role)
        await member.send(f"Gave you the {role} role in {uvicmc.name}")
        print(f"Gave {member.name} {role}")

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


class CallbackHandler(commands.Cog):
    def __init__(self, client, discordbot):
        self.message_queue = queue.Queue()
        self.role_queue = queue.Queue()
        self.timeout = 1.0/60
        self.discordbot = discordbot
        self.check_for_action.start()

    def queue_message(self, message):
        print(f"got {message} on the thread")
        self.message_queue.put(message)

    def queue_role(self, uuid, role):
        print(f"got user: {uuid} and role: {role}")
        self.role_queue.put([uuid, role])

    @tasks.loop(seconds=1.0)
    async def check_for_action(self):
        try:
            message = self.message_queue.get(timeout=self.timeout)
            print(f"got message from queue")
            await self.discordbot.send_message(message)
        except Exception as e:
            if str(e) != "":
                print("exception in callback handler")
                print(e)

        try:
            data = self.role_queue.get(timeout=self.timeout)
            uuid = data[0]
            role = data[1]
            print("got role/uuid from queue")
            await self.discordbot.receive_success(uuid, role)
        except Exception as e:
            if str(e) != "":
                print("exception in callback handler")
                print(e)


discordbot = DiscordBot(client)
discordbot.start()

cb_handler = CallbackHandler(client, discordbot)

app = flask.Flask(__name__)


@app.route('/api/v1/send_message', methods=['GET'])
def api_message():
    print("received api call")
    if 'message' in request.args:
        message = str(request.args['message'])
        cb_handler.queue_message(message)
        return 'message success'

    return 'message failure'


@app.route('/api/v1/give_role', methods=['GET'])
def api_():
    print("received api call")
    if 'uuid' in request.args and 'role' in request.args:
        uuid = str(request.args['uuid'])
        role = str(request.args['role'])
        cb_handler.queue_role(uuid, role)
        return 'role passed onto discord bot'

    return 'role failure'


print("attempting to start api")
app.run()
