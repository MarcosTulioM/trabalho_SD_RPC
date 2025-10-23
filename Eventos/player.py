import paho.mqtt.client as paho
import tkinter as tk
from tkinter import ttk
import random
import time
import warnings
import subprocess
import socket

#Identificação inicial player/tópicos
player_id = f"player_{random.randint(1000, 9999)}"
TOPICO_MATCH = "jogo/matchmaking"
TOPICO_PRESENCA = f"jogo/matchmaking/players/{player_id}"
TOPICO_CONFIRMACAO = "jogo/matchmaking/confirmacao"
TOPICO_ESTADO = "jogo/matchmaking/estado"

#Estados Globais
confirmacoes = {}  #Guarda quem aceitou/recusou
jogadores_conectados = set()
partida_anunciada = False
partida_iniciada = False
entrou_no_matchmaking = False
timer_confirmacao = None  #Controle do tempo limite

#Utilitário para definir publica que a partida foi iniciada
def menor_id(conjunto_ids):
    return min(conjunto_ids, key=lambda s: int(s.split("_")[-1]))

# Interface Tkinter
class MatchmakingUI:
    def __init__(self, player_id):
        self.root = tk.Tk()
        self.root.title(f"Matchmaking - {player_id}")
        self.root.geometry("400x420")
        self.root.resizable(False, False)

        self.status_label = ttk.Label(self.root, text="Aguardando conexão...", font=("Arial", 12, "bold"), foreground="orange")
        self.status_label.pack(pady=10)

        ttk.Label(self.root, text=f"ID do jogador: {player_id}", font=("Arial", 10)).pack()
        ttk.Label(self.root, text="Jogadores conectados:", font=("Arial", 11)).pack(pady=(20, 5))

        self.lista_jogadores = tk.Text(self.root, height=6, width=40, state="disabled", bg="#f7f7f7")
        self.lista_jogadores.pack()

        self.botao_buscar = ttk.Button(self.root, text="Buscar Partida", command=self.buscar_partida)
        self.botao_buscar.pack(pady=25)

        # Botões de confirmação Aceitar/Recusar
        self.botao_aceitar = ttk.Button(self.root, text="Aceitar", command=self.aceitar_partida)
        self.botao_recusar = ttk.Button(self.root, text="Recusar", command=self.recusar_partida)
        self.botao_aceitar.pack_forget()
        self.botao_recusar.pack_forget()

        self.on_buscar_callback = None  #Será atribuído no main

    #Mostra os botões de confirmação
    def mostrar_confirmacao(self):
        self.botao_aceitar.pack(pady=5)
        self.botao_recusar.pack(pady=5)

    #Esconde os botões de confirmação
    def esconder_confirmacao(self):
        self.botao_aceitar.pack_forget()
        self.botao_recusar.pack_forget()

    def aceitar_partida(self):
        confirmar("aceitou")

    def recusar_partida(self):
        confirmar("recusou")

    #Buscar a partida
    def buscar_partida(self):
        self.set_status("Buscando partida...", "blue")
        self.habilitar_botao(False)
        if self.on_buscar_callback:
            self.on_buscar_callback()

    #Função para ajudar a mudar os botões
    def set_status(self, texto, cor="black"):
        self.status_label.config(text=texto, foreground=cor)

    #Função para atualizar a lista de jogadores
    def atualizar_jogadores(self, lista):
        self.lista_jogadores.config(state="normal")
        self.lista_jogadores.delete(1.0, tk.END)
        for jogador in sorted(lista):
            self.lista_jogadores.insert(tk.END, f"• {jogador}\n")
        self.lista_jogadores.config(state="disabled")

    #Função para mudar o botão
    def habilitar_botao(self, ativar=True):
        self.botao_buscar.config(state="normal" if ativar else "disabled")

    #Inicia o looping principal
    def iniciar(self):
        self.root.mainloop()

#Função para registrar a presença com QOS
def set_presenca(ativo: bool, final=False):
    if final:
        client.publish(TOPICO_PRESENCA, payload="", retain=True, qos=1)
    elif ativo:
        client.publish(TOPICO_PRESENCA, payload="online", retain=True, qos=1)

#Função para checar se a partida pode ser formada
def verificar_partida():
    global partida_anunciada
    if not partida_anunciada and len(jogadores_conectados) >= 3:
        partida_anunciada = True
        if player_id == menor_id(jogadores_conectados):
            print(f"[{player_id}] Anunciando partida")
            client.publish(TOPICO_MATCH, "Partida encontrada!", qos=1)

#Função que chama o matchmaking
def iniciar_matchmaking():
    global entrou_no_matchmaking, partida_anunciada, partida_iniciada
    entrou_no_matchmaking = True
    partida_anunciada = False
    partida_iniciada = False
    jogadores_conectados.add(player_id)
    set_presenca(True)
    client.publish(TOPICO_MATCH, f"{player_id} entrou no matchmaking", qos=1)

#Confirma ou recusa a partida
def confirmar(resposta):
    global timer_confirmacao
    confirmacoes[player_id] = resposta
    client.publish(TOPICO_CONFIRMACAO, f"{player_id} {resposta}", qos=1)
    ui.set_status("Aguardando outros jogadores...", "blue")
    ui.esconder_confirmacao()
    if timer_confirmacao:
        ui.root.after_cancel(timer_confirmacao)
        timer_confirmacao = None

#Função para fechar a janela de forma segura
def fechar_janela():
    print(f"[{player_id}] Encerrando...")
    if entrou_no_matchmaking:
        set_presenca(False, final=True)
        time.sleep(0.1)
        client.publish(TOPICO_MATCH, f"{player_id} saiu do matchmaking", qos=1)
    client.loop_stop()
    client.disconnect()
    ui.root.destroy()

#Funções RPC
def servidor_rpc_on(host="localhost", port=18861): #Verifica se o servidor RPC está rodando
    try:
        with socket.create_connection((host,port), timeout=1):
            return True
    except OSError:
        return False
    
def iniciar_rpc_se_necessario():
    if not servidor_rpc_on():
        print("Servidor RPC não encontrado. Iniciando...")
        subprocess.Popen(["python", "servidorRPC.py"])
        time.sleep(2) #Pequena pausa para subir o servidor
    else:
        print("Servidor RPC já está rodando.")

#Função principal das mensagens
def on_message(client, userdata, msg):
    global partida_anunciada, partida_iniciada, timer_confirmacao

    conteudo = msg.payload.decode() if msg.payload else ""
    topico = msg.topic

    #Partida encontrada
    if "Partida encontrada!" in conteudo:
        ui.set_status("Partida encontrada! Aceitar?", "green")
        ui.mostrar_confirmacao()
        confirmacoes.clear()

        #Timeout (10 Segundos)
        def tempo_limite():
            if player_id not in confirmacoes:
                confirmar("recusou")
                ui.set_status("Tempo esgotado! Você recusou automaticamente.", "red")

        timer_confirmacao = ui.root.after(10000, tempo_limite)  #10s
        return

    #Processa confirmações
    if topico == TOPICO_CONFIRMACAO:
        partes = conteudo.split()
        if len(partes) < 2:
            return
        id_jogador, resposta = partes[0], partes[1]
        confirmacoes[id_jogador] = resposta

        aceitos = sum(1 for v in confirmacoes.values() if v == "aceitou")
        ui.set_status(f"{aceitos}/{len(jogadores_conectados)} aceitaram...", "blue")

        #Se for o líder, decide o resultado final
        if player_id == menor_id(jogadores_conectados):
            if len(confirmacoes) == len(jogadores_conectados):
                if all(v == "aceitou" for v in confirmacoes.values()):
                    client.publish(TOPICO_ESTADO, "Partida confirmada!", qos=1)
                else:
                    client.publish(TOPICO_ESTADO, "Partida cancelada!", qos=1)
        return

    #Resultado final
    if topico == TOPICO_ESTADO:
        if "confirmada" in conteudo:
            ui.set_status("Todos prontos! Iniciando jogo...", "green")
            ui.esconder_confirmacao()

            def iniciar_jogo():
                ui.root.destroy()
                iniciar_rpc_se_necessario()
                subprocess.Popen(["python", "game.py"])
            ui.root.after(1500, iniciar_jogo)

        elif "cancelada" in conteudo:
            ui.set_status("Partida cancelada! Voltando ao matchmaking...", "red")
            ui.esconder_confirmacao()
            confirmacoes.clear()
            ui.root.after(3000, ui.habilitar_botao, True)
        return

    #Atualização de presença
    if topico.startswith(TOPICO_PRESENCA):
        id_jogador = topico.split("/")[-1]

        if conteudo == "online":
            jogadores_conectados.add(id_jogador)
        else:
            jogadores_conectados.discard(id_jogador)

        print(f"[PRESENÇA] {id_jogador} → {conteudo or 'offline'}")
        ui.atualizar_jogadores(jogadores_conectados)
        ui.root.after(300, verificar_partida)
        return

    #Entrada ou saída do matchmaking
    if "entrou no matchmaking" in conteudo:
        id_novo = conteudo.split()[0]
        jogadores_conectados.add(id_novo)
        ui.atualizar_jogadores(jogadores_conectados)
        ui.root.after(300, verificar_partida)
        return

    if "saiu do matchmaking" in conteudo:
        id_saiu = conteudo.split()[0]
        jogadores_conectados.discard(id_saiu)
        ui.atualizar_jogadores(jogadores_conectados)
        return

#Inicia a interface
ui = MatchmakingUI(player_id)
ui.on_buscar_callback = iniciar_matchmaking
ui.root.protocol("WM_DELETE_WINDOW", fechar_janela)

#Iniciando MQTT/Definindo os subs
warnings.filterwarnings("ignore", category=DeprecationWarning)
client = paho.Client(client_id=player_id, callback_api_version=paho.CallbackAPIVersion.VERSION1)
client.on_message = on_message
client.connect("localhost", 1883)
client.subscribe(TOPICO_MATCH, qos=1)
client.subscribe("jogo/matchmaking/players/#", qos=1)
client.subscribe(TOPICO_CONFIRMACAO, qos=1)
client.subscribe(TOPICO_ESTADO, qos=1)
client.loop_start()

#Inicia o loop da interface
ui.iniciar()
