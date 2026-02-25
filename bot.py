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

# Configuração base do motor de download
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

def limpar_titulo(titulo_sujo):
    """Apaga os lixos do título do YouTube (tudo depois de traços ou parênteses)"""
    # Exemplo: "Junto a Ti - Graduação 2025" vira "Junto a Ti"
    titulo_limpo = re.split(r'[-|\[\(]', titulo_sujo)[0].strip()
    return titulo_limpo if titulo_limpo else titulo_sujo

async def processar_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text
    if "youtube.com" not in url and "youtu.be" not in url:
        await update.message.reply_text("Mande um link do YouTube ou digite /buscar seguido do nome da música! 🎵")
        return

    msg_espera = await update.message.reply_text("⏳ Iniciando a Busca Implacável...")

    # 1. Tenta baixar o vídeo original direto do YouTube (Modo Kamikaze com TV client)
    try:
        opts_direto = ydl_opts_base.copy()
        opts_direto['extractor_args'] = {'youtube': {'client': ['tv']}}
        logging.info("Tentativa 1: YouTube Direto")
        
        with YoutubeDL(opts_direto) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info).rsplit('.', 1)[0] + ".mp3"
            
        await update.message.reply_audio(audio=open(filename, 'rb'), title=info.get('title'))
        os.remove(filename)
        await msg_espera.delete()
        return
    except Exception as e:
        logging.warning("YouTube bloqueou. Indo para o Truque do Espelho Inteligente.")

    # 2. Se o YouTube bloqueou, usa o Truque do Espelho com o "Limpador de Títulos"
    try:
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
                    if 'entries' in info and len(info['entries']) > 0:
                        info_musica = info['entries'][0]
                    else:
                        info_musica = info
                        
                    filename = ydl.prepare_filename(info_musica).rsplit('.', 1)[0] + ".mp3"

                await update.message.reply_audio(audio=open(filename, 'rb'), title=info_musica.get('title'))
                os.remove(filename)
                await msg_espera.delete()
                return
    except Exception as e:
        logging.error(f"Erro no Espelho Limpo: {e}")

    # 3. Se tudo falhar, sugere a busca manual
    aviso_falha = (
        "❌ O link automático falhou (O nome estava muito confuso ou foi bloqueado).\n\n"
        "Mas não se preocupe! Tente pesquisar o nome da música manualmente. Digite:\n\n"
        "`/buscar Nome da Música`"
    )
    await msg_espera.edit_text(aviso_falha, parse_mode='Markdown')

# --- PARTE NOVA: O MODO INTERATIVO DE BUSCA ---

async def comando_buscar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Junta todas as palavras que o usuário digitou depois do /buscar
    pesquisa = " ".join(context.args)
    if not pesquisa:
        await update.message.reply_text("⚠️ Você esqueceu o nome da música! Digite assim:\n`/buscar Tudo é Perda`", parse_mode='Markdown')
        return

    msg_espera = await update.message.reply_text(f"🔍 Procurando por '{pesquisa}'...")

    try:
        # Busca a música SEM baixar ainda (download=False)
        busca_sc = f"scsearch1:{pesquisa}"
        with YoutubeDL({'format': 'bestaudio/best', 'noplaylist': True}) as ydl:
            info = ydl.extract_info(busca_sc, download=False)
            if 'entries' in info and len(info['entries']) > 0:
                info_musica = info['entries'][0]
            else:
                info_musica = info

        titulo_encontrado = info_musica.get('title')
        url_da_musica = info_musica.get('webpage_url') or info_musica.get('url')

        # Salva a música na "memória" do bot
        context.user_data['musica_url'] = url_da_musica
        context.user_data['musica_titulo'] = titulo_encontrado

        # Cria os botões na tela
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
        await msg_espera.edit_text("❌ Não encontrei nenhuma música com esse exato nome. Tente usar outras palavras!")

async def responder_botoes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    clique = update.callback_query
    await clique.answer() # Avisa o Telegram que recebemos o clique

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
            # Baixa a música que estava na memória
            with YoutubeDL(ydl_opts_base) as ydl:
                info = ydl.extract_info(url, download=True)
                filename = ydl.prepare_filename(info).rsplit('.', 1)[0] + ".mp3"

            await clique.message.reply_audio(audio=open(filename, 'rb'), title=titulo)
            os.remove(filename)
            await clique.message.delete() # Apaga a mensagem de "Baixando..."
        except Exception as e:
            logging.error(f"Erro no botão baixar: {e}")
            await clique.edit_message_text("❌ Erro na hora de fazer o download do arquivo.")

if __name__ == '__main__':
    if not TOKEN:
        print("ERRO: Variável TELEGRAM_TOKEN não encontrada!")
    else:
        application = ApplicationBuilder().token(TOKEN).build()
        
        # O bot agora entende Mensagens normais, Comandos (/buscar) e Cliques nos botões!
        application.add_handler(CommandHandler("buscar", comando_buscar))
        application.add_handler(CallbackQueryHandler(responder_botoes))
        application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), processar_link))
        
        print("Bot Canivete Suíço Iniciado com Sucesso!")
        application.run_polling()
