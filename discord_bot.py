import os
import discord
from discord.ext import commands
import random
import datetime
import pytz
import wavelink
from prometheus_client import start_http_server, Counter, Gauge, Histogram
from typing import cast

# 프로메테우스 메트릭 정의
COMMAND_COUNTER = Counter('discord_bot_commands_total', 'Total number of commands executed', ['command'])
VOICE_CONNECTIONS = Gauge('discord_bot_voice_connections', 'Number of active voice connections')
MESSAGE_LATENCY = Histogram('discord_bot_message_latency_seconds', 'Message processing latency')

# 봇 토큰 환경 변수에서 가져오기
TOKEN = os.environ['BOT_TOKEN']

# OpenWeatherMap API 키 (실제 API 키로 교체 필요)
WEATHER_API_KEY = "YOUR_API_KEY"  # OpenWeatherMap API 키를 여기에 입력하세요

# 봇 설명
description = '''Discord 봇 with 음성 기능과 유틸리티 명령어'''

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
    # 프로메테우스 메트릭 서버 시작
    start_http_server(8000)
    # Wavelink 노드 연결
    nodes = [wavelink.Node(
        uri='http://lavalink.default.svc.cluster.local:2333',
        password='youshallnotpass'
    )]
    await wavelink.Pool.connect(nodes=nodes, client=bot, cache_capacity=100)

@bot.event
async def on_wavelink_node_ready(payload: wavelink.NodeReadyEventPayload) -> None:
    print(f"Wavelink Node connected: {payload.node} | Resumed: {payload.resumed}")

@bot.event
async def on_wavelink_track_start(payload: wavelink.TrackStartEventPayload) -> None:
    player: wavelink.Player | None = payload.player
    if not player:
        return

    track: wavelink.Playable = payload.track
    embed: discord.Embed = discord.Embed(title="Now Playing")
    embed.description = f"**{track.title}** by `{track.author}`"

    if track.artwork:
        embed.set_image(url=track.artwork)

    if track.album.name:
        embed.add_field(name="Album", value=track.album.name)

    await player.home.send(embed=embed)

# 명령어 실행 전/후 처리
@bot.before_invoke
async def before_invoke(ctx):
    import time
    setattr(ctx, '_start_time', time.time())

@bot.after_invoke
async def after_invoke(ctx):
    import time
    if hasattr(ctx, '_start_time'):
        latency = time.time() - getattr(ctx, '_start_time')
        MESSAGE_LATENCY.observe(latency)
        COMMAND_COUNTER.labels(command=ctx.command.name).inc()

# 두 숫자를 더하는 명령어
@bot.command()
async def add(ctx, left: int, right: int):
    """Adds two numbers together."""
    await ctx.send(left + right)


# 주사위를 굴리는 명령어 (NdN 형식: N개의 N면체 주사위)
@bot.command()
async def roll(ctx, dice: str):
    """주사위를 굴립니다. 형식: NdN (예: 2d6)"""
    try:
        rolls, limit = map(int, dice.split('d'))
        if rolls <= 0 or limit <= 0 or rolls > 100:
            await ctx.send('올바른 형식이 아닙니다! (예: 2d6)')
            return
        results = [random.randint(1, limit) for r in range(rolls)]
        await ctx.send(', '.join(str(r) for r in results))
    except ValueError:
        await ctx.send('올바른 형식이 아닙니다! (예: 2d6)')


# 여러 선택지 중 하나를 무작위로 선택하는 명령어
@bot.command()
async def choose(ctx, *choices: str):
    """여러 선택지 중 하나를 무작위로 선택합니다."""
    if not choices:
        await ctx.send('선택지를 입력해주세요!')
        return
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
    """현재 한국 시간을 보여줍니다."""
    korea_tz = pytz.timezone('Asia/Seoul')
    current_time = datetime.datetime.now(korea_tz)
    await ctx.send(f'현재 한국 시간: {current_time.strftime("%Y-%m-%d %H:%M:%S %Z")}')


# 음성 채널에 참가하는 명령어
@bot.command()
async def join(ctx):
    """봇을 음성 채널에 참가시킵니다."""
    if ctx.author.voice is None:
        await ctx.send("먼저 음성 채널에 참가해주세요!")
        return
    
    try:
        player = await ctx.author.voice.channel.connect(cls=wavelink.Player)
        player.home = ctx.channel
        VOICE_CONNECTIONS.inc()
        await ctx.send(f"{ctx.author.voice.channel.name}에 참가했습니다!")
    except Exception as e:
        await ctx.send(f"음성 채널 참가 중 오류가 발생했습니다: {str(e)}")


# 음성 채널에서 나가는 명령어
@bot.command(aliases=["dc"])
async def disconnect(ctx):
    """봇을 음성 채널에서 나가게 합니다."""
    player: wavelink.Player = cast(wavelink.Player, ctx.voice_client)
    if not player:
        await ctx.send("봇이 음성 채널에 없습니다!")
        return
    
    await player.disconnect()
    VOICE_CONNECTIONS.dec()
    await ctx.message.add_reaction("✅")


# 음악을 재생하는 명령어
@bot.command()
async def play(ctx, *, query: str):
    """YouTube에서 음악을 검색하고 재생합니다."""
    if not ctx.guild:
        return

    player: wavelink.Player = cast(wavelink.Player, ctx.voice_client)
    if not player:
        try:
            player = await ctx.author.voice.channel.connect(cls=wavelink.Player)
            player.home = ctx.channel
        except AttributeError:
            await ctx.send("먼저 음성 채널에 참가해주세요!")
            return
        except discord.ClientException:
            await ctx.send("음성 채널 참가에 실패했습니다. 다시 시도해주세요.")
            return

    # 자동 재생 활성화
    player.autoplay = wavelink.AutoPlayMode.enabled

    # 검색 결과 가져오기
    tracks: wavelink.Search = await wavelink.Playable.search(query)
    if not tracks:
        await ctx.send(f"{ctx.author.mention} - 검색 결과가 없습니다. 다시 시도해주세요.")
        return

    if isinstance(tracks, wavelink.Playlist):
        # 플레이리스트인 경우
        added: int = await player.queue.put_wait(tracks)
        await ctx.send(f"플레이리스트 **`{tracks.name}`** ({added}곡)을 큐에 추가했습니다.")
    else:
        # 단일 트랙인 경우
        track: wavelink.Playable = tracks[0]
        await player.queue.put_wait(track)
        await ctx.send(f"**`{track}`**을 큐에 추가했습니다.")

    if not player.playing:
        # 현재 재생 중이 아니면 바로 재생
        await player.play(player.queue.get(), volume=30)

# 재생 중인 음악을 일시정지하는 명령어
@bot.command(name="toggle", aliases=["pause", "resume"])
async def pause_resume(ctx):
    """재생 중인 음악을 일시정지하거나 다시 재생합니다."""
    player: wavelink.Player = cast(wavelink.Player, ctx.voice_client)
    if not player:
        await ctx.send("봇이 음성 채널에 없습니다!")
        return
    
    await player.pause(not player.paused)
    await ctx.message.add_reaction("✅")

# 재생 중인 음악을 중지하는 명령어
@bot.command()
async def skip(ctx):
    """현재 재생 중인 음악을 건너뜁니다."""
    player: wavelink.Player = cast(wavelink.Player, ctx.voice_client)
    if not player:
        await ctx.send("봇이 음성 채널에 없습니다!")
        return
    
    await player.skip(force=True)
    await ctx.message.add_reaction("✅")

# 볼륨 조절 명령어
@bot.command()
async def volume(ctx, value: int):
    """재생 볼륨을 조절합니다 (0-100)."""
    player: wavelink.Player = cast(wavelink.Player, ctx.voice_client)
    if not player:
        await ctx.send("봇이 음성 채널에 없습니다!")
        return
    
    await player.set_volume(value)
    await ctx.message.add_reaction("✅")

# 봇 실행 (직접 실행될 때만)
if __name__ == '__main__':
    bot.run(TOKEN)