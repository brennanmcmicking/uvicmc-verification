# NzM0MTIxODA2MzY5MzkwNzA0.XxNGNQ.ufsJIGFmuSOk8PuoNx2r9IMPhRQ

import discord
from datetime import datetime
import requests
import jwt
from smtplib import SMTP
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

pending = []
PORT = 8000
# THIS IS NOT THE UVICMC GUILD ID! THIS IS THE DEDOTATED WHAM GUILD ID!! CHANGE IT BEFORE DEPLOYING THIS
UVICMC_GUILDID = 219649098989568000


# Now we must create a listen server for the web client to send back when the client clicks the link. All we need to know is when it succeeded.
# When we get that response, we find out whether the player is a referral or not. Then we

# let's make a dummy function so that we can write the actual role-giving code right now

def receive_success(data):
    uvicmc = client.get_guild(UVICMC_GUILDID)
    # DECODE DATA
    data = {'discordid': 210555928158666753, 'referred': False}
    member = uvicmc.get_member(data['discordid'])

    if data['referred']:
        # give the user the REFERRED role
        # THIS IS NOT THE ROLE ID IN UVICMC! THIS IS FOR DEDOTATED WHAM. I HAVE DONE THIS FOR TESTING PURPOSES
        referred_role = uvicmc.get_role(749553337057280033)
        member.add_roles(referred_role)
    else:
        # give the user the UVIC STUDENT role
        # THIS IS NOT THE ROLE ID IN UVICMC! THIS IS FOR DEDOTATED WHAM. I HAVE DONE THIS FOR TESTING PURPOSES
        uvic_role = uvicmc.get_role(749553275946139678)
        member.add_roles(uvic_role)


async def log(eventmsg):
    await client.wait_until_ready()

    if not client.is_closed():
        try:
            with open("log.txt", "a") as f:
                f.write(f"[{datetime.now()}]: {eventmsg}\n")
        except Exception as e:
            print(e)

client = discord.Client()


@client.event
async def on_ready():
    print(f'Logged in as \n{client.user.name}\n{client.user.id}\n')


@client.event
async def on_message(message):
    if message.author != client.user:
        if message.content.startswith("!link"):
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
                {'mcuuid': mcuuid, 'discordid': discordid, 'referred': referred}, 'secret', algorithm='HS256')
            await log("Encoded payload")
            s = SMTP(host='smtp.gmail.com', port=587)
            await log("Connected to SMTP server")
            s.starttls()
            s.login('brennanbottester', 'EMAIL_PASSWORD')
            await log("logged into brennanbottester@gmail.com")
            msg = MIMEMultipart()
            msg['From'] = 'brennanbottester@gmail.com'
            msg['To'] = netlink
            msg['Subject'] = "UVicMC Discord-Minecraft Verification"

            body = f"""
                <html>
                    <head />
                    <body>
                        Please <a href=https://api.uvicmc.club/link?jwt={encoded_jwt}>click this link</a> to connect discord account {message.author} with Minecraft user {mcusername}"
                    </body>
                </html>
            """
            msg.attach(MIMEText(body, 'html'))

            await log("Succesfully created message object")

            s.send_message(msg)
            pending.append(mcuuid)
            if mcuuid in pending:
                await message.author.send(
                    "You are already pending for discord verification. The email has been sent again. Please check your netlink email (or tell your referrer to check their email)")
                await log(f"User {message.author.id} resent verification message; awaiting verificationd")
            else:
                message.author.send(
                    "Sent verification email! Please check your netlink email (or tell your referrer to check their email) (webmail.uvic.ca)")
                await log("Sent message; awaiting verification")

client.run("BOT_TOKEN")
