"""
Slack Bot for Kubernetes Log Monitoring
슬랙에서 /로그 명령어로 쿠버네티스 로그를 조회할 수 있는 봇
"""

import os
import subprocess
import json
from datetime import datetime, timedelta
from flask import Flask, request, jsonify
from slack_sdk import WebClient
from slack_sdk.signature import SignatureVerifier
import logging

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# 슬랙 설정
SLACK_BOT_TOKEN = os.environ.get('SLACK_BOT_TOKEN')
SLACK_SIGNING_SECRET = os.environ.get('SLACK_SIGNING_SECRET')

if not SLACK_BOT_TOKEN or not SLACK_SIGNING_SECRET:
    logger.warning("SLACK_BOT_TOKEN 또는 SLACK_SIGNING_SECRET 환경변수가 설정되지 않았습니다. 테스트 모드로 실행됩니다.")

slack_client = WebClient(token=SLACK_BOT_TOKEN) if SLACK_BOT_TOKEN else None
signature_verifier = SignatureVerifier(SLACK_SIGNING_SECRET) if SLACK_SIGNING_SECRET else None

def get_pod_logs(namespace="monitoring", pod_name=None, lines=20):
    """쿠버네티스 Pod 로그를 가져오는 함수"""
    try:
        if pod_name:
            # 특정 Pod의 로그
            cmd = f"kubectl logs {pod_name} -n {namespace} --tail={lines}"
        else:
            # 네임스페이스의 모든 Pod 목록
            cmd = f"kubectl get pods -n {namespace} -o json"
        
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        
        if result.returncode != 0:
            return f"❌ 오류: {result.stderr}"
        
        return result.stdout
    except Exception as e:
        return f"❌ 예외 발생: {str(e)}"

def get_discord_bot_logs(lines=20):
    """Discord 봇 로그를 가져오는 함수"""
    try:
        # Discord 봇 Pod 찾기
        cmd = "kubectl get pods -n default -l app=discord-bot -o jsonpath='{.items[0].metadata.name}'"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        
        if result.returncode != 0:
            return "❌ Discord 봇 Pod를 찾을 수 없습니다"
        
        pod_name = result.stdout.strip()
        if not pod_name:
            return "❌ Discord 봇 Pod가 실행되고 있지 않습니다"
        
        # 로그 가져오기
        log_cmd = f"kubectl logs {pod_name} -n default --tail={lines}"
        log_result = subprocess.run(log_cmd, shell=True, capture_output=True, text=True)
        
        if log_result.returncode != 0:
            return f"❌ 로그 조회 실패: {log_result.stderr}"
        
        return log_result.stdout
    except Exception as e:
        return f"❌ 예외 발생: {str(e)}"

def get_monitoring_status():
    """모니터링 시스템 전체 상태를 가져오는 함수"""
    try:
        # 모니터링 네임스페이스의 모든 Pod 상태
        cmd = "kubectl get pods -n monitoring -o json"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        
        if result.returncode != 0:
            return f"❌ 오류: {result.stderr}"
        
        pods_data = json.loads(result.stdout)
        status_text = "🔍 *모니터링 시스템 상태*\n\n"
        
        for pod in pods_data['items']:
            name = pod['metadata']['name']
            status = pod['status']['phase']
            if 'containerStatuses' in pod['status']:
                ready = pod['status']['containerStatuses'][0]['ready']
                restart_count = pod['status']['containerStatuses'][0]['restartCount']
                status_icon = "✅" if ready else "❌"
                status_text += f"{status_icon} `{name}`: {status} (재시작: {restart_count}회)\n"
            else:
                status_text += f"⏳ `{name}`: {status}\n"
        
        return status_text
    except Exception as e:
        return f"❌ 예외 발생: {str(e)}"

def format_logs_for_slack(logs, title="📋 로그"):
    """로그를 슬랙 메시지 형식으로 포맷팅"""
    if not logs or len(logs.strip()) == 0:
        return f"{title}\n```\n로그가 없습니다.\n```"
    
    # 슬랙 메시지 길이 제한 (4000자)
    if len(logs) > 3500:
        logs = logs[-3500:] + "\n...(로그가 잘렸습니다)"
    
    return f"{title}\n```\n{logs}\n```"

@app.route('/slack/commands', methods=['POST'])
def handle_slack_command():
    """슬랙 슬래시 명령어 처리"""
    
    # 슬랙 서명 검증 (개발 환경에서는 우회)
    # if SLACK_SIGNING_SECRET and not signature_verifier.is_valid_request(request.get_data(), request.headers):
    #     return jsonify({"error": "Invalid request signature"}), 403
    
    # 슬래시 명령어 데이터 파싱
    command_data = request.form
    command = command_data.get('command')
    text = command_data.get('text', '').strip()
    user_id = command_data.get('user_id')
    channel_id = command_data.get('channel_id')
    
    logger.info(f"슬래시 명령어 수신: {command} {text} from user {user_id}")
    
    # 즉시 응답 (슬랙 3초 제한)
    immediate_response = {"response_type": "ephemeral", "text": "🔍 로그를 조회 중입니다..."}
    
    # 백그라운드에서 실제 로그 처리
    if command == '/로그' or command == '/logs':
        if text == 'discord' or text == '디스코드':
            logs = get_discord_bot_logs(30)
            message = format_logs_for_slack(logs, "🤖 Discord 봇 로그")
        elif text == 'prometheus' or text == '프로메테우스':
            logs = get_pod_logs("monitoring", "prometheus-5dd845868d-ppjj2", 30)
            message = format_logs_for_slack(logs, "📊 Prometheus 로그")
        elif text == 'alertmanager' or text == '알림':
            logs = get_pod_logs("monitoring", None, 30)
            # Alertmanager Pod 찾기
            cmd = "kubectl get pods -n monitoring -l app=alertmanager -o jsonpath='{.items[0].metadata.name}'"
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            if result.returncode == 0 and result.stdout.strip():
                pod_name = result.stdout.strip()
                logs = get_pod_logs("monitoring", pod_name, 30)
                message = format_logs_for_slack(logs, "🚨 Alertmanager 로그")
            else:
                message = "❌ Alertmanager Pod를 찾을 수 없습니다"
        elif text == 'grafana' or text == '그라파나':
            cmd = "kubectl get pods -n monitoring -l app=grafana -o jsonpath='{.items[0].metadata.name}'"
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            if result.returncode == 0 and result.stdout.strip():
                pod_name = result.stdout.strip()
                logs = get_pod_logs("monitoring", pod_name, 30)
                message = format_logs_for_slack(logs, "📈 Grafana 로그")
            else:
                message = "❌ Grafana Pod를 찾을 수 없습니다"
        elif text == 'status' or text == '상태':
            message = get_monitoring_status()
        else:
            # 기본: Discord 봇 로그
            logs = get_discord_bot_logs(20)
            message = format_logs_for_slack(logs, "🤖 Discord 봇 로그 (최근 20줄)")
            
            # 사용법 안내 추가
            message += "\n\n💡 *사용법:*\n"
            message += "• `/로그` 또는 `/로그 discord` - Discord 봇 로그\n"
            message += "• `/로그 prometheus` - Prometheus 로그\n"
            message += "• `/로그 alertmanager` - Alertmanager 로그\n"
            message += "• `/로그 grafana` - Grafana 로그\n"
            message += "• `/로그 status` - 전체 상태 확인"
        
        # 슬랙으로 메시지 전송
        try:
            if slack_client:
                slack_client.chat_postMessage(
                    channel=channel_id,
                    text=message,
                    mrkdwn=True
                )
                return jsonify({"response_type": "in_channel", "text": "✅ 로그를 확인했습니다!"})
            else:
                # 테스트 모드: 메시지를 콘솔에 출력
                logger.info(f"테스트 모드 - 메시지: {message}")
                return jsonify({"response_type": "in_channel", "text": message})
        except Exception as e:
            logger.error(f"슬랙 메시지 전송 실패: {e}")
            return jsonify({"response_type": "ephemeral", "text": f"❌ 메시지 전송 실패: {str(e)}"})
    
    return jsonify(immediate_response)

@app.route('/health')
def health():
    """헬스 체크 엔드포인트"""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
