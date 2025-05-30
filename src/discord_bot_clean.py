#!/usr/bin/env python3
"""
Discord Bot with Prometheus Metrics
===================================
Discord 봇과 Prometheus 메트릭을 통합한 모니터링 봇

Features:
- Discord bot commands
- Prometheus metrics collection
- Health check endpoints
- Error tracking and logging
"""

import os
import discord
from discord.ext import commands, tasks
import random
import datetime
import pytz
from prometheus_client import Counter, Gauge, Histogram, generate_latest, Info
from flask import Flask, Response
import threading
import time as time_module
import logging


class DiscordBotMetrics:
    """Discord 봇 메트릭 관리 클래스"""
    
    def __init__(self):
        # 프로메테우스 메트릭 정의
        self.command_counter = Counter(
            'discord_bot_commands_total', 
            'Total number of commands executed', 
            ['command', 'status']
        )
        self.message_latency = Histogram(
            'discord_bot_message_latency_seconds', 
            'Message processing latency'
        )
        self.messages_sent = Counter(
            'discord_bot_messages_sent_total', 
            'Number of messages sent'
        )
        self.error_count = Counter(
            'discord_bot_errors_total', 
            'Number of errors', 
            ['error_type']
        )
        self.heartbeat_timestamp = Gauge(
            'discord_bot_heartbeat_timestamp_seconds', 
            'Timestamp of last heartbeat'
        )
        self.active_guilds = Gauge(
            'discord_bot_active_guilds', 
            'Number of active guilds'
        )
        self.active_users = Gauge(
            'discord_bot_active_users', 
            'Number of active users'
        )
        self.bot_info = Info('discord_bot_info', 'Bot information')


class MetricsServer:
    """Flask 기반 메트릭 서버"""
    
    def __init__(self, metrics: DiscordBotMetrics):
        self.app = Flask(__name__)
        self.metrics = metrics
        self._setup_routes()
    
    def _setup_routes(self):
        @self.app.route('/metrics')
        def metrics():
            """프로메테우스 메트릭 엔드포인트"""
            self.metrics.heartbeat_timestamp.set(time_module.time())
            return Response(generate_latest(), mimetype='text/plain')

        @self.app.route('/health')
        def health():
            """헬스 체크 엔드포인트"""
            return {"status": "healthy", "timestamp": time_module.time()}

        @self.app.route('/test-error')
        def test_error():
            """테스트용 에러 발생 엔드포인트"""
            self.metrics.error_count.labels(error_type='test_error').inc()
            logging.error("Test error triggered via /test-error endpoint")
            return {"status": "error", "message": "Test error generated"}, 500

        @self.app.route('/test-crash')
        def test_crash():
            """테스트용 크래시 시뮬레이션"""
            self.metrics.error_count.labels(error_type='crash_simulation').inc()
            logging.critical("Crash simulation triggered")
            raise Exception("Simulated crash for testing alerts")
    
    def run(self, host='0.0.0.0', port=8000):
        """Flask 서버 실행"""
        self.app.run(host=host, port=port, debug=False)


class DiscordBot:
    """Discord 봇 메인 클래스"""
    
    def __init__(self, token: str, metrics: DiscordBotMetrics):
        self.token = token
        self.metrics = metrics
        self.logger = logging.getLogger(__name__)
        
        # 봇 권한 설정
        intents = discord.Intents.default()
        intents.members = True
        intents.message_content = True
        
        # 봇 객체 생성
        self.bot = commands.Bot(
            command_prefix='?', 
            description='Discord 유틸리티 봇', 
            intents=intents
        )
        
        self._setup_events()
        self._setup_commands()
    
    def _setup_events(self):
        """봇 이벤트 설정"""
        
        @self.bot.event
        async def on_ready():
            self.logger.info(f'Logged in as {self.bot.user} (ID: {self.bot.user.id})')
            
            # 봇 정보 메트릭 설정
            self.metrics.bot_info.info({
                'name': str(self.bot.user),
                'id': str(self.bot.user.id),
                'version': '1.0.0'
            })
            
            # 주기적 메트릭 업데이트 시작
            self.update_metrics.start()
        
        @self.bot.before_invoke
        async def before_invoke(ctx):
            setattr(ctx, '_start_time', time_module.time())
        
        @self.bot.after_invoke
        async def after_invoke(ctx):
            if hasattr(ctx, '_start_time'):
                latency = time_module.time() - getattr(ctx, '_start_time')
                self.metrics.message_latency.observe(latency)
                self.metrics.command_counter.labels(
                    command=ctx.command.name, 
                    status='success'
                ).inc()
        
        @self.bot.event
        async def on_command_error(ctx, error):
            """명령어 에러 처리"""
            self.metrics.error_count.labels(error_type='command_error').inc()
            self.metrics.command_counter.labels(
                command=ctx.command.name if ctx.command else 'unknown', 
                status='error'
            ).inc()
            self.logger.error(f"Command error in {ctx.command}: {error}")
    
    @tasks.loop(seconds=30)
    async def update_metrics(self):
        """주기적으로 메트릭 업데이트"""
        try:
            self.metrics.active_guilds.set(len(self.bot.guilds))
            total_users = sum(guild.member_count for guild in self.bot.guilds if guild.member_count)
            self.metrics.active_users.set(total_users)
            self.metrics.heartbeat_timestamp.set(time_module.time())
            self.logger.info(f"Metrics updated: {len(self.bot.guilds)} guilds, {total_users} users")
        except Exception as e:
            self.metrics.error_count.labels(error_type='metrics_update').inc()
            self.logger.error(f"Error updating metrics: {e}")
    
    def _setup_commands(self):
        """봇 명령어 설정"""
        
        @self.bot.command()
        async def add(ctx, left: int, right: int):
            """두 숫자를 더합니다."""
            try:
                result = left + right
                await ctx.send(f"{left} + {right} = {result}")
                self.metrics.messages_sent.inc()
            except Exception as e:
                self.metrics.error_count.labels(error_type='command_error').inc()
                self.logger.error(f"Error in add command: {e}")
        
        @self.bot.command()
        async def roll(ctx, dice: str):
            """주사위를 굴립니다. 형식: NdN (예: 2d6)"""
            try:
                rolls, limit = map(int, dice.split('d'))
                if rolls <= 0 or limit <= 0 or rolls > 100:
                    await ctx.send('올바른 형식이 아닙니다! (예: 2d6)')
                    return
                
                results = [random.randint(1, limit) for _ in range(rolls)]
                result_text = ', '.join(str(r) for r in results)
                total = sum(results)
                
                await ctx.send(f"🎲 {dice}: {result_text} (총합: {total})")
                self.metrics.messages_sent.inc()
            except ValueError:
                await ctx.send('올바른 형식이 아닙니다! (예: 2d6)')
                self.metrics.error_count.labels(error_type='command_error').inc()
            except Exception as e:
                self.metrics.error_count.labels(error_type='command_error').inc()
                self.logger.error(f"Error in roll command: {e}")
        
        @self.bot.command()
        async def choose(ctx, *choices: str):
            """여러 선택지 중 하나를 무작위로 선택합니다."""
            try:
                if not choices:
                    await ctx.send('선택지를 입력해주세요! 예: `?choose 사과 바나나 오렌지`')
                    return
                
                choice = random.choice(choices)
                await ctx.send(f"🎯 선택된 것: **{choice}**")
                self.metrics.messages_sent.inc()
            except Exception as e:
                self.metrics.error_count.labels(error_type='command_error').inc()
                self.logger.error(f"Error in choose command: {e}")
        
        @self.bot.command()
        async def time(ctx):
            """현재 한국 시간을 보여줍니다."""
            try:
                korea_tz = pytz.timezone('Asia/Seoul')
                current_time = datetime.datetime.now(korea_tz)
                formatted_time = current_time.strftime("%Y-%m-%d %H:%M:%S %Z")
                
                await ctx.send(f"🕐 현재 한국 시간: **{formatted_time}**")
                self.metrics.messages_sent.inc()
            except Exception as e:
                self.metrics.error_count.labels(error_type='command_error').inc()
                self.logger.error(f"Error in time command: {e}")
        
        @self.bot.command()
        async def ping(ctx):
            """봇의 응답 시간을 확인합니다."""
            try:
                latency = round(self.bot.latency * 1000)
                await ctx.send(f"🏓 Pong! 지연시간: {latency}ms")
                self.metrics.messages_sent.inc()
            except Exception as e:
                self.metrics.error_count.labels(error_type='command_error').inc()
                self.logger.error(f"Error in ping command: {e}")
        
        @self.bot.command()
        async def info(ctx):
            """봇 정보를 표시합니다."""
            try:
                guild_count = len(self.bot.guilds)
                user_count = sum(guild.member_count for guild in self.bot.guilds if guild.member_count)
                
                embed = discord.Embed(
                    title="🤖 봇 정보",
                    color=0x00ff00,
                    timestamp=datetime.datetime.now()
                )
                embed.add_field(name="서버 수", value=guild_count, inline=True)
                embed.add_field(name="사용자 수", value=user_count, inline=True)
                embed.add_field(name="지연시간", value=f"{round(self.bot.latency * 1000)}ms", inline=True)
                embed.set_footer(text="Discord Bot v1.0.0")
                
                await ctx.send(embed=embed)
                self.metrics.messages_sent.inc()
            except Exception as e:
                self.metrics.error_count.labels(error_type='command_error').inc()
                self.logger.error(f"Error in info command: {e}")
    
    def run(self):
        """봇 실행"""
        try:
            self.bot.run(self.token)
        except Exception as e:
            self.metrics.error_count.labels(error_type='startup').inc()
            self.logger.error(f"Bot startup error: {e}")
            raise


def main():
    """메인 함수"""
    # 로깅 설정
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    logger = logging.getLogger(__name__)
    
    # 환경 변수에서 토큰 가져오기
    token = os.environ.get('BOT_TOKEN')
    if not token:
        logger.error("BOT_TOKEN 환경변수가 설정되지 않았습니다.")
        exit(1)
    
    # 메트릭 및 서버 초기화
    metrics = DiscordBotMetrics()
    metrics_server = MetricsServer(metrics)
    discord_bot = DiscordBot(token, metrics)
    
    # Flask 서버를 별도 스레드에서 시작
    flask_thread = threading.Thread(
        target=metrics_server.run, 
        kwargs={'host': '0.0.0.0', 'port': 8000},
        daemon=True
    )
    flask_thread.start()
    
    logger.info("Discord 봇과 메트릭 서버가 시작되었습니다.")
    logger.info("메트릭: http://localhost:8000/metrics")
    logger.info("헬스체크: http://localhost:8000/health")
    
    # Discord 봇 실행
    discord_bot.run()


if __name__ == '__main__':
    main()
