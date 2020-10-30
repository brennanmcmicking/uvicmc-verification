# Personal imports
from io import BytesIO
from PIL import Image, ImageFont, ImageDraw
import os
from flask import Response
from flask import request
import flask
import requests
import threading
import queue
from discord.ext import tasks, commands
import discord
import secrets


# For the record, these uuids are NOT secrets! They can be accessed by anybody by going onto Discord
# THIS IS NOT THE UVICMC GUILD ID! THIS IS THE DEDOTATED WHAM GUILD ID!! CHANGE IT BEFORE DEPLOYING THIS
UVICMC_GUILDID = 219649098989568000
# THIS IS THE MEMES CHANNEL IN DEDOTATED WHAMMM
MEMES_CHANNEL = 349785662058135553

# Create the discord client object
client = discord.Client()

# Setup # logging
# logging.basicConfig(filename='uvicmc-discordbot.log', level=# logging.DEBUG)


# Discord bot events
@client.event
async def on_ready():
    # logging.info(f'Logged in as \n{client.user.name}\n{client.user.id}\n')
    pass


@client.event
async def on_message(message):
    if message.author == client.user:
        return

    # This is where we link the user's discord account to their netlink account
    if message.content.startswith('!link'):
        # logging.info('!link called')
        # Parse data. I should probably use regular expressions here
        discorduuid = message.author.id
        try:
            mcusername = message.content.split(' ')[1]
        except:
            # If it failed then they didn't provide a valid username
            # logging.error('No username was provided in the !link command')
            await message.channel.send(f'Error: no username provided. Usage: !link <minecraft username>')
            return
        # this is a placeholder just to confirm that the bot works
        await message.channel.send(f'Bot working. Username: {mcusername}')

        # Apparently Colin doesn't want me to do a quick check to see if the username is valid with the Mojang API but
        # that could save him money every time someone sends the wrong username
        '''
        res = await requests.get(f'https://api.uvicmc.net/v1/discord/link?username={mcusername}&discorduuid={discorduuid}')
        if res.status_code == 200:
            message.author.send(
                "An email has been sent to the netlink account associated with that Minecraft username. If you are not a UVic student and have been referred, please tell your referrer to check their email.")
        else:
            message.author.send(res["error"])
        '''


class DiscordBot(threading.Thread):
    def __init__(self, client):
        self.client = client
        super(DiscordBot, self).__init__()

    def run(self):
        # This is the magic. Because this class inherits from threading.Thread,
        # whatever happens in this function is run in a seperate thread
        # This means we can have other processes running at the same time.
        self.client.run(secrets.get_bot_token())

    async def receive_success(self, discorduuid, roleuid):
        # this still needs to be updated to have logging
        # however I tried and it broke it at the role = uvicmc.get_role(...)
        # line so yeah that's weird
        print(f"attempting to give user {discorduuid} role {roleuid}")
        uvicmc = self.client.get_guild(UVICMC_GUILDID)
        print(uvicmc.name)
        member = await uvicmc.fetch_member(discorduuid)
        print(member.name)
        role = uvicmc.get_role(int(roleuid))
        print(role)
        await member.add_roles(role)
        await member.send(f"Gave you the {role} role in {uvicmc.name}")
        print(f"Gave {member.name} {role}")

    async def send_message(self, message):
        print(f'[BRENNAN] got the callback with message: {message}')
        # server = self.client.get_guild(219649098989568000)
        # print(server.name)
        channel = self.client.get_channel(734131788779356300)
        print(channel.name)
        try:
            await channel.send(f'retrieved message from api: {message}')
            print('sent message')
        except Exception as e:
            print('exception in discord bot callback')
            print(e)


class CallbackHandler(commands.Cog):
    def __init__(self, client, discordbot):
        # Here we initialize two queue objects.
        # message_queue is temporary: it will be removed before production
        # role_queue is a queue object that stores all the pending role
        # adds that have been received from the api.
        # we need this queue so that we can synchronously add
        # items to the queue and then asynchronously pop them off
        # the queue.
        self.message_queue = queue.Queue()
        self.role_queue = queue.Queue()
        self.timeout = 1.0/60
        self.discordbot = discordbot
        self.check_for_action.start()

    def queue_message(self, message):
        # logging.info(f'Adding {message} to the message queue')
        self.message_queue.put(message)

    def queue_role(self, uuid, role):
        # Simple line of code: we put the received uuid/role onto the queue
        print(f'Addomg user: {uuid}, role: {role} to the role queue')
        self.role_queue.put([uuid, role])

    @tasks.loop(seconds=1.0)
    async def check_for_action(self):
        try:
            message = self.message_queue.get(timeout=self.timeout)
            print(f'got message from queue')
            await self.discordbot.send_message(message)
        except Exception as e:
            if str(e) != '':
                print('exception in callback handler')
                print(e)

        try:
            # Here we try to see if there is a [role, uuid] object on the queue.
            # If there is, then we pop it off. Otherwise, the queue
            # will timeout and throw an exception. We just catch it and pass.
            # Note that we print the exception if it isn't empty, but
            # that only occurs when some other type of exception is raised
            data = self.role_queue.get(timeout=self.timeout)
            uuid = data[0]
            role = data[1]
            print('got role/uuid from queue')
            await self.discordbot.receive_success(uuid, role)
        except Exception as e:
            if str(e) != '':
                print('exception in callback handler')
                print(e)


# Create the discord bot object and then run it.
discordbot = DiscordBot(client)
discordbot.start()

# Create the callback handler. It will run itself.
cb_handler = CallbackHandler(client, discordbot)

# Create the flask app object
app = flask.Flask(__name__)

# Flask events
@app.route('/api/v1/send_message', methods=['GET'])
def api_message():
    if 'message' in request.args:
        message = str(request.args['message'])
        cb_handler.queue_message(message)
        return ('message success', 200)

    return ('no message provided', 400)


@app.route('/api/v1/give_role', methods=['GET'])
def api_give_role():
    # logging.info('Got role add request')
    key = request.headers.get('X-Api-Key')
    if key is None:
        # logging.warning(
        # 'No api key was provided. This is an error somewhere else')
        return ('some api key error', 401)
    if key == secrets.get_api_key():
        if 'uuid' in request.args and 'role' in request.args:
            uuid = str(request.args['uuid'])
            role = str(request.args['role'])
            cb_handler.queue_role(uuid, role)
            return ('role passed onto discord bot', 200)
        else:
            return ('no uuid or role provided', 400)
    else:
        # logging.warning('An api key was provided, but it was the wrong key.')
        return ('some api key error', 401)


app.run()
