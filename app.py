
import time
import aiohttp
import asyncio
import discord
from dotenv import dotenv_values
from discord.ext import commands
import os

status_url = "https://www.fotmob.com/matches?date={date}"
game_url = "https://www.fotmob.com/matchDetails?matchId={match_id}"

league_list = ['Champions League', 'Europa League', 'Premier League']

debug = False

bot = commands.Bot(command_prefix='!')

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
        if league.get('parentLeagueName', league.get('name')) not in league_list:
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
                channel = bot.get_channel(912383883935375440) # Bot test channel
                await channel.send(update_text)
            print(update_text)
        else:
            print("* None")
        if debug:
            print("LIVE DATA")
            print(live_data)
        await asyncio.sleep(30)


client = discord.Client()

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
