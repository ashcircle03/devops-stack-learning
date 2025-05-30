#!/bin/bash
# Test Discord Bot Metrics and Health Endpoints

echo "🧪 Discord Bot Monitoring Test Script"
echo "======================================"

# Test 1: Health Check
echo -e "\n1. 🏥 Testing Health Endpoint..."
kubectl exec discord-bot-85d6d4474-k82rb -- python3 -c "
import urllib.request
import json
try:
    response = urllib.request.urlopen('http://localhost:8000/health')
    data = json.loads(response.read().decode())
    print(f'✅ Health Check: {data}')
except Exception as e:
    print(f'❌ Health Check Failed: {e}')
"

# Test 2: Metrics endpoint
echo -e "\n2. 📊 Testing Metrics Endpoint..."
kubectl exec discord-bot-85d6d4474-k82rb -- python3 -c "
import urllib.request
try:
    response = urllib.request.urlopen('http://localhost:8000/metrics')
    content = response.read().decode()
    lines = content.split('\n')
    discord_metrics = [line for line in lines if 'discord_bot' in line and not line.startswith('#')]
    print(f'✅ Metrics Endpoint Active')
    print(f'📈 Found {len(discord_metrics)} Discord bot metrics')
    for metric in discord_metrics[:5]:  # Show first 5 metrics
        print(f'   - {metric}')
    if len(discord_metrics) > 5:
        print(f'   ... and {len(discord_metrics) - 5} more')
except Exception as e:
    print(f'❌ Metrics Test Failed: {e}')
"

# Test 3: Bot Status
echo -e "\n3. 🤖 Discord Bot Status..."
kubectl get pods -l app=discord-bot --no-headers | while read line; do
    name=$(echo $line | awk '{print $1}')
    status=$(echo $line | awk '{print $3}')
    echo "   Pod: $name - Status: $status"
done

# Test 4: Service Discovery
echo -e "\n4. 🔍 Service Discovery..."
kubectl get svc discord-bot --no-headers | while read line; do
    name=$(echo $line | awk '{print $1}')
    type=$(echo $line | awk '{print $2}')
    port=$(echo $line | awk '{print $5}')
    echo "   Service: $name - Type: $type - Port: $port"
done

echo -e "\n✨ Test completed!"
