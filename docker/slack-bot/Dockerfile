FROM python:3.11-slim

WORKDIR /app

# 의존성 설치
COPY src/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# 애플리케이션 코드 복사
COPY src/slack_bot.py .

# ARG/ENV 제거 (쿠버네티스에서 주입)
CMD ["python", "slack_bot.py"]
