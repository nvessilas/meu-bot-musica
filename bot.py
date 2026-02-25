import os
import re
import logging
import httpx
from yt_dlp import YoutubeDL
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, CommandHandler, CallbackQueryHandler, filters

# Configuração de Logs
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
TOKEN = os.environ.get('TELEGRAM_TOKEN')

ydl_opts_base = {
    'format': 'bestaudio/best',
    'postprocessors': [{
        'key': 'FFmpegExtractAudio',
        'preferredcodec': 'mp3',
        'preferredquality': '192',
    }],
    'ffmpeg_location': './ffmpeg',
    'outtmpl': '/tmp/%(title)s.%(ext)s',
    'noplaylist': True,
}

# A ROLETA: Lista de servidores alternativos para tentar driblar o YouTube
servidores_cobalt = [
    "https://api.cobalt.tools",
    "https://api.cobalt.q-n.space",
    "https://co.wuk.sh"
]

def limpar_titulo(titulo_sujo):
    titulo_limpo = re.split(r'[-|\[\(]', titulo_sujo)[0].strip()
    return titulo_limpo if titulo_limpo else titulo_sujo

async def processar_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text
    if "youtube.com" not in url and "youtu.be" not in url:
        await update.message.reply_text("Mande um link do YouTube ou digite /buscar seguido do nome da música! 🎵")
        return

    msg_espera = await update.message.reply_text("⏳ Roleta de Servidores ativada! Tentando baixar o vídeo original...")

    # 1. Tenta a Roleta (O melhor para os seus vídeos de teclado/oração)
    try:
        payload = {"url": url, "isAudioOnly": True, "aFormat": "mp3"}
        headers = {"Accept": "application/json", "Content-Type": "application/json"}
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            for api in servidores_cobalt:
                try:
                    logging.info(f"Tentando servidor: {api}")
                    resp = await client.post(api, json=payload, headers=headers)
                    if resp.status_code == 200 and "url" in resp.json():
                        url_direta = resp.json()["url"]
                        
                        await msg_espera.edit_text("✅ Servidor secreto encontrou! Baixando o áudio original...")
                        arquivo_temp = f"/tmp/musica_{update.message.message_id}.mp3"
                        
                        req_audio = await client.get(url_direta, timeout=60.0)
                        with open(arquivo_temp, "wb") as f:
                            f.write(req_audio.content)
                        
                        await update.message.reply_audio(audio=open(arquivo_temp, 'rb'))
                        os.remove(arquivo_temp)
                        await msg_espera.delete()
                        return # Sucesso! Para o código aqui.
                except Exception as e:
                    logging.warning(f"Servidor {api} falhou. Tentando o próximo...")
    except Exception as e:
        logging.error(f"Roleta falhou: {e}")

    # 2. Se a roleta falhar, tenta o Truque do Espelho como última esperança
    try:
        await msg_espera.edit_text("⏳ YouTube bloqueou os servidores. Tentando o Truque do Espelho...")
        api_oembed = f"https://www.youtube.com/oembed?url={url}&format=json"
        async with httpx.AsyncClient() as client:
            resp = await client.get(api_oembed)
            if resp.status_code == 200:
                titulo_original = resp.json().get("title")
                titulo_limpo = limpar_titulo(titulo_original)
                
                await msg_espera.edit_text(f"🔍 Título original: {titulo_original}\n✨ Buscando versão limpa: '{titulo_limpo}' no SoundCloud...")

                busca_sc = f"scsearch1:{titulo_limpo}"
                with YoutubeDL(ydl_opts_base) as ydl:
                    info = ydl.extract_info(busca_sc, download=True)
                    
                    # CORREÇÃO DO BUG AQUI TAMBÉM!
                    if 'entries' in info and len(info['entries']) > 0:
                        info_musica = info['entries'][0]
                    else:
                        await msg_espera.edit_text("❌ Não encontrei esse áudio em nenhum lugar. É muito específico! 😭")
                        return
                        
                    filename = ydl.prepare_filename(info_musica).rsplit('.', 1)[0] + ".mp3"

                await update.message.reply_audio(audio=open(filename, 'rb'), title=info_musica.get('title'))
                os.remove(filename)
                await msg_espera.delete()
                return
    except Exception as e:
        logging.error(f"Erro no Espelho Limpo: {e}")

    # 3. Se tudo der errado
    await msg_espera.edit_text("❌ Todos os métodos falharam hoje. O YouTube bloqueou tudo.")


async def comando_buscar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    pesquisa = " ".join(context.args)
    if not pesquisa:
        await update.message.reply_text("⚠️ Você esqueceu o nome da música! Digite assim:\n`/buscar Nome da Música`", parse_mode='Markdown')
        return

    msg_espera = await update.message.reply_text(f"🔍 Procurando por '{pesquisa}'...")

    try:
        busca_sc = f"scsearch1:{pesquisa}"
        with YoutubeDL({'format': 'bestaudio/best', 'noplaylist': True}) as ydl:
            info = ydl.extract_info(busca_sc, download=False)
            
            # CORREÇÃO DO BUG PRINCIPAL DO PAPAGAIO!
            if 'entries' in info and len(info['entries']) > 0:
                info_musica = info['entries'][0]
            else:
                await msg_espera.edit_text("❌ Poxa, não encontrei nenhuma música com esse nome. Tente usar outras palavras ou nomes mais simples!")
                return

        titulo_encontrado = info_musica.get('title')
        url_da_musica = info_musica.get('webpage_url') or info_musica.get('url')

        context.user_data['musica_url'] = url_da_musica
        context.user_data['musica_titulo'] = titulo_encontrado

        botoes = [
            [InlineKeyboardButton("✅ SIM, PODE BAIXAR", callback_data="baixar_sim")],
            [InlineKeyboardButton("❌ NÃO, TENTAR OUTRA", callback_data="baixar_nao")]
        ]
        teclado = InlineKeyboardMarkup(botoes)

        await msg_espera.edit_text(
            f"🎵 Eu achei essa música:\n*{titulo_encontrado}*\n\nÉ essa que você quer?",
            reply_markup=teclado,
            parse_mode='Markdown'
        )
    except Exception as e:
        logging.error(f"Erro na busca manual: {e}")
        await msg_espera.edit_text("❌ Erro ao pesquisar no servidor.")


async def responder_botoes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    clique = update.callback_query
    await clique.answer()

    if clique.data == "baixar_nao":
        await clique.edit_message_text("Ok, cancelei! Use `/buscar` com outro nome para tentarmos de novo.")
        return

    if clique.data == "baixar_sim":
        url = context.user_data.get('musica_url')
        titulo = context.user_data.get('musica_titulo')

        if not url:
            await clique.edit_message_text("❌ Esqueci qual era a música (O tempo expirou). Faça a busca de novo!")
            return

        await clique.edit_message_text(f"⬇️ Baixando: *{titulo}*...\nIsso pode levar alguns segundos.", parse_mode='Markdown')

        try:
            with YoutubeDL(ydl_opts_base) as ydl:
                info = ydl.extract_info(url, download=True)
                filename = ydl.prepare_filename(info).rsplit('.', 1)[0] + ".mp3"

            await clique.message.reply_audio(audio=open(filename, 'rb'), title=titulo)
            os.remove(filename)
            await clique.message.delete()
        except Exception as e:
            logging.error(f"Erro no botão baixar: {e}")
            await clique.edit_message_text("❌ Erro na hora de fazer o download do arquivo.")


if __name__ == '__main__':
    if not TOKEN:
        print("ERRO: Variável TELEGRAM_TOKEN não encontrada!")
    else:
        application = ApplicationBuilder().token(TOKEN).build()
        application.add_handler(CommandHandler("buscar", comando_buscar))
        application.add_handler(CallbackQueryHandler(responder_botoes))
        application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), processar_link))
        print("Bot Iniciado com Roleta e Anti-Papagaio!")
        application.run_polling()
