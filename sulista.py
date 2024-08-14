import telebot
from telebot import types
import os
import time
from tqdm import tqdm
import urllib.parse
from datetime import timedelta, datetime
import requests
import json
import base64
import random
import string

print("Bot ligado com sucesso")

CHAVE_API = "7184148164:AAGTH5U1JTGLZ1o88HfSrJ99bN_lgIQr2pQ"
bot = telebot.TeleBot('7184148164:AAGTH5U1JTGLZ1o88HfSrJ99bN_lgIQr2pQ')

resultados_cache = {}

def buscar_arquivo(termo_busca):
    if termo_busca in resultados_cache:
        return resultados_cache[termo_busca]
    else:
        resultado_busca = buscar_no_banco_de_dados(termo_busca)
        resultados_cache[termo_busca] = resultado_busca
        return resultado_busca

def buscar_no_banco_de_dados(termo_busca):
    return 'Conteúdo do arquivo encontrado no banco de dados'

ARQUIVO_LOGINS = "sulista/logins.txt"
LOGINS_SALVOS = {}

def carregar_logins():
    if os.path.exists(ARQUIVO_LOGINS):
        with open(ARQUIVO_LOGINS, "r") as arquivo:
            return eval(arquivo.read())
    else:
        return {}

def salvar_logins(logins):
    with open(ARQUIVO_LOGINS, "w") as arquivo:
        arquivo.write(str(logins))

def salvar_login(login, senha, url, user_id):
    if user_id not in LOGINS_SALVOS:
        LOGINS_SALVOS[user_id] = []
    novo_login = {"login": login, "senha": senha, "url": url}
    LOGINS_SALVOS[user_id].append(novo_login)
    salvar_logins(LOGINS_SALVOS)

def ver_logins_salvos(user_id):
    if user_id in LOGINS_SALVOS and LOGINS_SALVOS[user_id]:
        return "\n".join([f"{login['url']} : {login['login']} : {login['senha']}\n" for login in LOGINS_SALVOS[user_id]])
    else:
        return "Nenhum login salvo."

LOGINS_SALVOS = carregar_logins()

@bot.message_handler(commands=['login'])
def handle_login(message):
    args = message.text.split(" ")
    if len(args) == 4:
        url = args[1]
        login = args[2]
        senha = args[3]
        salvar_login(login, senha, url, message.from_user.id)
        bot.reply_to(message, "Login salvo com sucesso!")
    else:
        bot.reply_to(message, "Comando inválido. Use: /login URL login senha")

@bot.message_handler(commands=['meus_logins'])
def handle_meus_logins(message):
    bot.reply_to(message, ver_logins_salvos(message.from_user.id))

ARQUIVO_USUARIOS_PERMITIDOS = "sulista/usuarios_permitidos.txt"
USUARIOS_AUTORIZADOS = {}

def salvar_usuarios_permitidos():
    with open(ARQUIVO_USUARIOS_PERMITIDOS, "w") as arquivo:
        for usuario_id, data_expiracao in USUARIOS_AUTORIZADOS.items():
            if data_expiracao:
                data_expiracao_str = data_expiracao.strftime("%Y-%m-%d %H:%M:%S")
                arquivo.write(f"{usuario_id},{data_expiracao_str}\n")
            else:
                arquivo.write(f"{usuario_id}\n")

def carregar_usuarios_permitidos():
    try:
        with open(ARQUIVO_USUARIOS_PERMITIDOS, "r") as arquivo:
            for linha in arquivo:
                dados = linha.strip().split(",")
                if len(dados) >= 2:
                    user_id = dados[0]
                    data_expiracao = dados[1]
                    USUARIOS_AUTORIZADOS[int(user_id)] = datetime.strptime(data_expiracao, "%Y-%m-%d %H:%M:%S")
    except FileNotFoundError:
        return {}
    return USUARIOS_AUTORIZADOS

USUARIOS_AUTORIZADOS = carregar_usuarios_permitidos()
IDS_PERMITIDOS_COMANDOS_ADMIN = [6847670004]

def limpar_nome_arquivo(nome_arquivo):
    caracteres_invalidos = ['/', '\\', ':', '*', '?', '"', '<', '>', '|']
    for char in caracteres_invalidos:
        nome_arquivo = nome_arquivo.replace(char, '_')
    return nome_arquivo

def searchr_e_escrever_linhas_com_palavra_chave(nome_arquivo, palavra_chave):
    linhas_relevantes = []
    erros_decodificacao = 0
    with open(nome_arquivo, 'rb') as arquivo:
        for linha_bytes in arquivo:
            try:
                linha = linha_bytes.decode('utf-8')
                if palavra_chave in linha:
                    linhas_relevantes.append(linha.strip())
            except UnicodeDecodeError:
                erros_decodificacao += 1
    return linhas_relevantes, erros_decodificacao

def main(palavra_chave, chat_id, message_id):
    pasta_db = "db"
    pasta_buscados = "buscados"

    palavra_chave_encoded = urllib.parse.quote(palavra_chave)

    nome_arquivo_saida = f"{limpar_nome_arquivo(palavra_chave_encoded)}.txt"

    caminho_arquivo_buscado = os.path.join(pasta_buscados, nome_arquivo_saida)
    if os.path.exists(caminho_arquivo_buscado):
        with open(caminho_arquivo_buscado, 'rb') as documento:
            bot.send_document(chat_id, documento)
        bot.delete_message(chat_id, message_id)
        return

    arquivos_txt = [arquivo for arquivo in os.listdir(pasta_db) if arquivo.endswith('.txt')]

    with tqdm(total=len(arquivos_txt), desc="Progresso da pesquisa") as progresso_barra:
        total_linhas_encontradas = 0
        total_erros_decodificacao = 0
        linhas_relevantes_set = set() 
        for arquivo_txt in arquivos_txt:
            caminho_arquivo = os.path.join(pasta_db, arquivo_txt)
            linhas, erros_decodificacao = searchr_e_escrever_linhas_com_palavra_chave(caminho_arquivo, palavra_chave)
            total_linhas_encontradas += len(linhas)
            total_erros_decodificacao += erros_decodificacao
            linhas_relevantes_set.update(linhas)
            progresso_barra.update(1)
            time.sleep(0.1)

        linhas_relevantes = list(linhas_relevantes_set)

    if total_linhas_encontradas == 0:
        mensagem = "Nenhuma linha relevante encontrada."
    else:
        mensagem = ""

    if mensagem:
        bot.send_message(chat_id, mensagem)
    else:
        caminho_saida = os.path.join(pasta_buscados, nome_arquivo_saida)
        with open(caminho_saida, 'wb') as documento:
            documento.write("\n".join(linhas_relevantes).encode('utf-8'))
        with open(caminho_saida, 'rb') as documento:
            bot.send_document(chat_id, documento)
        bot.delete_message(chat_id, message_id)
        

ULTIMO_USO_BUSCA = {}

@bot.message_handler(commands=["buscar"])
def handle_search(message):
    chat_id = message.chat.id
    user_id = message.from_user.id
    if user_id not in USUARIOS_AUTORIZADOS:
        bot.reply_to(message, "Desculpe, você não está autorizado a usar este bot.")
        return

    if user_id in ULTIMO_USO_BUSCA and (datetime.now() - ULTIMO_USO_BUSCA[user_id]).seconds < 1:
        tempo_restante = timedelta(seconds=10) - (datetime.now() - ULTIMO_USO_BUSCA[user_id])
        minutos_restantes = tempo_restante.seconds // 10
        bot.reply_to(message, f"Por favor, espere {minutos_restantes} minutos para usar o comando novamente.")
        return

    texto = message.text.split(maxsplit=1)
    if len(texto) > 1:
        palavra_chave = texto[1]
        
        print(f"({user_id}) acabou de usar o comando /buscar.")
        
        caminho_arquivo_buscado = os.path.join("buscados", limpar_nome_arquivo(palavra_chave) + ".txt")
        if os.path.exists(caminho_arquivo_buscado):
            with open(caminho_arquivo_buscado, 'rb') as documento:
                bot.send_document(chat_id, documento)
            return
            
        msg = bot.reply_to(message, "Buscando URL nas bases de dados...\n\nPor favor, espere o bot enviar essa busca para fazer outra; caso contrário, o bot ficará com atraso e você poderá ser banido de usar o bot.")
        main(palavra_chave, chat_id, msg.message_id)
        ULTIMO_USO_BUSCA[user_id] = datetime.now()
    else:
        bot.reply_to(message, "Por favor, inclua a palavra-chave após o comando /buscar.")


def remover_autorizacao_periodicamente():
    while True:
        usuarios_remover = []
        for usuario_id, data_expiracao in USUARIOS_AUTORIZADOS.items():
            if data_expiracao and data_expiracao <= datetime.now():
                usuarios_remover.append(usuario_id)

        for usuario_id in usuarios_remover:
            del USUARIOS_AUTORIZADOS[usuario_id]
            bot.send_message(usuario_id, "Sua autorização para usar o bot expirou. Quer renovar seu plano? Chame: @eusoujudas 🎉")

        salvar_usuarios_permitidos()
        time.sleep(60)

import threading
threading.Thread(target=remover_autorizacao_periodicamente).start()

def remover_autorizacoes_expiradas():
    global USUARIOS_AUTORIZADOS
    agora = datetime.now()
    usuarios_remover = []
    for user_id, data_expiracao in USUARIOS_AUTORIZADOS.items():
        if data_expiracao is not None and data_expiracao <= agora:
            usuarios_remover.append(user_id)
    for user_id in usuarios_remover:
        del USUARIOS_AUTORIZADOS[user_id]
    salvar_usuarios_permitidos()

@bot.message_handler(commands=['gpt'])
def handle_pergunta_command(message):
    chat_id = message.chat.id
    user_id = message.from_user.id
    if user_id in USUARIOS_AUTORIZADOS:
        pergunta = message.text.replace('/gpt', '').strip()
        response = requests.get(f"https://chatgpt.apinepdev.workers.dev/?question={pergunta}")
        
        if response.status_code == 200:
            resposta = response.json().get("answer")
            bot.reply_to(message, resposta)
        else:
            bot.reply_to(message, "Desculpe, não consegui obter uma resposta no momento. Por favor, tente novamente mais tarde.")
    else:
        bot.reply_to(message, "Você não está autorizado a usar este comando.")

@bot.message_handler(commands=["autorizar"])
def autorizar_usuario(message):
    user_id = message.from_user.id
    if user_id in IDS_PERMITIDOS_COMANDOS_ADMIN:
        parametros = message.text.split()
        if len(parametros) >= 2 and parametros[1].isdigit():
            novo_usuario_id = int(parametros[1])
            plano = parametros[2] if len(parametros) > 2 else None
            duracao = None
            if plano:
                duracao = {
                "diario": timedelta(days=1),
                "5dias": timedelta(days=5),
                "semanal": timedelta(weeks=1),
               "2semanas": timedelta(weeks=2),
                "mensal": timedelta(days=30),
                "3meses": timedelta(days=90),
                "anual": timedelta(days=365),
                "vitalicio": timedelta(days=9999999),
                "1minuto": timedelta(minutes=1)
                  }.get(plano)
            data_expiracao = datetime.now() + duracao if duracao else None
            if novo_usuario_id not in USUARIOS_AUTORIZADOS:
                USUARIOS_AUTORIZADOS[novo_usuario_id] = data_expiracao
                salvar_usuarios_permitidos()
                bot.reply_to(message, f"Usuário {novo_usuario_id} autorizado com sucesso!")
                if data_expiracao:
                    mensagem_notificacao = f"Você foi autorizado para usar o bot até {data_expiracao.strftime('%d/%m/%Y')}!"
                else:
                    mensagem_notificacao = "Você foi autorizado para usar o bot permanentemente!"
                bot.send_message(novo_usuario_id, mensagem_notificacao)
            else:
                bot.reply_to(message, "Este usuário já está autorizado.")
        else:
            bot.reply_to(message, "Formato incorreto. Use /autorizar seguido do ID do usuário e do plano desejado.")
    else:
        bot.reply_to(message, "Desculpe, você não tem permissão para autorizar usuários.")

@bot.message_handler(commands=["remover"])
def remover_autorizacao_usuario(message):
    user_id = message.from_user.id

    if user_id in IDS_PERMITIDOS_COMANDOS_ADMIN:
        parametros = message.text.split()
        if len(parametros) >= 2 and parametros[1].isdigit():
            usuario_id = int(parametros[1])

            if usuario_id in USUARIOS_AUTORIZADOS:
                del USUARIOS_AUTORIZADOS[usuario_id]
                salvar_usuarios_permitidos()

                bot.reply_to(message, f"Autorização removida para o usuário {usuario_id}.")

            else:
                bot.reply_to(message, "Este usuário não está autorizado.")
        else:
            bot.reply_to(message, "Formato incorreto. Use /remover_autorizacao seguido do ID do usuário.")
    else:
        bot.reply_to(message, "Desculpe, você não tem permissão para remover autorizações.")


@bot.message_handler(commands=["dono"])
def handle_dono(message):
    bot.reply_to(message, "Entendi! Se você estiver enfrentando algum problma fale comigo basta apenas me chamar meu usuario e esse. @eusoujudas 🎉.")

@bot.message_handler(commands=["planos"])
def handle_planos(message):
    bot.reply_to(message, """Olá! Seja bem-vindo ao menu de planos!

• Plano diário: R$ 5,00
• Plano semanal: R$ 10,00
• Plano duas semanas: R$ 18,00
• Plano mensal: R$ 40,00
• Plano 3 meses R$ 90,00
• Plano anual: R$ 150,00
• Plano vitalício: R$ 200,00

Se interessou? Chame @eusoujudas para adquirir seu acesso agora mesmo! 🎉""")


@bot.message_handler(commands=['id'])
def send_id(message):
    chat_id = message.chat.id
    bot.reply_to(message, f"{chat_id}")
    
@bot.message_handler(commands=["start"])
def handle_start(message):
    chat_id = message.chat.id
    bot.send_message(chat_id, """Olá! eu sou o sulista - logs Um bot de login 100% funcional Sou um bot desenvolvido pelo @eusoujudas 🎉. Meus comandos estão aqui embaixo:
    
─────────────────────────

🔎 /buscar -> Este comando lhe permite procurar logins com base em uma palavra-chave ou URL.
🔑 /login -> Salvar logins para acesso rápido e fácil.
🔐 /meus_logins -> Ver logins salvos anteriormente.

─────────────────────────
👤 /dono -> Contatar o dono do bot para obter ajuda.
💎 /loja -> Conheça nossa Loja de logins.
💳 /planos -> Conhecer os planos disponíveis.""")

@bot.message_handler(commands=["menu"])
def handle_start(message):
    chat_id = message.chat.id
    bot.send_message(chat_id, """Olá! eu sou o sulista - logs - bot Um bot de login 100% funcional Sou um bot desenvolvido pelo @eusoujudas 🎉. Meus comandos estão aqui embaixo:
    
─────────────────────────

🔎 /buscar -> Este comando lhe permite procurar logins com base em uma palavra-chave ou URL.
🔑 /login -> Salvar logins para acesso rápido e fácil.
🔐 /meus_logins -> Ver logins salvos anteriormente.

─────────────────────────
👤 /dono -> Contatar o dono do bot para obter ajuda.
💎 /loja -> Conheça nossa Loja de logins.
💳 /planos -> Conhecer os planos disponíveis.""")

pasta_salvar = "sulistalogs"

usuarios_interagiram = set()

arquivo_usuarios_interagiram = os.path.join(pasta_salvar, 'usuarios_interagiram.txt')

if not os.path.exists(arquivo_usuarios_interagiram):
    with open(arquivo_usuarios_interagiram, 'w'):
        pass

with open(arquivo_usuarios_interagiram, 'r') as file:
    for line in file:
        usuarios_interagiram.add(int(line.strip()))

@bot.message_handler(commands=["ts"])
def enviar_mensagem_para_autorizados(message):
    user_id = message.from_user.id

    if user_id in IDS_PERMITIDOS_COMANDOS_ADMIN:
        comando, *mensagem = message.text.split()
        if len(mensagem) > 0:
            mensagem_para_enviar = ' '.join(mensagem)
            for autorizado_id in usuarios_interagiram:
                try:
                    bot.send_message(autorizado_id, mensagem_para_enviar)
                except telebot.apihelper.ApiException as e:
                    if "Forbidden: user is deactivated" in str(e):
                        print(f"Usuário {autorizado_id} está desativado e não pode receber mensagens.")
                    else:
                        print(f"Erro ao enviar mensagem para {autorizado_id}: {e}")

            bot.reply_to(message, "Mensagem enviada para todos os usuários.")
        else:
            bot.reply_to(message, "Formato incorreto. Use /ts <sua mensagem para os usuários>.")
    else:
        bot.reply_to(message, "Desculpe, você não tem permissão para enviar mensagens para todos os usuários autorizados.")

@bot.message_handler(func=lambda message: True)
def armazenar_usuarios_interagiram(message):
    user_id = message.from_user.id
    if user_id not in usuarios_interagiram:
        usuarios_interagiram.add(user_id)
        with open(arquivo_usuarios_interagiram, 'a') as file:
            file.write(str(user_id) + '\n')

INTERVALO_VERIFICACAO = 1000

while True:
    try:
        bot.polling(none_stop=True)
    except Exception as e:
        print(f"Erro: {e}")
        time.sleep(0.01)
