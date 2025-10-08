from rpyc.utils.classic import obtain
import turtle
import time
import random
import rpyc
import threading

delay = 0.01

# Score
score = 0
high_score = 0

# Set up the screen
wn = turtle.Screen()
wn.title("Move Game by @Garrocho")
wn.bgcolor("green")
wn.setup(width=1.0, height=1.0, startx=None, starty=None)
wn.tracer(0) # Turns off the screen updates

# gamer 1
head = turtle.Turtle()
head.speed(0)
head.shape("circle")
head.color("red")
head.penup()
head.goto(0,0)
head.direction = "stop"

# Functions
def go_up():
    head.direction = "up"

def go_down():
    head.direction = "down"

def go_left():
    head.direction = "left"

def go_right():
    head.direction = "right"

def close():
    wn.bye()

def move():
    if head.direction == "up":
        y = head.ycor()
        head.sety(y + 2)

    if head.direction == "down":
        y = head.ycor()
        head.sety(y - 2)

    if head.direction == "left":
        x = head.xcor()
        head.setx(x - 2)

    if head.direction == "right":
        x = head.xcor()
        head.setx(x + 2)

# Keyboard bindings
wn.listen()
wn.onkeypress(go_up, "w")
wn.onkeypress(go_down, "s")
wn.onkeypress(go_left, "a")
wn.onkeypress(go_right, "d")
wn.onkeypress(close, "Escape")

#Dicionário para "guardar" os outros jogadores
posicoes_dos_outros = {}
turtles_dos_outros = {}

def sincronizar_posicoes():
    while True:
        global posicoes_dos_outros
        while True:
            try:
                # Pega uma cópia local dos dados do servidor
                posicoes_dos_outros = obtain(conn.root.exposed_obter_posicoes())
            
            except Exception as e:
                # Se a conexão cair, apenas zera as posicões
                print(f"Erro de conexão no assistente: {e}")
                posicoes_dos_outros = {}

            time.sleep(0.05) # Pausa para evitar sobrecarga do servidor

# Conexão com o servidor RPC
print("Conectando ao servidor...")
conn = rpyc.connect('localhost', 18861)
meu_id = f"jogador_{random.randint(1000, 9999)}"
print(f"Conectado! Você é o {meu_id}")

# Inicia a thread que atualiza as posições dos outros jogadores
thread_assistente = threading.Thread(target=sincronizar_posicoes, daemon=True)
thread_assistente.start()

# Main game loop
while True:
    wn.update()
    move()
    conn.root.exposed_publicar_movimento(meu_id, head.xcor(), head.ycor())
    for jogador_id, posicao in posicoes_dos_outros.items():
        if jogador_id == meu_id:
            continue # Pula o próprio jogador

        if jogador_id not in turtles_dos_outros:
            # Jogador novo, cria a turtle
            novo_jogador = turtle.Turtle()
            novo_jogador.speed(0)
            novo_jogador.shape("circle")
            novo_jogador.color("blue")
            novo_jogador.penup()
            turtles_dos_outros[jogador_id] = novo_jogador

        #Atualiza a posição da turtle já existente
        turtles_dos_outros[jogador_id].goto(posicao['x'], posicao['y'])

    time.sleep(delay)


wn.mainloop()
