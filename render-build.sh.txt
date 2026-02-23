#!/usr/bin/env bash
# Instala o ffmpeg no servidor do Render
apt-get update && apt-get install -y ffmpeg
# Instala as bibliotecas do Python
pip install -r requirements.txt
