import sqlite3

# Conectar ao banco de dados
conn = sqlite3.connect('DADOS.db')
cursor = conn.cursor()

# Criar a tabela 'dados_recebidos' com as colunas adicionais
def criar_tabela():
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS dados_recebidos (
            codObjeto TEXT PRIMARY KEY,
            tipoPostalCategoria TEXT,
            dtPrevista TEXT,
            descricaoEvento TEXT,
            dtHrCriadoEvento TEXT,
            uf TEXT,
            cidade TEXT
        )
    ''')

criar_tabela()

# Fechar a conexão
conn.close()