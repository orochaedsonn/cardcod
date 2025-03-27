import pandas as pd
import psycopg2
import os
import requests
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

# Configuração do banco de dados no Neon
DB_CONFIG = {
    'dbname': 'baserecar',
    'user': 'neondb_owner',
    'password': 'npg_OAqHKv6bj4tQ',
    'host': 'ep-rapid-dew-a5yqklt8-pooler.us-east-2.aws.neon.tech',
    'port': '5432',
    'sslmode': 'require'
}

# Configuração da Nuvemshop
NUVEMSHOP_TOKEN = "SEU_ACCESS_TOKEN"  # Substitua pelo access_token obtido
NUVEMSHOP_STORE_ID = "SEU_STORE_ID"  # Substitua pelo user_id obtido
NUVEMSHOP_API_URL = f"https://api.nuvemshop.com.br/v1/{NUVEMSHOP_STORE_ID}/orders"

app = FastAPI()

def conectar_db():
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        print("Conexão com o banco de dados Neon estabelecida com sucesso!")
        return conn
    except Exception as e:
        print(f"Erro ao conectar no banco de dados: {str(e)}")
        return None

def criar_tabelas():
    conn = conectar_db()
    if conn is None:
        return
    try:
        with conn.cursor() as cur:
            cur.execute("DROP TABLE IF EXISTS pedidos;")
            cur.execute("DROP TABLE IF EXISTS gift_cards;")
            cur.execute('''
                CREATE TABLE gift_cards (
                    id SERIAL PRIMARY KEY,
                    codigo VARCHAR(16) UNIQUE NOT NULL,
                    item VARCHAR(255) NOT NULL,
                    status VARCHAR(20) DEFAULT 'disponivel'
                );
            ''')
            cur.execute('''
                CREATE TABLE pedidos (
                    id SERIAL PRIMARY KEY,
                    pedido_id VARCHAR(50) UNIQUE NOT NULL,
                    cliente_nome VARCHAR(255),
                    cliente_email VARCHAR(255),
                    codigo_enviado VARCHAR(16),
                    status VARCHAR(20) DEFAULT 'pendente',
                    FOREIGN KEY (codigo_enviado) REFERENCES gift_cards (codigo)
                );
            ''')
            conn.commit()
            print("Tabelas recriadas com sucesso no Neon!")
    except Exception as e:
        print(f"Erro ao criar tabelas: {str(e)}")
    finally:
        conn.close()

def processar_planilha(arquivo):
    caminho_completo = os.path.abspath(arquivo)
    print(f"Tentando acessar o arquivo em: {caminho_completo}")

    if not os.path.exists(caminho_completo):
        raise HTTPException(status_code=404, detail=f"Arquivo {arquivo} não encontrado")

    try:
        df = pd.read_excel(caminho_completo)
        print(f"Planilha lida com sucesso. Total de linhas: {len(df)}")
        print(f"Colunas encontradas: {list(df.columns)}")

        required_columns = ['Codigo', 'Nome_produto']
        if len(df) == 0:
            raise HTTPException(status_code=400, detail="Planilha vazia")
        if not all(col in df.columns for col in required_columns):
            raise HTTPException(status_code=400, detail=f"A planilha deve conter: {required_columns}")

        conn = conectar_db()
        if conn is None:
            raise HTTPException(status_code=500, detail="Erro ao conectar ao banco")

        try:
            with conn.cursor() as cur:
                inserted = 0
                for index, row in df.iterrows():
                    status_raw = str(row['Status']) if 'Status' in df.columns and pd.notna(row['Status']) else 'disponivel'
                    status = 'disponivel' if 'disponivel' in status_raw.lower() else 'usado'
                    cur.execute('''
                        INSERT INTO gift_cards (codigo, item, status)
                        VALUES (%s, %s, %s)
                        ON CONFLICT (codigo) DO NOTHING;
                    ''', (str(row['Codigo']), str(row['Nome_produto']), status))
                    inserted += 1
                conn.commit()
                print(f"Dados inseridos com sucesso! Total de registros: {inserted}")
                return {"message": f"Dados inseridos com sucesso! Total de registros: {inserted}"}
        except Exception as e:
            conn.rollback()
            raise HTTPException(status_code=500, detail=f"Erro ao processar dados: {str(e)}")
        finally:
            conn.close()

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao processar planilha: {str(e)}")

def verificar_dados():
    conn = conectar_db()
    if conn is None:
        raise HTTPException(status_code=500, detail="Erro ao conectar ao banco")
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM gift_cards;")
            rows = cur.fetchall()
            return [{"id": r[0], "codigo": r[1], "item": r[2], "status": r[3]} for r in rows]
    except Exception as e:
        print(f"Erro ao verificar dados: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erro ao listar gift cards: {str(e)}")
    finally:
        conn.close()

def obter_pedidos_nuvemshop():
    headers = {
        "Authentication": f"bearer {NUVEMSHOP_TOKEN}",
        "Content-Type": "application/json",
        "User-Agent": "GiftCardApp (seuemail@exemplo.com)"  # Substitua pelo seu e-mail
    }
    try:
        response = requests.get(NUVEMSHOP_API_URL, headers=headers, params={"status": "paid"})
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        print(f"Erro ao obter pedidos da Nuvemshop: {str(e)}")
        return []

def associar_gift_card(pedido_id, cliente_nome, cliente_email):
    conn = conectar_db()
    if conn is None:
        raise HTTPException(status_code=500, detail="Erro ao conectar ao banco")
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT codigo FROM gift_cards WHERE status = 'disponivel' LIMIT 1;")
            gift_card = cur.fetchone()
            if not gift_card:
                raise HTTPException(status_code=404, detail="Nenhum gift card disponível")

            codigo = gift_card[0]
            cur.execute('''
                INSERT INTO pedidos (pedido_id, cliente_nome, cliente_email, codigo_enviado, status)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (pedido_id) DO NOTHING;
            ''', (pedido_id, cliente_nome, cliente_email, codigo, 'enviado'))
            cur.execute("UPDATE gift_cards SET status = 'usado' WHERE codigo = %s;", (codigo,))
            conn.commit()
            return {"pedido_id": pedido_id, "codigo_enviado": codigo}
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Erro ao associar gift card: {str(e)}")
    finally:
        conn.close()

# Endpoints da API
@app.get("/")
def root():
    print("Recebida requisição para /")
    return {"message": "API de Gift Cards rodando!"}

@app.post("/upload-planilha/")
def upload_planilha(arquivo: str = "gift_cards.xlsx"):
    print(f"Recebida requisição para /upload-planilha/ com arquivo: {arquivo}")
    return processar_planilha(arquivo)

@app.get("/gift-cards/")
def listar_gift_cards():
    print("Recebida requisição para /gift-cards/")
    gift_cards = verificar_dados()
    return gift_cards

@app.get("/monitorar-pedidos/")
def monitorar_pedidos():
    pedidos = obter_pedidos_nuvemshop()
    resultados = []
    for pedido in pedidos:
        pedido_id = str(pedido["id"])
        cliente_nome = pedido["customer"]["name"]
        cliente_email = pedido["customer"]["email"]
        try:
            resultado = associar_gift_card(pedido_id, cliente_nome, cliente_email)
            resultados.append(resultado)
        except HTTPException as e:
            print(f"Erro ao processar pedido {pedido_id}: {str(e)}")
    return {"processados": resultados}

if __name__ == "__main__":
    criar_tabelas()
    try:
        processar_planilha("gift_cards.xlsx")
    except Exception as e:
        print(f"Erro ao processar planilha no início: {str(e)}")
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8001)