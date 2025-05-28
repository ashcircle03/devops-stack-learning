#!/bin/bash

# Docker 소켓 권한 수정 스크립트
echo "Docker 소켓 권한을 수정합니다..."
sudo chmod 666 /var/run/docker.sock
echo "Docker 소켓 권한이 수정되었습니다."
