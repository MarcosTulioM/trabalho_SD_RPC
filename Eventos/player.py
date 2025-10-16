#simulator device 1 for mqtt message publishing
import paho.mqtt.client as paho
import time
import random
import warnings
import tkinter as tk
from tkinter import ttk
import threading

player_id = f"player_{random.randint(1000, 9999)}"
jogadores_conectados = {player_id}  # Adiciona o próprio jogador
partida_anunciada = False           # flag para não anunciar várias vezes

#Esconder o aviso de versão antiga
warnings.filterwarnings("ignore", category=DeprecationWarning)
#hostname
broker="localhost"
#port
port=1883

def on_publish(client, userdata, result):
    pass

#Definindo os tópicos
TOPICO_MATCH = "jogo/matchmaking"
TOPICO_PRESENCA = f"jogo/matchmaking/players/{player_id}"

client = paho.Client(client_id=player_id, callback_api_version=paho.CallbackAPIVersion.VERSION1)
client.on_publish = on_publish
client.will_set(TOPICO_PRESENCA, payload=None, retain=True)  # Limpa o retained ao desconectar inesperado
client.connect(broker,port)
client.publish(TOPICO_PRESENCA, payload="online", retain=True)
print("Conectado ao broker")

# Interface
janela = tk.Tk()
janela.title(f"Matchmaking - {player_id}")
janela.geometry("400x250")
janela.resizable(False, False)

status_label = ttk.Label(janela, text="Conectado ao broker!", font=("Arial", 14))
status_label.pack(pady=30)

#Função para iniciar o matchmaking
def iniciar_matchmaking():
    status_label.config(text="Buscando partida...")
    botao_buscar.config(state="disabled") #Desabilita o botão depois de clicar para não iniciar duas vezes
    #Rodando o loop MQTT em thread separada pra não travar a interface
    threading.Thread(target=client.loop_forever, daemon=True).start()

botao_buscar = ttk.Button(janela, text="Buscar Partida", command=iniciar_matchmaking)
botao_buscar.pack(pady=20)

#Função para evitar os erros ao fechar a janela
def fechar_janela():
    print("Encerrando matchmaking...")
    try:
        client.disconnect()
        client.loop_stop()
    except:
        pass
    janela.destroy()

janela.protocol("WM_DELETE_WINDOW", fechar_janela)

janela.mainloop()


#Se inscrevendo nos topicos
client.subscribe("jogo/matchmaking/players/#")
client.subscribe(TOPICO_MATCH)

#Função chamada quando chega novas mensagens no tópico
def on_message(client, userdata, msg):
    global partida_anunciada
    conteudo = msg.payload.decode()

    #Mantém os jogadores conectados sincronizados em todos os clientes
    if msg.topic.startswith("jogo/matchmaking/players/"):
        id_recebido = msg.topic.split("/")[-1]

        # Se o payload for None, o jogador saiu (LWT limpa)
        if msg.payload and msg.payload.decode() == "online":
            jogadores_conectados.add(id_recebido)
        else:
            jogadores_conectados.discard(id_recebido)
        
        if len(jogadores_conectados) < 3:
            if partida_anunciada:
                print(f"Um jogador saiu! Voltando ao matchmaking...")
                partida_anunciada = False
        #Se o número de jogadores voltar a ser 3, cria uma nova partida
        elif not partida_anunciada and len(jogadores_conectados) == 3:
            partida_anunciada = True
            if player_id == min(jogadores_conectados):
                print(f"\n Nova partida formada automaticamente! Jogadores: {jogadores_conectados}")
                client.publish(TOPICO_MATCH, "Partida encontrada!", retain=False)
        
        print(f"[PRESENÇA] jogadores agora conectados: {jogadores_conectados}")
        return

    if "Partida encontrada!" in conteudo:
        print(f"\n {player_id}: Iniciando partida com jogadores {jogadores_conectados}...\n")
        #Para de ouvir o loop
        client.loop_stop()
    
    # Apenas imprime (sem retornar ainda)
    print(f"[Mensagem recebida de tópico {msg.topic}] {conteudo}")

    # Se for uma mensagem de entrada de matchmaking
    if "entrou no matchmaking" in conteudo:
        id_recebido = conteudo.split()[0]

        # Adiciona o id
        jogadores_conectados.add(id_recebido)

        # Ignora as mensagens do próprio jogador nas próximas partes
        if id_recebido == player_id:
            return
        
        print(f"Jogadores conectados até agora: {jogadores_conectados}")

    #Se já houver 3 jogadores conectados, o jogador com menos ID anuncia a partida
    if not partida_anunciada and len(jogadores_conectados) == 3:
        partida_anunciada = True
        if player_id == min(jogadores_conectados):
            print("\nPartida encontrada! Jogadores prontos:", jogadores_conectados)
            time.sleep(0.5) #Pequena pausa para entregar as mensagens anteriores
            client.publish(TOPICO_MATCH, "Partida encontrada!", retain=False)

client.on_message = on_message

#Criando mensagem
message = f"{player_id} entrou no matchmaking!"

#Publicando a mensagem criada
client.publish(TOPICO_MATCH, message)

#Rodar indefinidamente
client.loop_forever()
