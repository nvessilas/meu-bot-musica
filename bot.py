import os
import re
import logging
import httpx
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters

# Configuração de Logs
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
TOKEN = os.environ.get('TELEGRAM_TOKEN')

# Lista de servidores alternativos do Piped (A rede descentralizada)
servidores_piped = [
    "https://pipedapi.kavin.rocks",
    "https://pipedapi.tokhmi.xyz",
    "https://piped-api.garudalinux.org",
    "https://api.piped.projectsegfau.lt"
]

def extrair_id_video(url):
    """Pega apenas o código do vídeo do YouTube (ex: EgOhjhqxxNw)"""
    match = re.search(r"(?:v=|\/)([0-9A-Za-z_-]{11}).*", url)
    return match.group(1) if match else None

async def baixar_audio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text
    if "youtube.com" in url or "youtu.be" in url:
        video_id = extrair_id_video(url)
        if not video_id:
            await update.message.reply_text("❌ Não consegui identificar o ID do vídeo nesse link.")
            return

        msg_espera = await update.message.reply_text("⏳ Conectando à rede descentralizada... Aguarde.")
        sucesso = False

        async with httpx.AsyncClient(timeout=60.0) as client:
            # Tenta baixar usando cada servidor da nossa lista
            for i, servidor in enumerate(servidores_piped):
                try:
                    logging.info(f"Tentando extrair pelo servidor {i+1}: {servidor}")
                    api_url = f"{servidor}/streams/{video_id}"
                    
                    resposta = await client.get(api_url)
                    if resposta.status_code != 200:
                        continue # Pula para o próximo se der erro
                        
                    dados = resposta.json()
                    if "error" in dados:
                        continue # Pula se o YouTube bloqueou esse servidor
                        
                    audio_streams = dados.get("audioStreams", [])
                    if not audio_streams:
                        continue
                        
                    # Procura o formato M4A (que o Telegram aceita perfeitamente como áudio)
                    melhor_audio = next((s for s in audio_streams if s.get("format") == "M4A"), audio_streams[0])
                    url_download = melhor_audio["url"]
                    
                    # Baixa o arquivo para o Render
                    arquivo_temp = f"/tmp/{video_id}.m4a"
                    logging.info("Link encontrado! Baixando para o bot...")
                    
                    req_audio = await client.get(url_download)
                    with open(arquivo_temp, "wb") as f:
                        f.write(req_audio.content)
                    
                    # Envia para o usuário
                    titulo = dados.get("title", "Audio")
                    await update.message.reply_audio(audio=open(arquivo_temp, 'rb'), title=titulo)
                    
                    # Limpa o servidor e encerra o loop de tentativas
                    os.remove(arquivo_temp)
                    sucesso = True
                    await msg_espera.delete()
                    break 

                except Exception as e:
                    logging.warning(f"Falha no servidor {i+1}: {e}")
                    continue

        if not sucesso:
            await msg_espera.edit_text("❌ Todos os servidores da rede estão bloqueados pelo YouTube no momento. Tente novamente mais tarde.")
            
    else:
        await update.message.reply_text("Pode mandar o link do YouTube! 🎵")

if __name__ == '__main__':
    if not TOKEN:
        print("ERRO: Variável TELEGRAM_TOKEN não encontrada!")
    else:
        application = ApplicationBuilder().token(TOKEN).build()
        application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), baixar_audio))
        print("Bot iniciado com a Rede Descentralizada (Plano D)!")
        application.run_polling()
