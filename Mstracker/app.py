from flask import Flask, render_template, request, redirect, url_for
from datetime import datetime
from datetime import datetime, timedelta
import requests
import sqlite3
import json

app = Flask(__name__)

def gerar_token():
    url = 'https://api.correios.com.br/token/v1/autentica/cartaopostagem'
    headers = {
        'accept': 'application/json',
        'Content-Type': 'application/json',
        'Authorization': 'Basic MTM5NTYzNjUwMDAxMzY6WG1oZng2WUVVUHVwYVFiYnJoOHBYdFlrcmtjZHlYc0hUbmdYOXJJVA=='
    }
    data = {
        "numero": "0077126548"
    }

    try:
        response = requests.post(url, headers=headers, json=data)

        if response.status_code in [200, 201]:
            token_data = response.json()
            token = token_data.get('token')
            print(token)

            with open('token.json', 'w') as token_file:
                json.dump({'token': token}, token_file)

            print("Token criado com sucesso.")
            atualizar_dados()
            return token
        else:
            print("Erro na requisição de token:", response.status_code)
            print("Resposta:", response.text)
            return None
    except Exception as e:
        print("Erro ao gerar o token:", e)
        return None
    
def ler_token():
    with open('token.json', 'r') as token_file:
        token_data = json.load(token_file)
        return token_data.get('token')

def atualizar_dados(codigo_objeto):
    resultado = 'U'
    auth_token = ler_token()

    api_url = f'https://api.correios.com.br/srorastro/v1/objetos?codigosObjetos={codigo_objeto}&resultado={resultado}'

    headers = {
        'Authorization': f'Bearer {auth_token}',
        'accept': 'application/json'
    }

    try:
        response = requests.get(api_url, headers=headers)

        if response.status_code == 200:
            dados_api = response.json()

            conn = sqlite3.connect('DADOS.db')
            cursor = conn.cursor()

            for objeto in dados_api.get("objetos", []):
                codObjeto = objeto.get("codObjeto")
                tipoPostalCategoria = objeto.get("tipoPostal", {}).get("categoria")
                dtPrevista = objeto.get("dtPrevista")
                eventos = objeto.get("eventos", [])

                for evento in eventos:
                    unidade = evento.get("unidade", {})
                    descricaoEvento = evento.get("descricao")
                    dtHrCriadoEvento = evento.get("dtHrCriado")

                    uf = unidade.get("endereco", {}).get("uf")
                    cidade = unidade.get("endereco", {}).get("cidade")

                    # Inserir ou atualizar os dados na tabela
                    cursor.execute('''
                        INSERT OR REPLACE INTO dados_recebidos (
                            codObjeto, tipoPostalCategoria, dtPrevista,
                            descricaoEvento, dtHrCriadoEvento, uf, cidade
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        codObjeto, tipoPostalCategoria, dtPrevista, 
                        descricaoEvento, dtHrCriadoEvento, uf, cidade
                    ))

            conn.commit()
            conn.close()

            print("Atualização feita com sucesso.")
        elif response.status_code == 403:  # Token inválido
            print("Token inválido. Gerando um novo token...")
            auth_token = gerar_token()

            if auth_token is not None:
                    atualizar_dados(codigo_objeto)
            else:
                print("Não foi possível gerar um novo token. Consulta não realizada.")
        else:
            print("Erro na requisição da API dos Correios. Status code:", response.status_code)
            print("Resposta:", response.text)
    except Exception as e:
        print("Erro ao atualizar dados:", e)

@app.route('/')
def index():
    conn = sqlite3.connect('DADOS.db')
    cursor = conn.cursor()
    codigo_pesquisado = request.args.get('codigo_pesquisado')

    if codigo_pesquisado:
        # Se houver um código pesquisado, execute a consulta apenas para esse código
        cursor.execute('SELECT * FROM dados_recebidos WHERE codObjeto = ? ORDER BY dtHrCriadoEvento DESC', (codigo_pesquisado,))
    else:
        # Caso contrário, exiba os registros dos ultimos 30 dias
        cursor.execute('''
            SELECT * FROM dados_recebidos
            WHERE dtHrCriadoEvento >= ?
            ORDER BY dtHrCriadoEvento DESC
        ''', (datetime.now() - timedelta(days=30),))

    dados = cursor.fetchall()
    conn.close()

    return render_template('index.html', dados=dados)

@app.route('/consultar', methods=['POST'])
def consultar():
    codigo_objeto = request.form['codigo_objeto']
    auth_token = ler_token()

    if auth_token is None or not ler_token():
        print("Token não encontrado ou inválido. Gerando um novo token...")
        auth_token = gerar_token()

        if auth_token is not None:
            atualizar_dados(codigo_objeto)
        else:
            print("Não foi possível gerar um novo token. Consulta não realizada.")
            return redirect(url_for('index'))  # Redireciona de volta para a página inicial
    else:
        atualizar_dados(codigo_objeto)

    return redirect(url_for('index', codigo_pesquisado=codigo_objeto))  # Redireciona de volta para a página inicial

@app.route('/atualizar-todos')
def atualizar_todos():
    auth_token = ler_token()

    if auth_token is None:
        print("Token não encontrado. Gerando um novo token...")
        auth_token = gerar_token()

        if auth_token is not None:
            # Consultar todos os objetos que você deseja atualizar (por exemplo, todos os objetos na tabela)
            conn = sqlite3.connect('DADOS.db')
            cursor = conn.cursor()
            cursor.execute('SELECT DISTINCT codObjeto FROM dados_recebidos')  # Supondo que codObjeto seja o campo que identifica os objetos
            codigos_objetos = [row[0] for row in cursor.fetchall()]
            conn.close()

            for codigo_objeto in codigos_objetos:
                atualizar_dados(codigo_objeto)
            
            return redirect(url_for('index'))
        else:
            print("Não foi possível gerar um novo token. Atualização não realizada.")
            return redirect(url_for('index'))
    else:
        conn = sqlite3.connect('DADOS.db')
        cursor = conn.cursor()
        cursor.execute('SELECT DISTINCT codObjeto FROM dados_recebidos') 
        codigos_objetos = [row[0] for row in cursor.fetchall()]
        conn.close()

        for codigo_objeto in codigos_objetos:
            atualizar_dados(codigo_objeto)
        
        return redirect(url_for('index'))

@app.route('/filtrar', methods=['POST'])
def filtrar():
    selected_option = request.form['filter-select']
    
    conn = sqlite3.connect('DADOS.db')
    cursor = conn.cursor()

    if selected_option == 'last-month':
        data_limite = datetime.now() - timedelta(days=30)
        query = '''
            SELECT * FROM dados_recebidos
            WHERE dtHrCriadoEvento >= ?
            ORDER BY dtHrCriadoEvento DESC
        '''
        cursor.execute(query, (data_limite,))
    elif selected_option == 'last-week':
        data_limite = datetime.now() - timedelta(days=7)
        query = '''
            SELECT * FROM dados_recebidos
            WHERE dtHrCriadoEvento >= ?
            ORDER BY dtHrCriadoEvento DESC
        '''
        cursor.execute(query, (data_limite,))
    elif selected_option == 'all':
        data_limite = datetime.now() - timedelta(days=365)
        query = '''
            SELECT * FROM dados_recebidos
            WHERE dtHrCriadoEvento >= ?
            ORDER BY dtHrCriadoEvento DESC
        '''
        cursor.execute(query, (data_limite,))

    dados = cursor.fetchall()
    conn.close()

    return render_template('index.html', dados=dados)
    
if __name__ == '__main__':
    app.run(debug=True)
