import os
import discord
from discord.ext import commands
import random
import datetime
import pytz
import requests
import wavelink

# 봇 토큰 환경 변수에서 가져오기
TOKEN = os.environ['BOT_TOKEN']

# OpenWeatherMap API 키 (실제 API 키로 교체 필요)
WEATHER_API_KEY = "YOUR_API_KEY"  # OpenWeatherMap API 키를 여기에 입력하세요

# 봇 설명
description = '''An example bot to showcase the discord.ext.commands extension
module.

There are a number of utility commands being showcased here.'''

# 봇 권한 설정
intents = discord.Intents.default()
intents.members = True  # 멤버 관련 권한 활성화
intents.message_content = True  # 메시지 내용 읽기 권한 활성화
intents.voice_states = True  # 음성 상태 권한 활성화

# 봇 객체 생성 (명령어 접두사: ?)
bot = commands.Bot(command_prefix='?', description=description, intents=intents)

# 음성 클라이언트 딕셔너리
voice_clients = {}

# 봇이 준비되었을 때 실행되는 이벤트
@bot.event
async def on_ready():
    print(f'Logged in as {bot.user} (ID: {bot.user.id})')
    print('------')
    # Wavelink 노드 연결
    node = wavelink.Node(uri='http://localhost:2333', password='youshallnotpass')
    await wavelink.NodePool.connect(client=bot, nodes=[node])


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


# 날씨 정보를 보여주는 명령어
@bot.command()
async def weather(ctx, city: str):
    """Shows the current weather for a city."""
    try:
        # OpenWeatherMap API 호출
        url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={WEATHER_API_KEY}&units=metric&lang=kr"
        response = requests.get(url)
        data = response.json()

        if response.status_code == 200:
            # 날씨 정보 추출
            temp = data['main']['temp']
            feels_like = data['main']['feels_like']
            humidity = data['main']['humidity']
            weather_desc = data['weather'][0]['description']
            wind_speed = data['wind']['speed']

            # 임베드 생성
            embed = discord.Embed(title=f"{city}의 날씨", color=discord.Color.blue())
            embed.add_field(name="온도", value=f"{temp}°C", inline=True)
            embed.add_field(name="체감 온도", value=f"{feels_like}°C", inline=True)
            embed.add_field(name="습도", value=f"{humidity}%", inline=True)
            embed.add_field(name="날씨", value=weather_desc, inline=True)
            embed.add_field(name="풍속", value=f"{wind_speed}m/s", inline=True)
            
            await ctx.send(embed=embed)
        else:
            await ctx.send(f"도시 '{city}'를 찾을 수 없습니다.")
    except Exception as e:
        await ctx.send(f"날씨 정보를 가져오는 중 오류가 발생했습니다: {str(e)}")


# 음성 채널에 참가하는 명령어
@bot.command()
async def join(ctx):
    """봇을 음성 채널에 참가시킵니다."""
    if ctx.author.voice is None:
        await ctx.send("먼저 음성 채널에 참가해주세요!")
        return
    
    channel = ctx.author.voice.channel
    if ctx.voice_client is None:
        await channel.connect()
        await ctx.send(f"{channel.name}에 참가했습니다!")
    else:
        await ctx.voice_client.move_to(channel)
        await ctx.send(f"{channel.name}로 이동했습니다!")


# 음성 채널에서 나가는 명령어
@bot.command()
async def leave(ctx):
    """봇을 음성 채널에서 나가게 합니다."""
    if ctx.voice_client is None:
        await ctx.send("봇이 음성 채널에 없습니다!")
        return
    
    await ctx.voice_client.disconnect()
    await ctx.send("음성 채널에서 나갔습니다!")


# 음악을 재생하는 명령어
@bot.command()
async def play(ctx, *, query: str):
    """YouTube에서 음악을 검색하고 재생합니다."""
    if ctx.voice_client is None:
        await ctx.send("먼저 `?join` 명령어로 봇을 음성 채널에 참가시켜주세요!")
        return

    # 검색 결과 가져오기
    tracks = await wavelink.NodePool.get_node().get_tracks(query)
    if not tracks:
        await ctx.send("검색 결과가 없습니다!")
        return

    # 첫 번째 결과 재생
    track = tracks[0]
    player = ctx.voice_client
    
    if player.is_playing():
        player.stop()
    
    await player.play(track)
    await ctx.send(f"🎵 재생 중: {track.title}")


# 재생 중인 음악을 일시정지하는 명령어
@bot.command()
async def pause(ctx):
    """재생 중인 음악을 일시정지합니다."""
    if ctx.voice_client is None:
        await ctx.send("봇이 음성 채널에 없습니다!")
        return
    
    if not ctx.voice_client.is_playing():
        await ctx.send("현재 재생 중인 음악이 없습니다!")
        return
    
    await ctx.voice_client.pause()
    await ctx.send("⏸️ 일시정지")


# 일시정지된 음악을 다시 재생하는 명령어
@bot.command()
async def resume(ctx):
    """일시정지된 음악을 다시 재생합니다."""
    if ctx.voice_client is None:
        await ctx.send("봇이 음성 채널에 없습니다!")
        return
    
    if not ctx.voice_client.is_paused():
        await ctx.send("일시정지된 음악이 없습니다!")
        return
    
    await ctx.voice_client.resume()
    await ctx.send("▶️ 재생 재개")


# 재생 중인 음악을 중지하는 명령어
@bot.command()
async def stop(ctx):
    """재생 중인 음악을 중지합니다."""
    if ctx.voice_client is None:
        await ctx.send("봇이 음성 채널에 없습니다!")
        return
    
    if not ctx.voice_client.is_playing():
        await ctx.send("현재 재생 중인 음악이 없습니다!")
        return
    
    await ctx.voice_client.stop()
    await ctx.send("⏹️ 재생 중지")


# 봇 실행 (직접 실행될 때만)
if __name__ == '__main__':
    bot.run(TOKEN)