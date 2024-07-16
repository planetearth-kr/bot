import aiohttp
import discord

BOT_TOKEN = ""
API_KEY = ""
ROLE_NAME = "인증됨"

intents = discord.Intents.default()
intents.members = True
bot = discord.Client(intents=intents)
tree = discord.app_commands.CommandTree(bot)

async def fetch_json(session, endpoint, params):
    url = f"https://planetearth.kr/api/{endpoint}"
    try:
        async with session.get(url, params=params) as response:
            response.raise_for_status()
            return await response.json()
    except aiohttp.ClientError as e:
        print(f"HTTP request failed: {e}")
        return None

async def handle_api_response(interaction, json_response, error_message):
    if not json_response:
        await interaction.response.send_message("PlanetEarth API가 응답하지 않습니다. 디스코드 공지를 참고해주세요.")
        return None

    if json_response["status"] == "FAILED":
        code = json_response["error"]["code"]
        if code == "NO_DATA_FOUND":
            await interaction.response.send_message(error_message)
        elif code == "RATE_LIMIT":
            await interaction.response.send_message("봇의 요청이 제한되었습니다.")
        else:
            await interaction.response.send_message("알 수 없는 오류가 발생했습니다.")
        return None

    return json_response["data"][0]

@bot.event
async def on_ready():
    await tree.sync()
    await bot.change_presence(status=discord.Status.online, activity=discord.Game(name="planetearth.kr"))
    print(f"Logged in as {bot.user} (ID: {bot.user.id})")
    print("Joined servers:")
    for guild in bot.guilds:
        print(f"- {guild.name}")

@bot.event
async def on_guild_join(guild):
    print(f"Joined {guild.name}!")

@bot.event
async def on_member_join(member):
    if member.guild.id == 971724292482019359:
        return

    async with aiohttp.ClientSession() as session:
        discord_json = await fetch_json(session, "discord", {"key": API_KEY, "discord": member.id})
        
        if not discord_json or discord_json["status"] == "FAILED":
            error_message = "PlanetEarth API가 응답하지 않습니다." if not discord_json else discord_json["error"].get("message", "알 수 없는 오류가 발생했습니다.")
            await member.guild.system_channel.send(f"{error_message} {member.mention}의 인증에 실패했습니다.")
            return

        await member.edit(nick=discord_json["data"][0]["name"])
        verified_role = discord.utils.get(member.guild.roles, name=ROLE_NAME)
        if verified_role:
            await member.add_roles(verified_role)
        else:
            await member.guild.system_channel.send(f"서버에서 {ROLE_NAME} 역할을 찾을 수 없습니다. {member.mention}에게 역할을 지급하지 못했습니다.")

@tree.command(name="help", description="봇 소개를 확인합니다.")
async def help_command(interaction: discord.Interaction):
    help_message = (
        "## PlanetEarth 공식봇 소개\n\n"
        "PlanetEarth에 관련된 유용한 기능을 제공합니다.\n\n"
        "### 기능\n"
        "```- 새로운 유저가 디스코드 서버에 들어올 때 PlanetEarth에 인증된 유저인지 확인하고, 이름을 닉네임으로 설정합니다.\n"
        "- 서버에 '인증됨' 역할이 있을 경우 자동으로 역할을 지급합니다.```\n\n"
        "### 명령어\n"
        "```/resident - 플레이어 정보를 확인합니다.\n"
        "/town - 마을 정보를 확인합니다.\n"
        "/nation - 국가 정보를 확인합니다.```"
    )
    await interaction.response.send_message(help_message)

@tree.command(name="resident", description="플레이어 정보를 확인합니다.")
@discord.app_commands.describe(name="플레이어 이름을 입력해주세요")
async def resident_command(interaction: discord.Interaction, name: str):
    async with aiohttp.ClientSession() as session:
        resident_data = await handle_api_response(
            interaction,
            await fetch_json(session, "resident", {"key": API_KEY, "name": name}),
            "존재하지 않는 플레이어입니다!"
        )
        if not resident_data:
            return

        town_data = None
        if resident_data["town"]:
            town_data = await handle_api_response(
                interaction,
                await fetch_json(session, "town", {"key": API_KEY, "name": resident_data["town"]}),
                "마을 정보를 가져오는 데 실패했습니다."
            )

    embed = discord.Embed(title=resident_data["name"].replace("_", "\\_"), color=discord.Color.green())
    embed.set_thumbnail(url=f"https://mc-heads.net/avatar/{resident_data['name']}/600.png")
    embed.add_field(name="**최초 접속일**", value=f"<t:{int(resident_data['registered'])//1000}:f>", inline=False)
    embed.add_field(name="**최근 접속일**", value=f"<t:{int(resident_data['lastOnline'])//1000}:f>", inline=False)
    embed.add_field(name="**마을**", value=resident_data["town"].replace("_", "\\_") if resident_data["town"] else "없음", inline=False)
    embed.add_field(name="**국가**", value=town_data["nation"].replace("_", "\\_") if town_data and town_data.get("nation") else "없음", inline=False)

    await interaction.response.send_message(embed=embed)

@tree.command(name="town", description="마을 정보를 확인합니다.")
@discord.app_commands.describe(name="마을 이름을 입력해주세요")
async def town_command(interaction: discord.Interaction, name: str):
    async with aiohttp.ClientSession() as session:
        town_data = await handle_api_response(
            interaction,
            await fetch_json(session, "town", {"key": API_KEY, "name": name}),
            "존재하지 않는 마을입니다!"
        )
        if not town_data:
            return

    embed = discord.Embed(title=town_data["name"].replace("_", "\\_"), color=discord.Color.green())
    embed.add_field(name="**공지**", value=town_data["townBoard"].replace("_", "\\_"), inline=False)
    embed.add_field(name="**시장**", value=town_data["mayor"].replace("_", "\\_"), inline=False)
    embed.add_field(name="**국가**", value=town_data["nation"].replace("_", "\\_") if town_data["nation"] else "없음", inline=False)
    embed.add_field(name="**주민 수**", value=town_data["memberCount"], inline=False)
    embed.add_field(name="**클레임 크기**", value=town_data["claimSize"], inline=False)
    embed.add_field(name="**설립일**", value=f"<t:{int(town_data['registered'])//1000}:f>", inline=False)

    await interaction.response.send_message(embed=embed)

@tree.command(name="nation", description="국가 정보를 확인합니다.")
@discord.app_commands.describe(name="국가 이름을 입력해주세요")
async def nation_command(interaction: discord.Interaction, name: str):
    async with aiohttp.ClientSession() as session:
        nation_data = await handle_api_response(
            interaction,
            await fetch_json(session, "nation", {"key": API_KEY, "name": name}),
            "존재하지 않는 국가입니다!"
        )
        if not nation_data:
            return

    embed = discord.Embed(title=nation_data["name"].replace("_", "\\_"), color=discord.Color.green())
    embed.add_field(name="**공지**", value=nation_data["nationBoard"].replace("_", "\\_"), inline=False)
    embed.add_field(name="**왕**", value=nation_data["leader"].replace("_", "\\_"), inline=False)
    embed.add_field(name="**국민 수**", value=nation_data["memberCount"], inline=False)
    embed.add_field(name="**마을**", value=nation_data["towns"].replace("_", "\\_"), inline=False)
    embed.add_field(name="**동맹**", value=nation_data["allies"].replace("_", "\\_") if nation_data["allies"] else "없음", inline=False)
    embed.add_field(name="**적**", value=nation_data["enemies"].replace("_", "\\_") if nation_data["enemies"] else "없음", inline=False)
    embed.add_field(name="**설립일**", value=f"<t:{int(nation_data['registered'])//1000}:f>", inline=False)

    await interaction.response.send_message(embed=embed)

bot.run(BOT_TOKEN)