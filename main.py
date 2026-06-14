import discord
from discord.ext import commands
import os
from dotenv import load_dotenv

load_dotenv()

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix='/', intents=intents)

@bot.event
async def on_ready():
    print(f'{bot.user} 봇이 시작되었습니다!')
    try:
        synced = await bot.tree.sync()
        print(f'{len(synced)}개의 슬래시 커맨드가 동기화되었습니다.')
    except Exception as e:
        print(f'커맨드 동기화 실패: {e}')

async def setup():
    await bot.load_extension('cogs.quiz')

async def main():
    async with bot:
        await setup()
        await bot.start(os.getenv('DISCORD_TOKEN'))

if __name__ == '__main__':
    import asyncio
    asyncio.run(main())