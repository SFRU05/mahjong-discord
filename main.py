import discord
from discord.ext import commands, tasks
import os
from dotenv import load_dotenv
from itertools import cycle

load_dotenv()

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix='/', intents=intents)

def get_status_list():
    return [
        "{m}명의 작사와 함께",
        "작탁 {n}개에서 관전 중",
        "리치! 쯔모!"]

status = cycle(get_status_list())

@bot.event
async def on_ready():
    print(f'{bot.user} 봇이 시작되었습니다!')
    change_status.start()
    try:
        synced = await bot.tree.sync()
        print(f'{len(synced)}개의 슬래시 커맨드가 동기화되었습니다.')
    except Exception as e:
        print(f'커맨드 동기화 실패: {e}')

@tasks.loop(seconds=6)
async def change_status():
    template = next(status)
    server_count = len(bot.guilds)
    user_count = len(set(bot.users))
    text = template.format(n=server_count, m=user_count)
    await bot.change_presence(activity=discord.Game(name=text))

async def setup():
    await bot.load_extension('cogs.quiz')

async def main():
    async with bot:
        await setup()
        await bot.start(os.getenv('DISCORD_TOKEN'))

if __name__ == '__main__':
    import asyncio
    asyncio.run(main())