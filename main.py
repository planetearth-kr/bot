import aiohttp
import discord
from discord.ext import commands

BOT_TOKEN = ""

API_KEY = ""

ROLE_ID = ""

intents = discord.Intents.default()
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

async def fetch_json(session, url):
    try:
        async with session.get(url) as response:
            response.raise_for_status()
            return await response.json()
    except aiohttp.ClientError as e:
        print(f"HTTP request failed: {e}")
        return None

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user} (ID: {bot.user.id})")

@bot.event
async def on_member_join(member):
    guild = member.guild

    discord_url = f"https://planetearth.kr/api/discord.php?key={API_KEY}&discord={member.id}"

    async with aiohttp.ClientSession() as session:
        discord_json = await fetch_json(session, discord_url)
        if not discord_json:
            await guild.system_channel.send("PlanetEarth 서버가 응답하지 않습니다. 디스코드 공지를 참고해주세요.")
            return

        if discord_json["status"] == "FAILED":
            code = discord_json["error"]["code"]

            if code == "NO_DATA_FOUND":
                await guild.system_channel.send(f"{member.mention} (은)는 PlanetEarth 디스코드에 인증되지 않은 유저입니다.")
            elif code == "RATE_LIMIT":
                await guild.system_channel.send("봇의 요청이 제한되었습니다.")
            else:
                await guild.system_channel.send("알 수 없는 오류가 발생했습니다.")
            return

        ign = discord_json["data"][0]["name"]
        role = discord.utils.get(guild.roles, id=int(ROLE_ID))

        if role:
            await member.add_roles(role)
            await member.edit(nick=ign)
        else:
            await guild.system_channel.send(f"역할을 찾을 수 없습니다. {member.mention} 에게 역할을 지급하지 못했습니다.")
        return

bot.run(BOT_TOKEN)
