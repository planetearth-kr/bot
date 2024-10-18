import aiohttp
import discord
import re

BOT_TOKEN = ""
API_KEY = ""
ROLE_NAME = "인증됨"

intents = discord.Intents.default()
intents.members = True
bot = discord.Client(intents=intents)
tree = discord.app_commands.CommandTree(bot)

def is_valid_server(guild):
    pattern = r'P[.\s]?E|PLANETEARTH|𝑃[.\s]?𝐸|𝑃𝐿𝐴𝑁𝐸𝑇𝐸𝐴𝑅𝑇𝐻|Ｐ[.\s]?Ｅ|ＰＬＡＮＥＴＥＡＲＴＨ|𝐏[.\s]?𝐄|플래닛어스|플어'
    return bool(re.search(pattern, guild.name, re.IGNORECASE))

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

    if json_response.get("status") == "FAILED":
        code = json_response.get("error", {}).get("code", "UNKNOWN_ERROR")
        if code == "NO_DATA_FOUND":
            await interaction.response.send_message(error_message)
        elif code == "RATE_LIMIT":
            await interaction.response.send_message("봇의 요청이 제한되었습니다.")
        else:
            await interaction.response.send_message("알 수 없는 오류가 발생했습니다.")
        return None

    return json_response.get("data", [None])[0]

@bot.event
async def on_ready():
    await tree.sync()
    await bot.change_presence(status=discord.Status.online, activity=discord.Game(name="planetearth.kr"))
    print(f"Logged in as {bot.user} (ID: {bot.user.id})")
    print("Joined servers:")
    for guild in bot.guilds:
        print(f"- {guild.name} ({'Valid' if is_valid_server(guild) else 'Invalid'})")

@bot.event
async def on_guild_join(guild):
    print(f"Joined {guild.name}!")

@tree.command(name="help", description="봇 소개를 확인합니다.")
async def help_command(interaction: discord.Interaction):
    if not is_valid_server(interaction.guild):
        await interaction.response.send_message("플래닛어스 관련 디스코드에서만 사용할 수 있습니다!")
        return

    help_message = (
        "## PlanetEarth 공식봇 소개\n\n"
        "PlanetEarth에 관련된 유용한 기능을 제공합니다.\n\n"
        "### 기능\n"
        "```- 준비중\n"
        "### 명령어\n"
        "```/resident - 플레이어 정보를 확인합니다.\n"
        "/town - 마을 정보를 확인합니다.\n"
        "/nation - 국가 정보를 확인합니다.```"
    )
    await interaction.response.send_message(help_message)

@tree.command(name="resident", description="플레이어 정보를 확인합니다.")
@discord.app_commands.describe(name="플레이어 이름을 입력해주세요")
async def resident_command(interaction: discord.Interaction, name: str):
    if not is_valid_server(interaction.guild):
        await interaction.response.send_message("플래닛어스 관련 디스코드에서만 사용할 수 있습니다!")
        return

    async with aiohttp.ClientSession() as session:
        resident_data = await handle_api_response(
            interaction,
            await fetch_json(session, "resident", {"key": API_KEY, "name": name}),
            "존재하지 않는 플레이어입니다!"
        )
        if not resident_data:
            return

        town_data = None
        if resident_data.get("town"):
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
    if not is_valid_server(interaction.guild):
        await interaction.response.send_message("플래닛어스 관련 디스코드에서만 사용할 수 있습니다!")
        return

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
    embed.add_field(name="**주민 수**", value=str(town_data["memberCount"]), inline=False)
    embed.add_field(name="**클레임 크기**", value=str(town_data["claimSize"]), inline=False)
    embed.add_field(name="**설립일**", value=f"<t:{int(town_data['registered'])//1000}:f>", inline=False)

    await interaction.response.send_message(embed=embed)

@tree.command(name="nation", description="국가 정보를 확인합니다.")
@discord.app_commands.describe(name="국가 이름을 입력해주세요")
async def nation_command(interaction: discord.Interaction, name: str):
    if not is_valid_server(interaction.guild):
        await interaction.response.send_message("플래닛어스 관련 디스코드에서만 사용할 수 있습니다!")
        return

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
    embed.add_field(name="**국민 수**", value=str(nation_data["memberCount"]), inline=False)
    embed.add_field(name="**마을**", value=nation_data["towns"].replace("_", "\\_"), inline=False)
    embed.add_field(name="**동맹**", value=nation_data["allies"].replace("_", "\\_") if nation_data["allies"] else "없음", inline=False)
    embed.add_field(name="**적**", value=nation_data["enemies"].replace("_", "\\_") if nation_data["enemies"] else "없음", inline=False)
    embed.add_field(name="**설립일**", value=f"<t:{int(nation_data['registered'])//1000}:f>", inline=False)

    await interaction.response.send_message(embed=embed)

bot.run(BOT_TOKEN)
