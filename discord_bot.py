import os
import discord
from discord.ext import commands
import random
import datetime
import pytz

# 봇 토큰 환경 변수에서 가져오기
TOKEN = os.environ['BOT_TOKEN']

# 봇 설명
description = '''An example bot to showcase the discord.ext.commands extension
module.

There are a number of utility commands being showcased here.'''

# 봇 권한 설정
intents = discord.Intents.default()
intents.members = True  # 멤버 관련 권한 활성화
intents.message_content = True  # 메시지 내용 읽기 권한 활성화

# 봇 객체 생성 (명령어 접두사: ?)
bot = commands.Bot(command_prefix='?', description=description, intents=intents)


# 봇이 준비되었을 때 실행되는 이벤트
@bot.event
async def on_ready():
    print(f'Logged in as {bot.user} (ID: {bot.user.id})')
    print('------')


# 두 숫자를 더하는 명령어
@bot.command()
async def add(ctx, left: int, right: int):
    """Adds two numbers together."""
    await ctx.send(left + right)


# 주사위를 굴리는 명령어 (NdN 형식: N개의 N면체 주사위)
@bot.command()
async def roll(ctx, dice: str):
    """Rolls a dice in NdN format."""
    # Handle negative numbers in input
    if dice.startswith('-'):
        await ctx.send('Format has to be in NdN!')
        return
        
    try:
        rolls, limit = map(int, dice.split('d'))
        
        # Validate number of rolls and dice sides
        if rolls <= 0 or limit <= 0 or rolls > 100:
            await ctx.send('Format has to be in NdN!')
            return
            
        # Roll the dice and format results
        results = [random.randint(1, limit) for r in range(rolls)]
        await ctx.send(', '.join(str(r) for r in results))
        
    except ValueError:
        await ctx.send('Format has to be in NdN!')
        return


# 여러 선택지 중 하나를 무작위로 선택하는 명령어
@bot.command(description='For when you wanna settle the score some other way')
async def choose(ctx, *choices: str):
    """Chooses between multiple choices."""
    await ctx.send(random.choice(choices))


# 메시지를 지정된 횟수만큼 반복하는 명령어
@bot.command()
async def repeat(ctx, times: int, content='repeating...'):
    """Repeats a message multiple times."""
    # Validate number of repeats
    
    if times <= 0:
        await ctx.send('Number of repeats must be positive!')
        return
    # Send the message the specified number of times
    for i in range(times):
        await ctx.send(content)


# 멤버의 서버 참가일을 보여주는 명령어
@bot.command()
async def joined(ctx, member: discord.Member):
    """Says when a member joined."""
    await ctx.send(f'{member.name} joined {discord.utils.format_dt(member.joined_at)}')


# 'cool' 명령어 그룹 생성
@bot.group()
async def cool(ctx):
    """Says if a user is cool.
    In reality this just checks if a subcommand is being invoked.
    """
    # 하위 명령어가 없을 경우
    if ctx.invoked_subcommand is None:
        await ctx.send(f'No, {ctx.subcommand_passed} is not cool')


# 'cool' 그룹의 'bot' 하위 명령어
@cool.command(name='bot')
async def _bot(ctx):
    """Is the bot cool?"""
    await ctx.send('Yes, the bot is cool.')


# 현재 시간을 보여주는 명령어
@bot.command()
async def time(ctx):
    """Shows the current time in Korea."""
    korea_tz = pytz.timezone('Asia/Seoul')
    current_time = datetime.datetime.now(korea_tz)
    await ctx.send(f'현재 한국 시간: {current_time.strftime("%Y-%m-%d %H:%M:%S %Z")}')


# 봇 실행 (직접 실행될 때만)
if __name__ == '__main__':
    bot.run(TOKEN)