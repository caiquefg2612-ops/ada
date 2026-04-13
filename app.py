import requests
import hashlib
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import fdb

app = Flask(__name__)
app.secret_key = "chave_secreta_ada_2025"


ADMIN_FIXO = {
    "id": 999,
    "nome": "Administrador ADA",
    "email": "admin@ada.com",
    "senha_hash": hashlib.sha256("admin123".encode()).hexdigest(),
    "tipo": "admin"
}



def get_db_connection():
    try:
        conn = fdb.connect(
            host='localhost',
            database=r'C:\Users\Usuario\Downloads\BANCO.FDB',
            user='SYSDBA',
            password='SYSDBA',
            charset='UTF8'
        )
        return conn
    except:
        try:
            conn = fdb.connect(
                database='C:\\ADA\\ADA.FDB',
                user='SYSDBA',
                password='masterkey',
                charset='UTF8'
            )
            return conn
        except:
            try:
                conn = fdb.connect(
                    database='C:\\ADA\\ADA.FDB',
                    user='SYSDBA',
                    password='',
                    charset='UTF8'
                )
                return conn
            except Exception as e:
                print(f"Erro ao conectar: {e}")
                raise e


# ==================== CONFIGURAÇÃO DA IA ====================
CHAVE_API = ""
URL_IA = ""

HEADERS = {
    "Authorization": f"Bearer {CHAVE_API}",
    "Content-Type": "application/json"
}


def chamar_ia(prompt):
    try:
        data = {
            "model": "openrouter/free",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.3
        }
        resposta = requests.post(URL_IA, headers=HEADERS, json=data)
        resposta.raise_for_status()
        return resposta.json()['choices'][0]['message']['content']
    except Exception as e:
        return f"Erro na IA: {str(e)}"


def classificar_demanda(texto):
    prompt = f"""
    Classifique a seguinte demanda de acessibilidade em UMA das categorias: 
    'Arquitetônica', 'Comunicacional', 'Atitudinal', 'Tecnológica'.

    Responda APENAS com o nome da categoria, nada mais.

    Demanda: "{texto}"
    """
    return chamar_ia(prompt).strip()


def sugerir_solucao(demanda, categoria):
    prompt = f"""
    Você é o assistente ADA da Petrobras. Para a seguinte demanda de acessibilidade:

    Demanda: "{demanda}"
    Categoria: {categoria}

    Responda no seguinte formato EXATO:
    Solução: [solução prática]
    Área: [TI, RH, Engenharia, etc]
    Prazo: [dias]
    """
    resposta = chamar_ia(prompt)

    resultado = {"solucao": "", "area": "A definir", "prazo": "A definir"}

    for linha in resposta.split('\n'):
        linha = linha.strip()
        if linha.startswith("Solução:") or linha.startswith("Solucao:"):
            resultado["solucao"] = linha.replace("Solução:", "").replace("Solucao:", "").strip()
        elif linha.startswith("Área:") or linha.startswith("Area:"):
            resultado["area"] = linha.replace("Área:", "").replace("Area:", "").strip()
        elif linha.startswith("Prazo:"):
            resultado["prazo"] = linha.replace("Prazo:", "").strip()

    return resultado


# ==================== FUNÇÕES DO BANCO ====================
def criar_tabelas():
    conn = get_db_connection()
    cursor = conn.cursor()

    # Criar tabela USUARIOS
    try:
        cursor.execute("SELECT 1 FROM USUARIOS")
    except:
        cursor.execute("""
            CREATE TABLE USUARIOS (
                ID INTEGER NOT NULL PRIMARY KEY,
                NOME VARCHAR(100) NOT NULL,
                EMAIL VARCHAR(100) NOT NULL UNIQUE,
                SENHA VARCHAR(64) NOT NULL,
                TIPO VARCHAR(20),
                DEFICIENCIA VARCHAR(100),
                DATA_CADASTRO TIMESTAMP
            )
        """)
        conn.commit()
        print("Tabela USUARIOS criada")

    # Criar tabela DEMANDAS
    try:
        cursor.execute("SELECT 1 FROM DEMANDAS")
    except:
        cursor.execute("""
            CREATE TABLE DEMANDAS (
                ID INTEGER NOT NULL PRIMARY KEY,
                USUARIO_ID INTEGER NOT NULL,
                TITULO VARCHAR(200) NOT NULL,
                DESCRICAO VARCHAR(2000) NOT NULL,
                LOCALIZACAO VARCHAR(200),
                CATEGORIA VARCHAR(50),
                STATUS VARCHAR(20),
                SOLUCAO_SUGERIDA VARCHAR(2000),
                AREA_RESPONSAVEL VARCHAR(100),
                PRAZO_ESTIMADO VARCHAR(100),
                DATA_CRIACAO TIMESTAMP,
                SOLUCAO_EDITADA VARCHAR(2000)
            )
        """)
        conn.commit()
        print("Tabela DEMANDAS criada")
    else:
        # Verificar se a coluna SOLUCAO_EDITADA existe
        try:
            cursor.execute("SELECT SOLUCAO_EDITADA FROM DEMANDAS WHERE 1=0")
        except:
            cursor.execute("ALTER TABLE DEMANDAS ADD SOLUCAO_EDITADA VARCHAR(2000)")
            conn.commit()
            print("Coluna SOLUCAO_EDITADA adicionada")

    conn.close()


def criar_usuario(nome, email, senha, deficiencia=""):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT COALESCE(MAX(ID), 0) + 1 FROM USUARIOS")
    novo_id = cursor.fetchone()[0]

    senha_hash = hashlib.sha256(senha.encode()).hexdigest()

    cursor.execute("""
        INSERT INTO USUARIOS (ID, NOME, EMAIL, SENHA, TIPO, DEFICIENCIA, DATA_CADASTRO)
        VALUES (?, ?, ?, ?, 'user', ?, ?)
    """, (novo_id, nome, email, senha_hash, deficiencia, datetime.now()))

    conn.commit()
    conn.close()
    return novo_id


# Criar tabelas ao iniciar
try:
    criar_tabelas()
    print("Banco de dados verificado")
except Exception as e:
    print(f"Atenção ao verificar banco: {e}")


# ==================== ROTAS ====================
@app.route('/')
def index():
    if 'usuario_id' in session:
        if session['tipo'] == 'admin':
            return redirect(url_for('dashboard_admin'))
        return redirect(url_for('dashboard_user'))
    return redirect(url_for('login'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        senha = request.form['senha']
        senha_hash = hashlib.sha256(senha.encode()).hexdigest()

        if email == ADMIN_FIXO['email'] and senha_hash == ADMIN_FIXO['senha_hash']:
            session['usuario_id'] = ADMIN_FIXO['id']
            session['usuario_nome'] = ADMIN_FIXO['nome']
            session['tipo'] = 'admin'
            return redirect(url_for('dashboard_admin'))

        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT ID, NOME, TIPO FROM USUARIOS WHERE EMAIL = ? AND SENHA = ?", (email, senha_hash))
            user = cursor.fetchone()
            conn.close()
        except Exception as e:
            return render_template('login.html', erro=f"Erro no banco: {e}")

        if user:
            session['usuario_id'] = user[0]
            session['usuario_nome'] = user[1]
            session['tipo'] = user[2]
            return redirect(url_for('dashboard_user'))
        else:
            return render_template('login.html', erro="E-mail ou senha inválidos")

    return render_template('login.html')


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))


@app.route('/criar_usuario', methods=['GET', 'POST'])
def criar_usuario_view():
    erro = None
    if request.method == 'POST':
        nome = request.form['nome']
        email = request.form['email']
        senha = request.form['senha']
        deficiencia = request.form.get('deficiencia', '')

        try:
            criar_usuario(nome, email, senha, deficiencia)
            return redirect(url_for('login'))
        except Exception as e:
            erro = f"Erro ao criar usuário: {e}"

    return render_template('criar_usuario.html', erro=erro)


@app.route('/dashboard/user')
def dashboard_user():
    if 'usuario_id' not in session or session['tipo'] != 'user':
        return redirect(url_for('login'))

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT ID, TITULO, CATEGORIA, STATUS, DATA_CRIACAO, SOLUCAO_SUGERIDA, SOLUCAO_EDITADA, AREA_RESPONSAVEL
            FROM DEMANDAS 
            WHERE USUARIO_ID = ? 
            ORDER BY DATA_CRIACAO DESC
        """, (session['usuario_id'],))
        demandas = cursor.fetchall()
        conn.close()
    except Exception as e:
        demandas = []
        print(f"Erro: {e}")

    return render_template('dashboard_user.html', demandas=demandas, nome=session['usuario_nome'])


@app.route('/nova_demanda', methods=['GET', 'POST'])
def nova_demanda():
    if 'usuario_id' not in session or session['tipo'] != 'user':
        return redirect(url_for('login'))

    if request.method == 'POST':
        titulo = request.form['titulo']
        descricao = request.form['descricao']
        localizacao = request.form.get('localizacao', '')

        categoria = classificar_demanda(descricao)
        solucao_ia = sugerir_solucao(descricao, categoria)

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT COALESCE(MAX(ID), 0) + 1 FROM DEMANDAS")
        novo_id = cursor.fetchone()[0]

        cursor.execute("""
            INSERT INTO DEMANDAS (ID, USUARIO_ID, TITULO, DESCRICAO, LOCALIZACAO, CATEGORIA, 
                                  STATUS, SOLUCAO_SUGERIDA, AREA_RESPONSAVEL, PRAZO_ESTIMADO, DATA_CRIACAO)
            VALUES (?, ?, ?, ?, ?, ?, 'PENDENTE', ?, ?, ?, ?)
        """, (novo_id, session['usuario_id'], titulo, descricao, localizacao, categoria,
              solucao_ia['solucao'], solucao_ia['area'], solucao_ia['prazo'], datetime.now()))

        conn.commit()
        conn.close()

        return redirect(url_for('dashboard_user'))

    return render_template('nova_demanda.html')


@app.route('/dashboard/admin')
def dashboard_admin():
    if 'usuario_id' not in session or session['tipo'] != 'admin':
        return redirect(url_for('login'))

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT d.ID, u.NOME, d.TITULO, d.CATEGORIA, d.STATUS, d.DATA_CRIACAO
            FROM DEMANDAS d
            JOIN USUARIOS u ON d.USUARIO_ID = u.ID
            ORDER BY d.DATA_CRIACAO DESC
        """)
        demandas = cursor.fetchall()

        cursor.execute("SELECT COUNT(*) FROM DEMANDAS")
        total = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM DEMANDAS WHERE STATUS = 'PENDENTE'")
        pendentes = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM USUARIOS WHERE TIPO = 'user'")
        total_usuarios = cursor.fetchone()[0]

        conn.close()
    except Exception as e:
        demandas = []
        total = 0
        pendentes = 0
        total_usuarios = 0
        print(f"Erro: {e}")

    return render_template('dashboard_admin.html',
                           demandas=demandas,
                           total=total,
                           pendentes=pendentes,
                           total_usuarios=total_usuarios,
                           nome=session['usuario_nome'])


@app.route('/admin/demanda/<int:demanda_id>')
def ver_demanda(demanda_id):
    if 'usuario_id' not in session or session['tipo'] != 'admin':
        return redirect(url_for('login'))

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT d.*, u.NOME, u.EMAIL, u.DEFICIENCIA
        FROM DEMANDAS d
        JOIN USUARIOS u ON d.USUARIO_ID = u.ID
        WHERE d.ID = ?
    """, (demanda_id,))
    demanda = cursor.fetchone()
    conn.close()

    return render_template('ver_demanda.html', demanda=demanda)


@app.route('/admin/salvar_solucao', methods=['POST'])
def salvar_solucao():
    if 'usuario_id' not in session or session['tipo'] != 'admin':
        return jsonify({"erro": "Não autorizado"}), 401

    data = request.get_json()
    demanda_id = data.get('demanda_id')
    nova_solucao = data.get('solucao')

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE DEMANDAS SET SOLUCAO_EDITADA = ? WHERE ID = ?", (nova_solucao, demanda_id))
    conn.commit()
    conn.close()

    return jsonify({"sucesso": True})


@app.route('/admin/sugerir_nova_solucao', methods=['POST'])
def sugerir_nova_solucao():
    if 'usuario_id' not in session or session['tipo'] != 'admin':
        return jsonify({"erro": "Não autorizado"}), 401

    data = request.get_json()
    demanda_id = data.get('demanda_id')
    pergunta = data.get('pergunta', 'Sugira uma solução alternativa')

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT DESCRICAO, CATEGORIA FROM DEMANDAS WHERE ID = ?", (demanda_id,))
    demanda = cursor.fetchone()
    conn.close()

    if demanda:
        descricao, categoria = demanda
        prompt = f"""
        Você é o assistente ADA da Petrobras. Para a demanda abaixo, responda APENAS com a solução:

        Demanda: "{descricao}"
        Categoria: {categoria}
        Pergunta do admin: "{pergunta}"
        """
        nova_solucao = chamar_ia(prompt)
        return jsonify({"solucao": nova_solucao})

    return jsonify({"erro": "Demanda não encontrada"}), 404


@app.route('/admin/atualizar_status', methods=['POST'])
def atualizar_status():
    if 'usuario_id' not in session or session['tipo'] != 'admin':
        return jsonify({"erro": "Não autorizado"}), 401

    data = request.get_json()
    demanda_id = data.get('demanda_id')
    novo_status = data.get('status')

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE DEMANDAS SET STATUS = ? WHERE ID = ?", (novo_status, demanda_id))
    conn.commit()
    conn.close()

    return jsonify({"sucesso": True})


@app.route('/admin/relatorios')
def relatorios():
    if 'usuario_id' not in session or session['tipo'] != 'admin':
        return redirect(url_for('login'))

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT CATEGORIA, COUNT(*) as TOTAL
        FROM DEMANDAS
        GROUP BY CATEGORIA
    """)
    stats_categoria = cursor.fetchall()

    cursor.execute("""
        SELECT STATUS, COUNT(*) as TOTAL
        FROM DEMANDAS
        GROUP BY STATUS
    """)
    stats_status = cursor.fetchall()

    conn.close()

    return render_template('relatorios.html',
                           stats_categoria=stats_categoria,
                           stats_status=stats_status)


if __name__ == '__main__':
    app.run(debug=True, host='127.0.0.1', port=5000)
