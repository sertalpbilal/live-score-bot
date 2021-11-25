
import time
import aiohttp
import asyncio
import discord
from dotenv import dotenv_values
from discord.ext import commands
import os

status_url = "https://www.fotmob.com/matches?date={date}"
game_url = "https://www.fotmob.com/matchDetails?matchId={match_id}"

league_ids = [47, 42, 73] # Premier League - Champ League - Europa League

debug = False

bot = commands.Bot(command_prefix='!')
game_data = {}

async def get_snapshot():
    date = time.strftime("%Y%m%d")
    async with aiohttp.ClientSession() as session:
        async with session.get(status_url.format(date=date)) as response:
            data = await response.json()
            return data


def compare_live_data(old, new, date):
    events = []
    if old['date'] != new['date']: # day change
        return []
    match_ids = new['matches'].keys()
    for match_id in match_ids:
        old_data = old['matches'][match_id]
        new_data = new['matches'][match_id]
        for key in new_data.keys():
            if new_data.get(key) != old_data.get(key):
                events.append({
                    'match': match_id,
                    'event': key,
                    'old': old_data.get(key),
                    'new': new_data.get(key),
                    'entry': new_data
                })
    return events

def parse_status_data(snapshot, date):
    leagues = snapshot['leagues']
    data = {'date': date, 'matches': {}}
    for league in leagues:
        # if league.get('parentLeagueName', league.get('name')) not in league_list:
        #     continue
        if league.get('primaryId', '') not in league_ids:
            continue
        for match in league['matches']:
            match_id = match['id']
            data['matches'][match_id] = {
                'match_id': match_id,
                'home_name': match['home']['name'],
                'home_score': match['home']['score'],
                'away_name': match['away']['name'],
                'away_score': match['away']['score'],
                'started': match['status']['started'],
                'finished': match['status']['finished'],
                'liveTime': match['status'].get('liveTime', {}).get('short', '')
                }
    return data

async def main():
    global game_data
    # print(game_data)
    live_data = {}
    while True:
        date = time.strftime("%Y%m%d")
        snapshot = await get_snapshot()
        live_updates = []
        if live_data == {}:
            live_data = parse_status_data(snapshot, date)
        else:
            # Compare
            snapshot = parse_status_data(snapshot, date)
            live_updates = compare_live_data(live_data, snapshot, date)
            live_data = snapshot
        # Print differences to channel
        print("EVENTS")
        if len(live_updates) > 0:
            print(', '.join([e['event'] for e in live_updates]))
        for event in live_updates:
            match = event['entry']
            update_text = f"{event['event']}! {match['liveTime']} {match['home_name']} - {match['away_name']}: {match['home_score']} - {match['away_score']}"
            if event['event'] != 'liveTime':
                print('*** PUSH TO SERVER! ', str(event))
                channel = bot.get_channel(912375274430169109) #bot.get_channel(912383883935375440) # Bot test channel
                embed = discord.Embed(title=f"{match['home_name']} - {match['away_name']}", description="", color=discord.Color.green())
                embed.add_field(name="Event", value=event['event'], inline=True)
                if str(match['liveTime']) != '':
                    embed.add_field(name="Min", value=match['liveTime'], inline=True)
                embed.add_field(name="Score", value=f"{match['home_score']} - {match['away_score']}", inline=True)
                embed.add_field(name="Link", value=f"https://www.fotmob.com/match/{match['match_id']}", inline=True)
                
                # await message.channel.send('\n'.join(bot_message))
                await channel.send(embed=embed)
                # await channel.send(update_text)
            print(update_text)
        else:
            print("* None")
        if debug:
            print("LIVE DATA")
            print(live_data)
        game_data = live_data
        # print(game_data)
        await asyncio.sleep(30)


# client = discord.Client()

@bot.event
async def on_ready():
    print(f'Live Rank Bot is working! {bot.user}')

@bot.event
async def on_message(message):

    print(message)

    global game_data

    if message.author == bot.user:
        return
    if message.guild.name != 'FPL Analytics Community':
        return

    allowed_channels = [912383883935375440, 912375274430169109, 912790411951624263] # test/bot/match-chat channels

    if message.channel.id not in allowed_channels:
        return

    if message.content.lower().startswith('!live'):
        words = message.content.split()

        if len(words) == 1 or words[1] == 'list':
            # list ongoing games here
            embed = discord.Embed(title=f"Live Games", description="", color=discord.Color.red())
            bot_message = []
            for match in game_data.get('matches', {}).values():
                if not match['started'] or match['finished']:
                    continue
                match_text = f"Min {match['liveTime']} | {match['home_name']} - {match['away_name']}: {match['home_score']} - {match['away_score']}\n`Link: https://www.fotmob.com/match/{match['match_id']}/`" # [Started: {match['started']}, Finished: {match['finished']}]
                bot_message.append(match_text)
                embed.add_field(name=f"{match['home_name']} - {match['away_name']}", value=f"**Min** {match['liveTime']}\n**Score** {match['home_score']} - {match['away_score']}\n**Link** https://www.fotmob.com/match/{match['match_id']}", inline=False)
            
            # await message.channel.send('\n'.join(bot_message))
            await message.channel.send(embed=embed)


if __name__ == "__main__":
    if debug:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(main())
        finally:
            loop.close()
    else:
        try:
            config = dotenv_values(".env")
        except:
            config = {}
        bot.loop.create_task(main())
        bot.run(config.get('TOKEN', os.environ.get('TOKEN')))

