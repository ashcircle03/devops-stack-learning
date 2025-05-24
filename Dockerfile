FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ARG BOT_TOKEN
ENV BOT_TOKEN=$BOT_TOKEN

CMD ["python", "discord_bot.py"]
