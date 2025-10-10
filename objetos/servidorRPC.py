import rpyc

# Dicionário global compartilhado entre todos os jogadores
posicoes = {}

class ServicoDoJogo(rpyc.Service):
    def exposed_publicar_movimento(self, id_jogador, x, y, cor=None):
        global posicoes
        if id_jogador not in posicoes:
            posicoes[id_jogador] = {'x': x, 'y': y, 'cor': cor}
        else:
            posicoes[id_jogador]['x'] = x
            posicoes[id_jogador]['y'] = y
        print(f"Posição de {id_jogador} atualizada para ({x}, {y})")
        return "OK"

    def exposed_obter_posicoes(self):
        global posicoes
        return posicoes

    def on_connect(self, conn):
        print(f"Novo jogador conectado: {conn}")

    def on_disconnect(self, conn):
        global posicoes
        print(f"Jogador desconectado: {conn}")

if __name__ == "__main__":
    from rpyc.utils.server import ThreadedServer
    PORTA = 18861
    servidor = ThreadedServer(ServicoDoJogo, port=PORTA, protocol_config={"allow_pickle": True})
    print(f"Servidor RPC escutando na porta {PORTA}...")
    servidor.start()
