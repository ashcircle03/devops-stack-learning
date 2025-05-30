import os
import discord
from discord.ext import commands, tasks
import random
import datetime
import pytz
from prometheus_client import start_http_server, Counter, Gauge, Histogram, generate_latest, Info
from flask import Flask, Response
import threading
import time
import logging

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Flask 앱 생성 (메트릭 엔드포인트용)
app = Flask(__name__)

# 프로메테우스 메트릭 정의
COMMAND_COUNTER = Counter('discord_bot_commands_total', 'Total number of commands executed', ['command', 'status'])
MESSAGE_LATENCY = Histogram('discord_bot_message_latency_seconds', 'Message processing latency')
MESSAGES_SENT = Counter('discord_bot_messages_sent_total', 'Number of messages sent')
ERROR_COUNT = Counter('discord_bot_errors_total', 'Number of errors', ['error_type'])
HEARTBEAT_TIMESTAMP = Gauge('discord_bot_heartbeat_timestamp_seconds', 'Timestamp of last heartbeat')
ACTIVE_GUILDS = Gauge('discord_bot_active_guilds', 'Number of active guilds')
ACTIVE_USERS = Gauge('discord_bot_active_users', 'Number of active users')
BOT_INFO = Info('discord_bot_info', 'Bot information')

@app.route('/metrics')
def metrics():
    """프로메테우스 메트릭 엔드포인트"""
    # 하트비트 업데이트
    HEARTBEAT_TIMESTAMP.set(time.time())
    return Response(generate_latest(), mimetype='text/plain')

@app.route('/health')
def health():
    """헬스 체크 엔드포인트"""
    return {"status": "healthy", "timestamp": time.time()}

# 봇 토큰 환경 변수에서 가져오기
TOKEN = os.environ['BOT_TOKEN']

# 봇 설명
description = '''Discord 유틸리티 봇'''

# 봇 권한 설정
intents = discord.Intents.default()
intents.members = True
intents.message_content = True

# 봇 객체 생성
bot = commands.Bot(command_prefix='?', description=description, intents=intents)

# 봇이 준비되었을 때 실행되는 이벤트
@bot.event
async def on_ready():
    print(f'Logged in as {bot.user} (ID: {bot.user.id})')
    
    # 봇 정보 메트릭 설정
    BOT_INFO.info({
        'name': str(bot.user),
        'id': str(bot.user.id),
        'version': '1.0.0'
    })
    
    # 주기적 메트릭 업데이트 시작
    update_metrics.start()
    print('------')

@tasks.loop(seconds=30)
async def update_metrics():
    """주기적으로 메트릭 업데이트"""
    try:
        ACTIVE_GUILDS.set(len(bot.guilds))
        total_users = sum(guild.member_count for guild in bot.guilds if guild.member_count)
        ACTIVE_USERS.set(total_users)
        HEARTBEAT_TIMESTAMP.set(time.time())
        logger.info(f"Metrics updated: {len(bot.guilds)} guilds, {total_users} users")
    except Exception as e:
        ERROR_COUNT.labels(error_type='metrics_update').inc()
        logger.error(f"Error updating metrics: {e}")

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
        COMMAND_COUNTER.labels(command=ctx.command.name, status='success').inc()

@bot.event
async def on_command_error(ctx, error):
    """명령어 에러 처리"""
    ERROR_COUNT.labels(error_type='command_error').inc()
    COMMAND_COUNTER.labels(command=ctx.command.name if ctx.command else 'unknown', status='error').inc()
    logger.error(f"Command error in {ctx.command}: {error}")

# 메시지 전송 함수
def send_message():
    try:
        # 메시지 전송 로직
        MESSAGES_SENT.inc()
    except Exception as e:
        ERROR_COUNT.inc()
        print(f"Error: {e}")

# 두 숫자를 더하는 명령어
@bot.command()
async def add(ctx, left: int, right: int):
    """Adds two numbers together."""
    try:
        await ctx.send(left + right)
        MESSAGES_SENT.inc()
    except Exception as e:
        ERROR_COUNT.inc()
        print(f"Error in add command: {e}")

# 주사위를 굴리는 명령어
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
        MESSAGES_SENT.inc()
    except ValueError:
        await ctx.send('올바른 형식이 아닙니다! (예: 2d6)')
        ERROR_COUNT.inc()
    except Exception as e:
        ERROR_COUNT.inc()
        print(f"Error in roll command: {e}")

# 여러 선택지 중 하나를 무작위로 선택하는 명령어
@bot.command()
async def choose(ctx, *choices: str):
    """여러 선택지 중 하나를 무작위로 선택합니다."""
    try:
        if not choices:
            await ctx.send('선택지를 입력해주세요!')
            return
        await ctx.send(random.choice(choices))
        MESSAGES_SENT.inc()
    except Exception as e:
        ERROR_COUNT.inc()
        print(f"Error in choose command: {e}")

# 메시지를 지정된 횟수만큼 반복하는 명령어
@bot.command()
async def repeat(ctx, times: int, content='repeating...'):
    """Repeats a message multiple times."""
    try:
        if times <= 0:
            await ctx.send('Number of repeats must be positive!')
            return
        for i in range(times):
            await ctx.send(content)
            MESSAGES_SENT.inc()
    except Exception as e:
        ERROR_COUNT.inc()
        print(f"Error in repeat command: {e}")

# 멤버의 서버 참가일을 보여주는 명령어
@bot.command()
async def joined(ctx, member: discord.Member):
    """Says when a member joined."""
    try:
        await ctx.send(f'{member.name} joined {discord.utils.format_dt(member.joined_at)}')
        MESSAGES_SENT.inc()
    except Exception as e:
        ERROR_COUNT.inc()
        print(f"Error in joined command: {e}")

# 'cool' 명령어 그룹 생성
@bot.group()
async def cool(ctx):
    """Says if a user is cool."""
    if ctx.invoked_subcommand is None:
        await ctx.send(f'No, {ctx.subcommand_passed} is not cool')

@cool.command(name='bot')
async def _bot(ctx):
    """Is the bot cool?"""
    try:
        await ctx.send('Yes, the bot is cool.')
        MESSAGES_SENT.inc()
    except Exception as e:
        ERROR_COUNT.inc()
        print(f"Error in cool bot command: {e}")

# 현재 시간을 보여주는 명령어
@bot.command()
async def time(ctx):
    """현재 한국 시간을 보여줍니다."""
    try:
        korea_tz = pytz.timezone('Asia/Seoul')
        current_time = datetime.datetime.now(korea_tz)
        await ctx.send(f'현재 한국 시간: {current_time.strftime("%Y-%m-%d %H:%M:%S %Z")}')
        MESSAGES_SENT.inc()
    except Exception as e:
        ERROR_COUNT.inc()
        print(f"Error in time command: {e}")

def run_flask():
    """Flask 앱을 별도 스레드에서 실행"""
    app.run(host='0.0.0.0', port=8000)

# 봇 실행
if __name__ == '__main__':
    # Flask 서버를 별도 스레드에서 시작
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    
    print("Discord 봇과 메트릭 서버가 시작되었습니다.")
    print("메트릭: http://localhost:8000/metrics")
    print("헬스체크: http://localhost:8000/health")
    
    try:
        # Discord 봇 실행
        bot.run(TOKEN)
    except Exception as e:
        ERROR_COUNT.labels(error_type='startup').inc()
        logger.error(f"Bot startup error: {e}")
        raise
