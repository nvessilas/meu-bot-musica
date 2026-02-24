import os
import logging
import httpx
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters

# Configuração de Logs
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
TOKEN = os.environ.get('TELEGRAM_TOKEN')

async def baixar_audio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text
    if "youtube.com" in url or "youtu.be" in url:
        msg_espera = await update.message.reply_text("⏳ Acionando o Plano C (Servidor Auxiliar)... Aguarde.")
        
        try:
            # Configurações para pedir a música ao Cobalt
            headers = {
                "Accept": "application/json",
                "Content-Type": "application/json",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
            }
            payload = {
                "url": url,
                "isAudioOnly": True,
                "aFormat": "mp3"
            }
            
            # Usando httpx (já incluído no telegram-bot) para fazer o pedido
            async with httpx.AsyncClient(timeout=120.0) as client:
                logging.info("Enviando pedido para o Cobalt API...")
                resposta = await client.post("https://api.cobalt.tools/", json=payload, headers=headers)
                dados = resposta.json()
                
                # Se o Cobalt retornou o link direto do MP3
                if "url" in dados:
                    url_audio = dados["url"]
                    arquivo_temp = "/tmp/musica.mp3"
                    
                    # Baixa o MP3 do Cobalt para o Render
                    logging.info("Baixando o arquivo do Cobalt...")
                    req_audio = await client.get(url_audio)
                    with open(arquivo_temp, "wb") as f:
                        f.write(req_audio.content)
                    
                    # Envia o MP3 para você no Telegram
                    await update.message.reply_audio(audio=open(arquivo_temp, 'rb'))
                    await msg_espera.delete()
                    
                    # Limpa o arquivo do servidor
                    os.remove(arquivo_temp)
                    logging.info("Música enviada com sucesso pelo Plano C!")
                else:
                    erro = dados.get('text', 'Erro desconhecido')
                    await update.message.reply_text(f"❌ O servidor auxiliar encontrou um problema: {erro}")
                    
        except Exception as e:
            logging.error(f"Erro no Plano C: {e}")
            await update.message.reply_text(f"❌ Falha no Plano C: {str(e)}")
            
    else:
        await update.message.reply_text("Pode mandar o link do YouTube! 🎵")

if __name__ == '__main__':
    if not TOKEN:
        print("ERRO: Variável TELEGRAM_TOKEN não encontrada!")
    else:
        application = ApplicationBuilder().token(TOKEN).build()
        application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), baixar_audio))
        print("Bot iniciado com o Plano C (Cobalt API)!")
        application.run_polling()
