# slack_bot.py
import os
import logging
import json
import requests
from flask import Flask, request, jsonify
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from prometheus_client import start_http_server, Counter

# 환경 변수 설정
SLACK_BOT_TOKEN = os.getenv('SLACK_BOT_TOKEN')
SLACK_CHANNEL = os.getenv('SLACK_CHANNEL')
METRICS_PORT = int(os.getenv('METRICS_PORT', '8000'))

# 메트릭 정의
MESSAGES_SENT = Counter('slack_bot_messages_sent_total', 'Total number of messages sent to Slack')
MESSAGE_ERRORS = Counter('slack_bot_message_errors_total', 'Total number of message sending errors')

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
logger = logging.getLogger('slack_bot')

# Flask 앱 초기화
app = Flask(__name__)
slack_client = WebClient(token=SLACK_BOT_TOKEN) if SLACK_BOT_TOKEN else None

def send_to_slack(message, level='info'):
    """슬랙으로 메시지를 전송하는 함수"""
    if not slack_client or not SLACK_CHANNEL:
        logger.warning("Slack 클라이언트가 초기화되지 않았거나 채널이 설정되지 않았습니다.")
        return False

    emoji = {
        'info': 'ℹ️',
        'warning': '⚠️',
        'error': '❌',
        'success': '✅'
    }.get(level, 'ℹ️')

    try:
        response = slack_client.chat_postMessage(
            channel=SLACK_CHANNEL,
            text=f"{emoji} {message}",
            username="K8s 모니터링 봇"
        )
        MESSAGES_SENT.inc()
        logger.info(f"메시지 전송 성공: {message[:50]}...")
        return True
    except SlackApiError as e:
        MESSAGE_ERRORS.inc()
        logger.error(f"Slack API 오류: {str(e)}")
        return False
    except Exception as e:
        MESSAGE_ERRORS.inc()
        logger.error(f"메시지 전송 중 오류 발생: {str(e)}")
        return False

@app.route('/send', methods=['POST'])
def handle_send():
    """REST API 엔드포인트: 슬랙으로 메시지 전송"""
    try:
        data = request.get_json()
        message = data.get('message', '')
        level = data.get('level', 'info')
        
        if not message:
            return jsonify({"status": "error", "message": "메시지가 비어있습니다."}), 400
        
        if send_to_slack(message, level):
            return jsonify({"status": "success"})
        else:
            return jsonify({"status": "error", "message": "메시지 전송 실패"}), 500
            
    except Exception as e:
        logger.error(f"요청 처리 중 오류 발생: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/health')
def health_check():
    """헬스 체크 엔드포인트"""
    return jsonify({"status": "healthy"}), 200

if __name__ == '__main__':
    # 메트릭 서버 시작
    start_http_server(METRICS_PORT)
    logger.info(f"메트릭 서버가 {METRICS_PORT} 포트에서 시작되었습니다.")
    
    # Flask 앱 실행
    app.run(host='0.0.0.0', port=5000)