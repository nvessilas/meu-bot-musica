#!/usr/bin/env bash
set -e

# Baixa o FFmpeg portátil para Linux (não precisa de root)
wget https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz
tar -xf ffmpeg-release-amd64-static.tar.xz
mv ffmpeg-*-amd64-static/ffmpeg .
rm -rf ffmpeg-*-amd64-static* ffmpeg-release-amd64-static.tar.xz

# Instala as bibliotecas do Python
pip install -r requirements.txt
