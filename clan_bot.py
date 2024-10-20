import discord
import aiohttp
import asyncio
import requests
import os

TOKEN = os.getenv('DISCORD_BOT_TOKEN')

# The Discord channel ID where updates will be posted (replace this with your channel's ID)
CHANNEL_ID = 1255555435906465803

# Clan API URL
CLAN_API_URL = "https://ps99.biggamesapi.io/api/clan/FMLY"

# Initialize the Discord bot client
intents = discord.Intents.default()
client = discord.Client(intents=intents)

# This will store the last fetched points to calculate differences
previous_points = {}

# Function to get Roblox username and display name via API
def get_user_info(user_id):
    url = f"https://users.roblox.com/v1/users/{user_id}"
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        username = data.get('name')
        display_name = data.get('displayName')
        return username, display_name
    else:
        return None, None

async def fetch_clan_data():
    """Fetch the clan data from the API and return as JSON."""
    async with aiohttp.ClientSession() as session:
        async with session.get(CLAN_API_URL) as response:
            clan_data = await response.json()
            print("Fetched clan data:", clan_data)  # Print API response for debugging
            return clan_data

async def post_clan_data():
    """Fetch data from the API, calculate point changes, and post updates to Discord."""
    try:
        global previous_points

        # Fetch the current clan data
        print("Fetching clan data...")
        clan_data = await fetch_clan_data()

        # Extract necessary information from HalloweenBattle
        print("Processing battle data...")
        battle = clan_data['data']['Battles']['HalloweenBattle']
        clan_place = battle['Place']
        clan_total_points = battle['Points']
        point_contributions = battle['PointContributions']

        # List to store member data with point changes
        members = []

        # Loop through each member in PointContributions
        for contribution in point_contributions:
            user_id = contribution['UserID']
            points = contribution['Points']
            print(f"Processing user ID: {user_id} with points: {points}")

            # Fetch user info (username, display_name)
            username, display_name = get_user_info(user_id)
            
            if username and display_name:
                point_diff = points - previous_points.get(user_id, points)
                previous_points[user_id] = points

                # Append member data for sorting later
                members.append({
                    'display_name': display_name,
                    'username': username,
                    'points': points,
                    'point_diff': point_diff
                })
            else:
                # Handle unknown user case
                members.append({
                    'display_name': 'Unknown User',
                    'username': 'Unknown',
                    'points': points,
                    'point_diff': 0
                })
                print(f"Error fetching info for user ID: {user_id}")

        # Sort members by point changes (highest to lowest) and take the top 10
        members = sorted(members, key=lambda x: x['point_diff'], reverse=True)[:10]

        # Create an embed message
        embed = discord.Embed(
            title=f"Top 10 Point Changes - {clan_data['data']['Name']} Clan",
            description=f"🥇 **#{clan_place}** place\n⭐ **{clan_total_points:,}** Total Points",
            color=0x00ff00  # Green color for the embed
        )

        # Add each top 10 member to the embed
        for member in members:
            entry = f"⭐️ **{member['points']:,}** (+{member['point_diff']:,})"
            embed.add_field(
                name=f"{member['display_name']} (@{member['username']})",
                value=entry,
                inline=False
            )

        # Send the embed message to the specified Discord channel
        channel = client.get_channel(CHANNEL_ID)
        if channel:
            await channel.send(embed=embed)
            print("Embed message sent.")

    except Exception as e:
        print(f"An error occurred: {e}")

# Run the point update every 60 seconds using asyncio
async def scheduled_task():
    while True:
        print("Running scheduled task...")
        await post_clan_data()
        await asyncio.sleep(600)  # Run every 60 seconds (1 minute)

# When the bot is ready
@client.event
async def on_ready():
    print(f'Logged in as {client.user}')

    # Send a message when the bot starts up
    channel = client.get_channel(CHANNEL_ID)
    if channel:
        await channel.send("Hello! The Clan Bot is now online and tracking points for Halloween Battle!")
        print(f"Startup message sent to channel {CHANNEL_ID}")

    # Start the scheduled task
    client.loop.create_task(scheduled_task())

# Run the bot
client.run(TOKEN)