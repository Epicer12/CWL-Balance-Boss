git config --global user.name "Hasun Tisera"
git config --global user.email "hasuntissera12epicer@gmail.com"

import discord
from discord.ext import commands
import coc
from dotenv import load_dotenv
import os
import logging
import asyncio
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import re

# Setup logging to discord.log
handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
logging.getLogger('').addHandler(handler)
logging.getLogger('').setLevel(logging.INFO)

# Emoji mappings
HERO_EMOJIS = {
    'Barbarian King': '<:BarbarianKing:1371194900636500089>',
    'Archer Queen': '<:ArcherQueen:1371194890091892796>',
    'Minion Prince': '<:MinionPrince:1371194909213855805>',
    'Grand Warden': '<:GrandWarden:1371194905011163149>',
    'Royal Champion': '<:RoyalChampion:1371194913177342175>'    
}

TOWN_HALL_EMOJIS = {
    0: '<:TownHall1:1371194916604084394>',
    1: '<:TownHall1:1371194916604084394>',
    2: '<:TownHall2:1371194919837765822>',
    3: '<:TownHall3:1371194924237721681>',
    4: '<:TownHall4:1371194928486551562>',
    5: '<:TownHall5:1371194932823330947>',
    6: '<:TownHall6:1371194936896262245>',
    7: '<:TownHall7:1371194941404872734>',
    8: '<:TownHall8:1371194945679134811>',
    9: '<:TownHall9:1371194950171099229>',
    10: '<:TownHall10:1371194955179102308>',
    11: '<:TownHall11:1371194959281000528>',
    12: '<:TownHall12:1371194962426986696>',
    13: '<:TownHall13:1371194967044915210>',
    14: '<:TownHall14:1371194970165477437>',
    15: '<:TownHall15:1371194974435016926>',
    16: '<:TownHall16:1371194979166195723>',
    17: '<:TownHall17:1371194983423414322>'
}

TROPHY_LEAGUE_EMOJIS = {
    (0, 799): '<:Icon_Bronze:1371820654831341578>',
    (800, 1399): '<:Icon_Silver:1371820651677220925>',
    (1400, 1999): '<:Icon_Gold:1371820648220983337>',
    (2000, 2599): '<:Icon_Crystal:1371820644785983689>',
    (2600, 3199): '<:Icon_Master:1371820640545275975>',
    (3200, 4099): '<:Icon_Champion:1371820636695040091>',
    (4100, 4999): '<:Icon_Titan:1371820631892426794>',
    (5000, float('inf')): '<:Icon_Legend:1371820627350130718>'
}

# Load environment variables
load_dotenv()
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
COC_EMAIL = os.getenv('COC_EMAIL')
COC_PASSWORD = os.getenv('COC_PASSWORD')

# Single line to switch between local and public
API_BASE_URL = 'https://api.clashofclans.com/v1'  # Change to 'https://proxy.royaleapi.dev/v1' for public hosting

# Initialize bot with Message Content Intent
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix='!', intents=intents)

# Initialize CoC client
coc_client = None

# Initialize Google Sheets client
scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
creds = ServiceAccountCredentials.from_json_keyfile_name('service_account.json', scope)
gs_client = gspread.authorize(creds)

# Store sheet URL
sheet_url = None

async def init_coc_client():
    global coc_client
    try:
        logging.info("Initializing CoC client...")
        coc_client = coc.Client(base_url=API_BASE_URL)
        await coc_client.login(COC_EMAIL, COC_PASSWORD)
        logging.info("CoC client initialized successfully")
    except Exception as e:
        logging.error(f"Failed to initialize CoC client: {e}")
        coc_client = None

@bot.event
async def on_ready():
    logging.info(f'Bot logged in as {bot.user}')
    await init_coc_client()

async def get_sheet_data(url):
    """Fetch data from Google Sheet."""
    try:
        match = re.match(r'https://docs\.google\.com/spreadsheets/d/([a-zA-Z0-9-_]+)/', url)
        if not match:
            logging.error(f"Invalid sheet URL format: {url}")
            return None
        sheet_id = match.group(1)
        worksheet = gs_client.open_by_key(sheet_id).sheet1
        data = worksheet.get_all_records()
        return [
            {
                'discord_id': str(row['ID']).strip(),
                'tag': str(row['TAG']).strip().upper(),
                'name': str(row['NAME']).strip(),
                'clan': str(row['CLAN']).strip(),
                'town_hall': str(row['Town-Hall']).strip()
            }
            for row in data if str(row['ID']).strip() and str(row['TAG']).strip().startswith('#')
        ]
    except Exception as e:
        logging.error(f"Failed to fetch sheet data: {e}")
        return None

@bot.command()
async def update_all(ctx, *, link):
    """Verify Google Sheet access and store URL."""
    global sheet_url
    if not coc_client:
        await ctx.send("CoC API client not initialized. Check logs.")
        return

    data = await get_sheet_data(link)
    if data is None:
        embed = discord.Embed(title="Error", description="Failed to access Google Sheet. Check URL or permissions.", color=discord.Color.red())
        await ctx.send(embed=embed)
        return

    sheet_url = link  # Store the sheet URL
    embed = discord.Embed(
        title="Success",
        description=f"Verified access to sheet with {len(data)} valid rows.",
        color=discord.Color.green()
    )
    embed.set_footer(text="CWL Balance Boss")
    await ctx.send(embed=embed)
    logging.info(f"Verified sheet with {len(data)} rows: {link}")

@bot.command()
async def profile(ctx, user: discord.User = None):
    """Show all CoC accounts linked to a Discord user."""
    if not coc_client:
        await ctx.send("CoC API client not initialized. Check logs.")
        return

    if not sheet_url:
        embed = discord.Embed(title="Error", description="No sheet URL set. Run !update_all first.", color=discord.Color.red())
        await ctx.send(embed=embed)
        return

    user = user or ctx.author
    discord_id = str(user.id)

    data = await get_sheet_data(sheet_url)
    if data is None:
        embed = discord.Embed(title="Error", description="Failed to access Google Sheet.", color=discord.Color.red())
        await ctx.send(embed=embed)
        return

    user_accounts = [row for row in data if row['discord_id'] == discord_id]
    embed = discord.Embed(title=f"{user.name}'s Profile", color=discord.Color.blue(), timestamp=ctx.message.created_at)
    if not user_accounts:
        embed.description = "No Clash of Clans accounts linked to this user."
    else:
        try:
            tags = [row['tag'] for row in user_accounts]
            players = []
            async for player in coc_client.get_players(tags):
                players.append(player)
            account_list = "\n".join([f"{TOWN_HALL_EMOJIS.get(player.town_hall, '')} {player.name} - ({player.tag})" for player in players])
            embed.add_field(name="Linked Accounts", value=account_list, inline=False)
        except coc.errors.NotFound:
            embed.description = "Some accounts could not be found."
            logging.error(f"Some accounts not found for user {discord_id}")
        except Exception as e:
            embed.description = f"Error fetching accounts: {str(e)}"
            logging.error(f"Error fetching accounts for user {discord_id}: {e}")

    embed.set_footer(text="CWL Balance Boss")
    await ctx.send(embed=embed)

@bot.command()
async def player(ctx, *, tag: str):
    """Show profile of a CoC account by tag."""
    if not coc_client:
        await ctx.send("CoC API client not initialized. Check logs.")
        return

    if not sheet_url:
        embed = discord.Embed(title="Error", description="No sheet URL set. Run !update_all first.", color=discord.Color.red())
        await ctx.send(embed=embed)
        return

    tag = tag.strip().upper()
    if not tag.startswith('#'):
        tag = f"#{tag}"

    data = await get_sheet_data(sheet_url)
    if data is None:
        embed = discord.Embed(title="Error", description="Failed to access Google Sheet.", color=discord.Color.red())
        await ctx.send(embed=embed)
        return

    account = next((row for row in data if row['tag'] == tag), None)
    embed = discord.Embed(color=discord.Color.green(), timestamp=ctx.message.created_at)
    if not account:
        embed.title = "Error"
        embed.description = f"No account found with tag {tag}."
        await ctx.send(embed=embed)
        logging.error(f"No account found with tag {tag}")
        return

    try:
        player = await coc_client.get_player(tag)
        embed.title = f"{player.name} - {player.tag}"

        # Member Info field
        league_emoji = next(emoji for (min_trophies, max_trophies), emoji in TROPHY_LEAGUE_EMOJIS.items() if min_trophies <= player.trophies <= max_trophies)
        clan_info = "Clan: No Clan"
        if player.clan:
            clan_tag = player.clan.tag.lstrip('#')
            clan_info = f"[Clan: {player.clan.name}](https://link.clashofclans.com/en?action=OpenClanProfile&tag={clan_tag})"
        member_info = (
            f"{TOWN_HALL_EMOJIS.get(player.town_hall, '')} Town Hall: {player.town_hall}\n"
            f"<:Icon_Clan:1371824433492135966> {clan_info}\n"
            f"{league_emoji} Trophies: {player.trophies}"
        )
        embed.add_field(name="Member Info", value=member_info, inline=False)

        # Hero levels (single field, emoji and level only, one line)
        heroes = {hero.name: hero.level for hero in player.heroes}
        hero_display = [
            f"{emoji} {heroes[hero_name]}"
            for hero_name, emoji in HERO_EMOJIS.items()
            if hero_name in heroes
        ]
        hero_value = "  ".join(hero_display) if hero_display else "None"
        embed.add_field(name="Hero Levels", value=hero_value, inline=False)

        # Rushed percentage
        expected_hero_levels = {
            7: {'Barbarian King': 5},
            9: {'Barbarian King': 30, 'Archer Queen': 30},
            11: {'Barbarian King': 50, 'Archer Queen': 50, 'Grand Warden': 20},
            13: {'Barbarian King': 75, 'Archer Queen': 75, 'Grand Warden': 50, 'Royal Champion': 25},
            15: {'Barbarian King': 85, 'Archer Queen': 85, 'Grand Warden': 60, 'Royal Champion': 35},
            17: {'Barbarian King': 95, 'Archer Queen': 95, 'Grand Warden': 70, 'Royal Champion': 45, 'Minion Prince': 20}
        }
        rush_scores = []
        th_level = player.town_hall
        for th, levels in sorted(expected_hero_levels.items(), reverse=True):
            if th_level >= th:
                for hero_name, expected_level in levels.items():
                    if hero_name in heroes:
                        actual_level = heroes[hero_name]
                        rush_score = max(0, (expected_level - actual_level) / expected_level)
                        rush_scores.append(rush_score)
                break
        rushed_percentage = (sum(rush_scores) / len(rush_scores) * 100) if rush_scores else 0
        embed.add_field(name="Rushed Percentage", value=f"Rushed: {rushed_percentage:.2f}%", inline=False)

        # Discord Username (pinged mention)
        discord_info = f"<@{account['discord_id']}>" if account['discord_id'] else "Not linked"
        embed.add_field(name="Discord Username", value=discord_info, inline=False)

        embed.set_footer(text="CWL Balance Boss")
        await ctx.send(embed=embed)
    except coc.errors.NotFound:
        embed.title = "Error"
        embed.description = f"No account found with tag {tag}."
        await ctx.send(embed=embed)
        logging.error(f"No account found with tag {tag}")
    except Exception as e:
        embed.title = "Error"
        embed.description = f"Failed to fetch player: {str(e)}"
        await ctx.send(embed=embed)
        logging.error(f"Failed to fetch player {tag}: {e}")

@bot.command()
async def claninfo(ctx, clan_tag):
    """Fetches clan info for a given clan tag (e.g., #XYZ123)"""
    if not coc_client:
        await ctx.send("CoC API client not initialized. Check logs.")
        return
    try:
        clan_tag = coc.utils.correct_tag(clan_tag)
        clan = await coc_client.get_clan(clan_tag)
        embed = discord.Embed(title=clan.name, description=clan.description, color=discord.Color.blue())
        embed.add_field(name="Tag", value=clan.tag)
        embed.add_field(name="Level", value=clan.level)
        embed.add_field(name="Members", value=f"{len(clan.members)}/50")
        embed.add_field(name="League", value=clan.war_league.name)
        embed.set_footer(text="CWL Balance Boss")
        await ctx.send(embed=embed)
    except coc.HTTPException as e:
        await ctx.send(f"Error fetching clan data: {e}")
        logging.error(f"CoC API error: {e}")

async def main():
    try:
        logging.info("Starting bot...")
        await bot.start(DISCORD_TOKEN)
    except Exception as e:
        logging.error(f"Failed to start bot: {e}")

if __name__ == "__main__":
    asyncio.run(main())