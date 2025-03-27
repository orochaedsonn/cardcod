processar_planilha(r"C:\Users\MKT_PC1_L1\Desktop\CardCod\cardcod\gift_cards.xlsx")


import pandas as pd
import psycopg2
from psycopg2 import sql

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
                codigo VARCHAR(16) UNIQUE NOT NULL,
                item VARCHAR(255) NOT NULL,
                status VARCHAR(20) DEFAULT 'disponivel'
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
                    INSERT INTO gift_cards (codigo, item) VALUES (%s, %s)
                    ON CONFLICT (codigo) DO NOTHING;
                ''', (row['Codigo'], row['Item']))
            except Exception as e:
                print("Erro ao inserir dados:", e)
        conn.commit()
        cur.close()
        conn.close()

if __name__ == "__main__":
    criar_tabelas()
    processar_planilha("gift_cards.xlsx")
