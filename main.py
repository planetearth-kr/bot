import aiohttp
import asyncio
import re
import os
import discord
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
ROLE_NAME = "인증됨"

intents = discord.Intents.default()
intents.members = True
bot = discord.Client(intents=intents)
tree = discord.app_commands.CommandTree(bot)

OFFICIAL_GUILDS = {971724292482019359, 1207333375598272553, 929915543337721947}

NAME_PATTERN = re.compile(
    r"(?:P[.\s]?E|PLANETEARTH|𝑃[.\s]?𝐸|𝑃𝐿𝐴𝑁𝐸𝑇𝐸𝐴𝑅𝑇𝐻|Ｐ[.\s]?Ｅ|ＰＬＡＮＥＴＥＡＲＴＨ|𝐏[.\s]?𝐄|플래닛어스|플어)",
    re.IGNORECASE,
)


def esc(text: str) -> str:
    return text.replace("_", "\\_")


def is_valid_server(guild: discord.Guild | None) -> bool:
    if not guild:
        return False
    if guild.id in OFFICIAL_GUILDS:
        return True
    return 7 <= guild.member_count <= 300 and bool(
        NAME_PATTERN.search(guild.name or "")
    )


async def leave_invalid_guild(guild: discord.Guild) -> None:
    print(
        f"Left guild: {guild.name} "
        f"(Members: {guild.member_count}, Reason: invalid name or member count)"
    )
    await guild.leave()


async def check_valid_server(interaction: discord.Interaction) -> bool:
    """Sends an error and leaves if the server is invalid. Returns whether it's valid."""
    if is_valid_server(interaction.guild):
        return True
    await interaction.response.send_message(
        "플래닛어스 관련 디스코드가 아니거나 인원수 조건을 만족하지 않습니다!"
    )
    await leave_invalid_guild(interaction.guild)
    return False


async def fetch_json(session: aiohttp.ClientSession, endpoint: str, params: dict) -> dict | None:
    try:
        async with session.get(f"https://api.planetearth.kr/{endpoint}", params=params) as resp:
            resp.raise_for_status()
            return await resp.json()
    except aiohttp.ClientError as e:
        print(f"HTTP request failed: {e}")
        return None


async def handle_api_response(
    interaction: discord.Interaction, json_response: dict | None, not_found_message: str
) -> dict | None:
    if not json_response:
        await interaction.response.send_message(
            "PlanetEarth API가 응답하지 않습니다. 디스코드 공지를 참고해주세요."
        )
        return None

    if json_response.get("status") == "FAILED":
        code = json_response.get("error", {}).get("code", "UNKNOWN_ERROR")
        messages = {
            "NO_DATA_FOUND": not_found_message,
            "RATE_LIMIT": "봇의 요청이 제한되었습니다.",
        }
        await interaction.response.send_message(
            messages.get(code, "알 수 없는 오류가 발생했습니다.")
        )
        return None

    return json_response.get("data", [None])[0]


async def send_system_message(guild: discord.Guild, message: str) -> None:
    if not guild.system_channel:
        return
    try:
        await guild.system_channel.send(message)
    except discord.errors.Forbidden:
        print(f"Cannot send message in system channel for {guild.name}: Missing permissions.")


@bot.event
async def on_ready():
    await tree.sync()
    await bot.change_presence(
        status=discord.Status.online, activity=discord.Game(name="planetearth.kr")
    )
    print(f"Logged in as {bot.user} (ID: {bot.user.id})\nJoined servers:")
    for guild in bot.guilds:
        valid = is_valid_server(guild)
        print(f"  - {guild.name} ({'Valid' if valid else 'Invalid'})")
        if not valid:
            await leave_invalid_guild(guild)
    print("Successfully started!")


@bot.event
async def on_guild_join(guild: discord.Guild):
    print(f"Joined {guild.name}!")
    if not is_valid_server(guild):
        await leave_invalid_guild(guild)


@bot.event
async def on_member_join(member: discord.Member):
    guild = member.guild
    if not is_valid_server(guild) or guild.id == 971724292482019359:
        return

    async with aiohttp.ClientSession() as session:
        discord_json = await fetch_json(session, "discord", {"discord": member.id})

    if not discord_json or discord_json.get("status") == "FAILED":
        error = (
            "PlanetEarth API가 응답하지 않습니다."
            if not discord_json
            else discord_json.get("error", {}).get("message", "알 수 없는 오류가 발생했습니다.")
        )
        await send_system_message(guild, f"{error} {member.mention}의 인증에 실패했습니다.")
        return

    new_nick = discord_json["data"][0].get("name")
    if new_nick:
        try:
            await member.edit(nick=new_nick)
        except discord.errors.Forbidden:
            await send_system_message(guild, f"{member.mention}의 닉네임을 변경할 권한이 없습니다.")

    verified_role = discord.utils.get(guild.roles, name=ROLE_NAME)
    if not verified_role:
        await send_system_message(
            guild,
            f"서버에서 {ROLE_NAME} 역할을 찾을 수 없습니다. {member.mention}에게 역할을 지급하지 못했습니다.",
        )
        return

    try:
        await member.add_roles(verified_role)
    except discord.errors.Forbidden:
        await send_system_message(guild, f"{member.mention}에게 역할을 지급할 권한이 없습니다.")


@tree.command(name="help", description="봇 소개를 확인합니다.")
async def help_command(interaction: discord.Interaction):
    if not await check_valid_server(interaction):
        return
    await interaction.response.send_message(
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


@tree.command(name="resident", description="플레이어 정보를 확인합니다.")
@discord.app_commands.describe(name="플레이어 이름을 입력해주세요")
async def resident_command(interaction: discord.Interaction, name: str):
    if not await check_valid_server(interaction):
        return

    async with aiohttp.ClientSession() as session:
        resident_json = await fetch_json(session, "resident", {"name": name})
        resident = await handle_api_response(interaction, resident_json, "존재하지 않는 플레이어입니다!")
        if not resident:
            return

        nation = "없음"
        if resident.get("town"):
            town_json = await fetch_json(session, "town", {"name": resident["town"]})
            town = await handle_api_response(interaction, town_json, "마을 정보를 가져오는 데 실패했습니다.")
            if town and town.get("nation"):
                nation = esc(town["nation"])

    embed = discord.Embed(title=esc(resident["name"]), color=discord.Color.green())
    embed.set_thumbnail(url=f"https://mc-heads.net/avatar/{resident['name']}/600.png")
    embed.add_field(name="**최초 접속일**", value=f"<t:{int(resident['registered'])//1000}:f>", inline=False)
    embed.add_field(name="**최근 접속일**", value=f"<t:{int(resident['lastOnline'])//1000}:f>", inline=False)
    embed.add_field(name="**마을**", value=esc(resident["town"]) if resident["town"] else "없음", inline=False)
    embed.add_field(name="**국가**", value=nation, inline=False)
    await interaction.response.send_message(embed=embed)


@tree.command(name="town", description="마을 정보를 확인합니다.")
@discord.app_commands.describe(name="마을 이름을 입력해주세요")
async def town_command(interaction: discord.Interaction, name: str):
    if not await check_valid_server(interaction):
        return

    async with aiohttp.ClientSession() as session:
        town_json = await fetch_json(session, "town", {"name": name})
        town = await handle_api_response(interaction, town_json, "존재하지 않는 마을입니다!")
        if not town:
            return

    embed = discord.Embed(title=esc(town["name"]), color=discord.Color.green())
    embed.add_field(name="**공지**", value=esc(town["townBoard"]), inline=False)
    embed.add_field(name="**시장**", value=esc(town["mayor"]), inline=False)
    embed.add_field(name="**국가**", value=esc(town["nation"]) if town["nation"] else "없음", inline=False)
    embed.add_field(name="**주민 수**", value=str(town["memberCount"]), inline=False)
    embed.add_field(name="**클레임 크기**", value=str(town["claimSize"]), inline=False)
    embed.add_field(name="**설립일**", value=f"<t:{int(town['registered'])//1000}:f>", inline=False)
    await interaction.response.send_message(embed=embed)


@tree.command(name="nation", description="국가 정보를 확인합니다.")
@discord.app_commands.describe(name="국가 이름을 입력해주세요")
async def nation_command(interaction: discord.Interaction, name: str):
    if not await check_valid_server(interaction):
        return

    async with aiohttp.ClientSession() as session:
        nation_json = await fetch_json(session, "nation", {"name": name})
        nation = await handle_api_response(interaction, nation_json, "존재하지 않는 국가입니다!")
        if not nation:
            return

    embed = discord.Embed(title=esc(nation["name"]), color=discord.Color.green())
    embed.add_field(name="**공지**", value=esc(nation["nationBoard"]), inline=False)
    embed.add_field(name="**왕**", value=esc(nation["leader"]), inline=False)
    embed.add_field(name="**국민 수**", value=str(nation["memberCount"]), inline=False)
    embed.add_field(name="**마을**", value=esc(nation["towns"]), inline=False)
    embed.add_field(name="**동맹**", value=esc(nation["allies"]) if nation["allies"] else "없음", inline=False)
    embed.add_field(name="**적**", value=esc(nation["enemies"]) if nation["enemies"] else "없음", inline=False)
    embed.add_field(name="**설립일**", value=f"<t:{int(nation['registered'])//1000}:f>", inline=False)
    await interaction.response.send_message(embed=embed)


bot.run(BOT_TOKEN)
