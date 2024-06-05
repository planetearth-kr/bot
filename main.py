import aiohttp
import aioping
import psutil
import discord

BOT_TOKEN = ""

API_KEY = ""

ROLE_NAME = "인증됨"

intents = discord.Intents.default()
intents.members = True

bot = discord.Client(intents=intents)
tree = discord.app_commands.CommandTree(bot)

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
    await tree.sync()
    await bot.change_presence(status=discord.Status.online, activity=discord.Game(name="planetearth.kr"))
    for guild in bot.guilds:
        print(guild.name)
    print(f"Logged in as {bot.user} (ID: {bot.user.id})")

@bot.event
async def on_member_join(member):
    guild = member.guild
    if guild.id != 971724292482019359:
        discord_url = f"https://planetearth.kr/api/discord.php?key={API_KEY}&discord={member.id}"

        async with aiohttp.ClientSession() as session:
            discord_json = await fetch_json(session, discord_url)
            if not discord_json:
                await guild.system_channel.send("PlanetEarth API가 응답하지 않습니다. 디스코드 공지를 참고해주세요.")
                return

            if discord_json["status"] == "FAILED":
                code = discord_json["error"]["code"]
                if code == "NO_DATA_FOUND":
                    await guild.system_channel.send(f"{member.mention} (은)는 PlanetEarth 디스코드에 인증되지 않은 유저입니다.")
                elif code == "RATE_LIMIT":
                    await guild.system_channel.send(f"봇의 요청이 제한되었습니다. {member.mention} 의 인증에 실패했습니다.")
                else:
                    await guild.system_channel.send(f"알 수 없는 오류가 발생했습니다. {member.mention} 의 인증에 실패했습니다.")
                return

            await member.edit(nick=discord_json["data"][0]["name"])

            verified_role = discord.utils.get(guild.roles, name=ROLE_NAME)
            if verified_role:
                await member.add_roles(verified_role)
            else:
                await guild.system_channel.send(f"서버에서 {ROLE_NAME} 역할을 찾을 수 없습니다. {member.mention} 에게 역할을 지급하지 못했습니다.")

@tree.command(name="help", description="봇 소개를 확인합니다.")
async def help(interaction: discord.Interaction):
    await interaction.response.send_message(f"## PlanetEarth 봇 소개\n\nPlanetEarth 에 관련된 유용한 기능을 제공합니다.\n\n### 기능\n```- 새로운 유저가 디스코드 서버에 들어올 때 PlanetEarth 에 인증된 유저인지 확인하고, 이름을 닉네임으로 설정합니다.\n- 서버에 '인증됨' 역할이 있을 경우 자동으로 역할을 지급합니다.```\n\n### 명령어\n```/resident - 플레이어 정보를 확인합니다.\n/town - 마을 정보를 확인합니다.\n/nation - 국가 정보를 확인합니다.```")

@tree.command(name="status", description="봇 상태 확인를 확인합니다.")
async def status(interaction: discord.Interaction):
    if interaction.user.id == 1086117494189723658:
        bot_status = discord.Embed(title="봇 정보", description="PlanetEarth 공식봇 상태를 확인합니다.", color=discord.Color.green())
        bot_status.add_field(name="CPU 사용률", value=f"{psutil.cpu_percent()}%", inline=False)
        bot_status.add_field(name="메모리 사용률", value=f"{psutil.virtual_memory().percent}%", inline=False)
        latency = await aioping.ping("1.1.1.1")
        bot_status.add_field(name="지연시간", value=f"{latency * 1000:.1f}ms", inline=False)
        await interaction.response.send_message(embed=bot_status)
    else:
        await interaction.response.send_message("이 명령어는 사용할 수 없습니다.")

@tree.command(name="resident", description="플레이어 정보를 확인합니다.")
@discord.app_commands.describe(name="플레이어 이름을 입력해주세요")
async def resident(interaction: discord.Interaction, name: str):
    resident_url = f"https://planetearth.kr/api/resident.php?key={API_KEY}&name={name}"

    async with aiohttp.ClientSession() as session:
        resident_json = await fetch_json(session, resident_url)
        if not resident_json:
            await interaction.response.send_message("PlanetEarth API가 응답하지 않습니다. 디스코드 공지를 참고해주세요.")
            return

        if resident_json["status"] == "FAILED":
            code = resident_json["error"]["code"]
            if code == "NO_DATA_FOUND":
                await interaction.response.send_message("존재하지 않는 플레이어입니다!")
            elif code == "RATE_LIMIT":
                await interaction.response.send_message("봇의 요청이 제한되었습니다.")
            else:
                await interaction.response.send_message("알 수 없는 오류가 발생했습니다.")
            return

        data = resident_json["data"][0]
        town_url = f"https://planetearth.kr/api/town.php?key={API_KEY}&name={data['town']}"

        town_json = await fetch_json(session, town_url)
        if not town_json:
            await interaction.response.send_message("PlanetEarth API가 응답하지 않습니다. 디스코드 공지를 참고해주세요.")
            return

        resident_info = discord.Embed(title=data["name"], color=discord.Color.green())
        resident_info.set_thumbnail(url=f"https://mc-heads.net/avatar/{data['name']}/600.png")
        resident_info.add_field(name="**최초 접속일**", value=f"<t:{int(data['registered'])//1000}:f>", inline=False)
        resident_info.add_field(name="**최근 접속일**", value=f"<t:{int(data['lastOnline'])//1000}:f>", inline=False)
        if data["town"]:
            resident_info.add_field(name="**마을**", value=data["town"], inline=False)
            if town_json["data"] and town_json["data"][0].get("nation"):
                resident_info.add_field(name="**국가**", value=town_json["data"][0]["nation"], inline=False)
            else:
                resident_info.add_field(name="**국가**", value="없음", inline=False)
        else:
            resident_info.add_field(name="**마을**", value="없음", inline=False)

        await interaction.response.send_message(embed=resident_info)

@tree.command(name="town", description="마을 정보를 확인합니다.")
@discord.app_commands.describe(name="마을 이름을 입력해주세요")
async def town(interaction: discord.Interaction, name: str):
    town_url = f"https://planetearth.kr/api/town.php?key={API_KEY}&name={name}"

    async with aiohttp.ClientSession() as session:
        town_json = await fetch_json(session, town_url)
        if not town_json:
            await interaction.response.send_message("PlanetEarth API가 응답하지 않습니다. 디스코드 공지를 참고해주세요.")
            return

        if town_json["status"] == "FAILED":
            code = town_json["error"]["code"]
            if code == "NO_DATA_FOUND":
                await interaction.response.send_message("존재하지 않는 마을입니다!")
            elif code == "RATE_LIMIT":
                await interaction.response.send_message("봇의 요청이 제한되었습니다.")
            else:
                await interaction.response.send_message("알 수 없는 오류가 발생했습니다.")
            return

        data = town_json["data"][0]
        town_info = discord.Embed(title=data["name"], color=discord.Color.green())
        town_info.add_field(name="**공지**", value=data["townBoard"], inline=False)
        town_info.add_field(name="**시장**", value=data["mayor"], inline=False)
        if data["nation"]:
            town_info.add_field(name="**국가**", value=data["nation"], inline=False)
        else:
            town_info.add_field(name="**국가**", value="없음", inline=False)
        town_info.add_field(name="**주민 수**", value=data["memberCount"], inline=False)
        town_info.add_field(name="**클레임 크기**", value=data["claimSize"], inline=False)
        town_info.add_field(name="**설립일**", value=f"<t:{int(data['registered'])//1000}:f>", inline=False)

        await interaction.response.send_message(embed=town_info)

@tree.command(name="nation", description="국가 정보를 확인합니다.")
@discord.app_commands.describe(name="국가 이름을 입력해주세요")
async def nation(interaction: discord.Interaction, name: str):
    nation_url = f"https://planetearth.kr/api/nation.php?key={API_KEY}&name={name}"

    async with aiohttp.ClientSession() as session:
        nation_json = await fetch_json(session, nation_url)
        if not nation_json:
            await interaction.response.send_message("PlanetEarth API가 응답하지 않습니다. 디스코드 공지를 참고해주세요.")
            return

        if nation_json["status"] == "FAILED":
            code = nation_json["error"]["code"]
            if code == "NO_DATA_FOUND":
                await interaction.response.send_message("존재하지 않는 국가입니다!")
            elif code == "RATE_LIMIT":
                await interaction.response.send_message("봇의 요청이 제한되었습니다.")
            else:
                await interaction.response.send_message("알 수 없는 오류가 발생했습니다.")
            return

        data = nation_json["data"][0]
        nation_info = discord.Embed(title=data["name"], color=discord.Color.green())
        nation_info.add_field(name="**공지**", value=data["nationBoard"], inline=False)
        nation_info.add_field(name="**왕**", value=data["leader"], inline=False)
        nation_info.add_field(name="**국민 수**", value=data["memberCount"], inline=False)
        nation_info.add_field(name="**마을**", value=data["towns"], inline=False)
        if data["allies"]:
            nation_info.add_field(name="**동맹**", value=data["allies"], inline=False)
        else:
            nation_info.add_field(name="**동맹**", value="없음", inline=False)
        if data["enemies"]:
            nation_info.add_field(name="**적**", value=data["enemies"], inline=False)
        else:
            nation_info.add_field(name="**적**", value="없음", inline=False)
        nation_info.add_field(name="**설립일**", value=f"<t:{int(data['registered'])//1000}:f>", inline=False)

        await interaction.response.send_message(embed=nation_info)

bot.run(BOT_TOKEN)
