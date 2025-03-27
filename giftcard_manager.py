import pandas as pd
import psycopg2

# Configuração do banco de dados no Neon
DB_CONFIG = {
    'dbname': 'baserecar',
    'user': 'neondb_owner',
    'password': 'npg_OAqHKv6bj4tQ',
    'host': 'ep-rapid-dew-a5yqklt8-pooler.us-east-2.aws.neon.tech',
    'port': '5432',
    'sslmode': 'require'
}

def conectar_db():
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        return conn
    except Exception as e:
        print("Erro ao conectar no banco de dados:", e)
        return None

def criar_tabelas():
    conn = conectar_db()
    if conn:
        cur = conn.cursor()
        cur.execute('''
            CREATE TABLE IF NOT EXISTS gift_cards (
                id SERIAL PRIMARY KEY,
                sku VARCHAR(50) UNIQUE NOT NULL,
                nome_produto VARCHAR(255) NOT NULL,
                tipo_produto VARCHAR(50) NOT NULL,
                duracao VARCHAR(20) NOT NULL,
                status VARCHAR(20) DEFAULT 'não usado',
                historico_uso TEXT DEFAULT 'Não usado'
            );
        ''')
        conn.commit()
        cur.close()
        conn.close()

def processar_planilha(arquivo):
    df = pd.read_excel(arquivo)
    conn = conectar_db()
    if conn:
        cur = conn.cursor()
        for _, row in df.iterrows():
            try:
                cur.execute('''
                    INSERT INTO gift_cards (sku, nome_produto, tipo_produto, duracao, status, historico_uso)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT (sku) DO UPDATE 
                    SET status = EXCLUDED.status, historico_uso = EXCLUDED.historico_uso;
                ''', (row['SKU'], row['Nome do produto'], row['Tipo de produto'], row['Duração'], row['Status'], row['Histórico de uso']))
            except Exception as e:
                print("Erro ao inserir dados:", e)
        conn.commit()
        cur.close()
        conn.close()

if __name__ == "__main__":
    criar_tabelas()
    processar_planilha("gift_cards.xlsx")
