#simulator device 1 for mqtt message publishing
import paho.mqtt.client as paho
import time
import random
import warnings

#Esconder o aviso de versão antiga
warnings.filterwarnings("ignore", category=DeprecationWarning)
#hostname
broker="localhost"
#port
port=1883

def on_publish(client, userdata, result):
    print("Dispositivo 1: Dados Publicados.")
    pass
    
client = paho.Client(client_id="admin", callback_api_version=paho.CallbackAPIVersion.VERSION1)
client.on_publish = on_publish
client.connect(broker,port)
print("Conectado o broker")

#Definindo o tópico
TOPICO_MATCH = "jogo/matchmaking"

#criando mensagem
message = "Jogador buscando partida..."

#publicando mensagem
ret= client.publish(TOPICO_MATCH, message)
