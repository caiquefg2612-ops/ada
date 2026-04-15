import requests
import hashlib
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import fdb
import json

app = Flask(__name__)
app.secret_key = "chave_secreta_ada_2025"

# ==================== CONTAS FIXAS ====================
ADMIN_FIXO = {
    "id": 999,
    "nome": "Administrador ADA",
    "email": "admin@ada.com",
    "senha_hash": hashlib.sha256("admin123".encode()).hexdigest(),
    "tipo": "admin"
}

SEDE_FIXA = {
    "id": 998,
    "nome": "Sede ADA",
    "email": "sede@ada.com",
    "senha_hash": hashlib.sha256("sede123".encode()).hexdigest(),
    "tipo": "sede"
}


def get_db_connection():
    try:
        conn = fdb.connect(
            host='localhost',
            database=r'C:\Users\Aluno\Downloads\ada-main\ada-main\BANCO (1).FDB',
            user='SYSDBA',
            password='sysdba',
            charset='NONE'
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


CHAVE_API = "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"
URL_IA = "https://openrouter.ai/api/v1/chat/completions"

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
        resposta = requests.post(URL_IA, headers=HEADERS, json=data, timeout=60)
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


def sugerir_solucao_simples(demanda, categoria):
    """Solução simples para o admin poder editar"""
    prompt = f"""
    Você é o assistente ADA da Petrobras. Para a seguinte demanda de acessibilidade:

    Demanda: "{demanda}"
    Categoria: {categoria}

    Responda no seguinte formato EXATO:
    Solução: [solução prática e objetiva]
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


def sugerir_solucao_complexa(demanda, categoria):
    """Solução complexa e detalhada - apenas para a sede"""
    prompt = f"""
    Você é um especialista em acessibilidade corporativa da Petrobras. 
    Forneça uma SOLUÇÃO COMPLEXA E DETALHADA para a seguinte demanda:

    DEMANDA: "{demanda}"
    CATEGORIA: {categoria}

    Sua resposta deve ser bem estruturada e incluir:

    1. ANÁLISE DO PROBLEMA: (análise detalhada das causas raiz)
    2. SOLUÇÃO PROPOSTA: (solução completa, com etapas e justificativas)
    3. RECURSOS NECESSÁRIOS: (orçamento aproximado, materiais, pessoal)
    4. CRONOGRAMA SUGERIDO: (em semanas/meses)
    5. MÉTRICAS DE SUCESSO: (como medir se a solução funcionou)
    6. PARCEIROS ENVOLVIDOS: (quem precisa ser consultado)

    Seja específico, técnico e realista.
    """
    return chamar_ia(prompt)


def comparar_solucoes(demanda, categoria, solucao_admin, solucao_ia_complexa):
    """IA compara as duas soluções e gera uma solução final"""
    prompt = f"""
    Você é um especialista em acessibilidade corporativa. Compare as duas soluções abaixo 
    para a seguinte demanda e crie uma SOLUÇÃO FINAL OTIMIZADA.

    DEMANDA: "{demanda}"
    CATEGORIA: {categoria}

    --- SOLUÇÃO DO ADMIN (simples e prática) ---
    {solucao_admin}

    --- SOLUÇÃO IA COMPLEXA (detalhada e técnica) ---
    {solucao_ia_complexa}

    Agora, faça o seguinte:
    1. Liste os PRÓS e CONTRAS de cada solução
    2. Identifique RISCOS e PROBLEMAS POTENCIAIS de cada abordagem
    3. Crie uma SOLUÇÃO FINAL que combine o melhor de ambas
    4. Defina um status sugerido (PENDENTE, EM_ANDAMENTO ou RESOLVIDO)
    5. Dê uma mensagem que será mostrada ao usuário (linguagem simples e acolhedora)

    Responda no seguinte formato JSON:
    {{
        "pros_admin": ["vantagem1", "vantagem2"],
        "contras_admin": ["desvantagem1", "desvantagem2"],
        "pros_ia": ["vantagem1", "vantagem2"],
        "contras_ia": ["desvantagem1", "desvantagem2"],
        "riscos": ["risco1", "risco2"],
        "solucao_final": "texto da solução final combinada",
        "status_sugerido": "EM_ANDAMENTO",
        "mensagem_usuario": "Com base nessa demanda, vamos fazer isso, isso e isso..."
    }}
    """

    resposta = chamar_ia(prompt)

    # Tentar extrair JSON
    try:
        # Encontrar o JSON na resposta
        inicio = resposta.find('{')
        fim = resposta.rfind('}') + 1
        if inicio != -1 and fim != -1:
            json_str = resposta[inicio:fim]
            return json.loads(json_str)
    except:
        pass

    # Fallback
    return {
        "pros_admin": ["Solução prática e de rápida implementação"],
        "contras_admin": ["Pode não abordar causas profundas"],
        "pros_ia": ["Solução completa e bem estruturada"],
        "contras_ia": ["Pode ser demorada ou cara"],
        "riscos": ["Necessário alinhamento entre equipes"],
        "solucao_final": f"Combinar abordagem prática do admin com visão técnica da IA.\n\nAdmin sugeriu: {solucao_admin[:200]}...\n\nIA sugeriu: {solucao_ia_complexa[:200]}...",
        "status_sugerido": "EM_ANDAMENTO",
        "mensagem_usuario": f"Recebemos sua demanda sobre {demanda[:100]}... Estamos analisando a melhor forma de atendê-lo."
    }


# ==================== FUNÇÕES DO BANCO ====================
def criar_tabelas():
    conn = get_db_connection()
    cursor = conn.cursor()

    # Criar tabela USUARIOS
    try:
        cursor.execute("SELECT 1 FROM USUARIOS")
    except:
        cursor.execute("""
                       CREATE TABLE USUARIOS
                       (
                           ID            INTEGER      NOT NULL PRIMARY KEY,
                           NOME          VARCHAR(100) NOT NULL,
                           EMAIL         VARCHAR(100) NOT NULL UNIQUE,
                           SENHA         VARCHAR(64)  NOT NULL,
                           TIPO          VARCHAR(20),
                           DEFICIENCIA   VARCHAR(100),
                           DATA_CADASTRO TIMESTAMP
                       )
                       """)
        conn.commit()
        print("Tabela USUARIOS criada")

    # Criar tabela DEMANDAS com novas colunas
    try:
        cursor.execute("SELECT 1 FROM DEMANDAS")
    except:
        cursor.execute("""
                       CREATE TABLE DEMANDAS
                       (
                           ID                  INTEGER       NOT NULL PRIMARY KEY,
                           USUARIO_ID          INTEGER       NOT NULL,
                           TITULO              VARCHAR(200)  NOT NULL,
                           DESCRICAO           VARCHAR(2000) NOT NULL,
                           LOCALIZACAO         VARCHAR(200),
                           CATEGORIA           VARCHAR(50),
                           STATUS              VARCHAR(20),
                           SOLUCAO_ADMIN       VARCHAR(2000),
                           AREA_RESPONSAVEL    VARCHAR(100),
                           PRAZO_ESTIMADO      VARCHAR(100),
                           DATA_CRIACAO        TIMESTAMP,
                           SOLUCAO_IA_COMPLEXA BLOB SUB_TYPE TEXT,
                           SOLUCAO_COMPARADA   BLOB SUB_TYPE TEXT,
                           MENSAGEM_USUARIO    VARCHAR(2000),
                           COMPARACAO_JSON     BLOB SUB_TYPE TEXT
                       )
                       """)
        conn.commit()
        print("Tabela DEMANDAS criada com novas colunas")
    else:
        # Verificar e adicionar colunas faltantes
        colunas_existentes = []
        try:
            cursor.execute("SELECT * FROM DEMANDAS WHERE 1=0")
            for col in cursor.description:
                colunas_existentes.append(col[0])
        except:
            pass

        novas_colunas = {
            "SOLUCAO_IA_COMPLEXA": "ALTER TABLE DEMANDAS ADD SOLUCAO_IA_COMPLEXA BLOB SUB_TYPE TEXT",
            "SOLUCAO_COMPARADA": "ALTER TABLE DEMANDAS ADD SOLUCAO_COMPARADA BLOB SUB_TYPE TEXT",
            "MENSAGEM_USUARIO": "ALTER TABLE DEMANDAS ADD MENSAGEM_USUARIO VARCHAR(2000)",
            "COMPARACAO_JSON": "ALTER TABLE DEMANDAS ADD COMPARACAO_JSON BLOB SUB_TYPE TEXT"
        }

        for col, sql in novas_colunas.items():
            if col not in colunas_existentes:
                try:
                    cursor.execute(sql)
                    conn.commit()
                    print(f"Coluna {col} adicionada")
                except Exception as e:
                    print(f"Erro ao adicionar {col}: {e}")

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


# Inserir contas fixas se não existirem
def inserir_contas_fixas():
    conn = get_db_connection()
    cursor = conn.cursor()

    # Admin
    cursor.execute("SELECT COUNT(*) FROM USUARIOS WHERE ID = ?", (ADMIN_FIXO['id'],))
    if cursor.fetchone()[0] == 0:
        cursor.execute("""
                       INSERT INTO USUARIOS (ID, NOME, EMAIL, SENHA, TIPO, DATA_CADASTRO)
                       VALUES (?, ?, ?, ?, ?, ?)
                       """, (ADMIN_FIXO['id'], ADMIN_FIXO['nome'], ADMIN_FIXO['email'],
                             ADMIN_FIXO['senha_hash'], ADMIN_FIXO['tipo'], datetime.now()))
        print("Admin inserido")

    # Sede
    cursor.execute("SELECT COUNT(*) FROM USUARIOS WHERE ID = ?", (SEDE_FIXA['id'],))
    if cursor.fetchone()[0] == 0:
        cursor.execute("""
                       INSERT INTO USUARIOS (ID, NOME, EMAIL, SENHA, TIPO, DATA_CADASTRO)
                       VALUES (?, ?, ?, ?, ?, ?)
                       """, (SEDE_FIXA['id'], SEDE_FIXA['nome'], SEDE_FIXA['email'],
                             SEDE_FIXA['senha_hash'], SEDE_FIXA['tipo'], datetime.now()))
        print("Sede inserida")

    conn.commit()
    conn.close()


# Criar tabelas e inserir contas fixas ao iniciar
try:
    criar_tabelas()
    inserir_contas_fixas()
    print("Banco de dados verificado")
except Exception as e:
    print(f"Atenção ao verificar banco: {e}")


# ==================== ROTAS ====================
@app.route('/')
def index():
    if 'usuario_id' in session:
        if session['tipo'] == 'admin':
            return redirect(url_for('dashboard_admin'))
        elif session['tipo'] == 'sede':
            return redirect(url_for('dashboard_sede'))
        return redirect(url_for('dashboard_user'))
    return redirect(url_for('login'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        senha = request.form['senha']
        senha_hash = hashlib.sha256(senha.encode()).hexdigest()

        # Verificar contas fixas
        if email == ADMIN_FIXO['email'] and senha_hash == ADMIN_FIXO['senha_hash']:
            session['usuario_id'] = ADMIN_FIXO['id']
            session['usuario_nome'] = ADMIN_FIXO['nome']
            session['tipo'] = 'admin'
            return redirect(url_for('dashboard_admin'))

        if email == SEDE_FIXA['email'] and senha_hash == SEDE_FIXA['senha_hash']:
            session['usuario_id'] = SEDE_FIXA['id']
            session['usuario_nome'] = SEDE_FIXA['nome']
            session['tipo'] = 'sede'
            return redirect(url_for('dashboard_sede'))

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


# ==================== ROTAS ADMIN ====================
@app.route('/admin/criar_usuario', methods=['POST'])
def admin_criar_usuario():
    if 'usuario_id' not in session or session['tipo'] != 'admin':
        return redirect(url_for('login'))

    nome = request.form['nome']
    email = request.form['email']
    senha = request.form['senha']
    deficiencia = request.form.get('deficiencia', '')

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM USUARIOS WHERE EMAIL = ?", (email,))
        if cursor.fetchone()[0] > 0:
            conn.close()
            return redirect(url_for('admin_usuarios', erro="E-mail já cadastrado"))

        criar_usuario(nome, email, senha, deficiencia)
        conn.close()
        return redirect(url_for('admin_usuarios', sucesso=f"Usuário {nome} criado com sucesso!"))
    except Exception as e:
        return redirect(url_for('admin_usuarios', erro=f"Erro ao criar usuário: {e}"))


@app.route('/admin/usuarios')
def admin_usuarios():
    if 'usuario_id' not in session or session['tipo'] != 'admin':
        return redirect(url_for('login'))

    erro = request.args.get('erro')
    sucesso = request.args.get('sucesso')

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
                       SELECT ID, NOME, EMAIL, TIPO, DEFICIENCIA, DATA_CADASTRO
                       FROM USUARIOS
                       WHERE TIPO = 'user'
                       ORDER BY DATA_CADASTRO DESC
                       """)
        usuarios = cursor.fetchall()
        conn.close()
    except Exception as e:
        usuarios = []
        print(f"Erro: {e}")

    return render_template('admin_usuarios.html', usuarios=usuarios, erro=erro, sucesso=sucesso)


@app.route('/admin/deletar_usuario/<int:usuario_id>', methods=['POST'])
def admin_deletar_usuario(usuario_id):
    if 'usuario_id' not in session or session['tipo'] != 'admin':
        return jsonify({"erro": "Não autorizado"}), 401

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM DEMANDAS WHERE USUARIO_ID = ?", (usuario_id,))
        tem_demandas = cursor.fetchone()[0] > 0

        if tem_demandas:
            return jsonify({"erro": "Usuário possui demandas. Exclua as demandas primeiro ou altere o status."}), 400

        cursor.execute("DELETE FROM USUARIOS WHERE ID = ? AND TIPO = 'user'", (usuario_id,))
        conn.commit()
        conn.close()
        return jsonify({"sucesso": True})
    except Exception as e:
        return jsonify({"erro": str(e)}), 500


# ==================== ROTAS SEDE ====================
@app.route('/dashboard/sede')
def dashboard_sede():
    if 'usuario_id' not in session or session['tipo'] != 'sede':
        return redirect(url_for('login'))

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
                       SELECT d.ID,
                              u.NOME,
                              d.TITULO,
                              d.CATEGORIA,
                              d.STATUS,
                              d.DATA_CRIACAO,
                              d.SOLUCAO_ADMIN,
                              d.SOLUCAO_IA_COMPLEXA,
                              d.SOLUCAO_COMPARADA
                       FROM DEMANDAS d
                                JOIN USUARIOS u ON d.USUARIO_ID = u.ID
                       ORDER BY d.DATA_CRIACAO DESC
                       """)
        demandas = cursor.fetchall()

        cursor.execute("SELECT COUNT(*) FROM DEMANDAS")
        total = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM DEMANDAS WHERE STATUS = 'PENDENTE'")
        pendentes = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM DEMANDAS WHERE SOLUCAO_COMPARADA IS NOT NULL")
        com_solucao_final = cursor.fetchone()[0]

        conn.close()
    except Exception as e:
        demandas = []
        total = pendentes = com_solucao_final = 0
        print(f"Erro: {e}")

    return render_template('dashboard_sede.html',
                           demandas=demandas,
                           total=total,
                           pendentes=pendentes,
                           com_solucao_final=com_solucao_final,
                           nome=session['usuario_nome'])


@app.route('/sede/demanda/<int:demanda_id>')
def sede_ver_demanda(demanda_id):
    if 'usuario_id' not in session or session['tipo'] != 'sede':
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

    return render_template('sede_ver_demanda.html', demanda=demanda)


@app.route('/sede/comparar_solucoes', methods=['POST'])
def sede_comparar_solucoes():
    if 'usuario_id' not in session or session['tipo'] != 'sede':
        return jsonify({"erro": "Não autorizado"}), 401

    data = request.get_json()
    demanda_id = data.get('demanda_id')

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT DESCRICAO, CATEGORIA, SOLUCAO_ADMIN, SOLUCAO_IA_COMPLEXA FROM DEMANDAS WHERE ID = ?",
                   (demanda_id,))
    row = cursor.fetchone()

    if not row:
        conn.close()
        return jsonify({"erro": "Demanda não encontrada"}), 404

    descricao, categoria, solucao_admin, solucao_ia_complexa = row

    # Chamar IA para comparar
    comparacao = comparar_solucoes(descricao, categoria, solucao_admin or "", solucao_ia_complexa or "")

    # Salvar no banco
    cursor.execute("""
                   UPDATE DEMANDAS
                   SET SOLUCAO_COMPARADA = ?,
                       MENSAGEM_USUARIO  = ?,
                       COMPARACAO_JSON   = ?,
                       STATUS            = ?
                   WHERE ID = ?
                   """, (comparacao.get('solucao_final', ''),
                         comparacao.get('mensagem_usuario', ''),
                         json.dumps(comparacao),
                         comparacao.get('status_sugerido', 'EM_ANDAMENTO'),
                         demanda_id))
    conn.commit()
    conn.close()

    return jsonify(comparacao)


@app.route('/sede/atualizar_status_final', methods=['POST'])
def sede_atualizar_status_final():
    if 'usuario_id' not in session or session['tipo'] != 'sede':
        return jsonify({"erro": "Não autorizado"}), 401

    data = request.get_json()
    demanda_id = data.get('demanda_id')
    novo_status = data.get('status')
    mensagem_usuario = data.get('mensagem_usuario')

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
                   UPDATE DEMANDAS
                   SET STATUS           = ?,
                       MENSAGEM_USUARIO = ?
                   WHERE ID = ?
                   """, (novo_status, mensagem_usuario, demanda_id))
    conn.commit()
    conn.close()

    return jsonify({"sucesso": True})


# ==================== ROTAS ADMIN (Dashboard e Gestão) ====================
@app.route('/dashboard/user')
def dashboard_user():
    if 'usuario_id' not in session or session['tipo'] != 'user':
        return redirect(url_for('login'))

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
                       SELECT ID,
                              TITULO,
                              CATEGORIA,
                              STATUS,
                              DATA_CRIACAO,
                              MENSAGEM_USUARIO
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

        # Gerar ambas as soluções
        solucao_simples = sugerir_solucao_simples(descricao, categoria)
        solucao_complexa = sugerir_solucao_complexa(descricao, categoria)

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT COALESCE(MAX(ID), 0) + 1 FROM DEMANDAS")
        novo_id = cursor.fetchone()[0]

        cursor.execute("""
                       INSERT INTO DEMANDAS (ID, USUARIO_ID, TITULO, DESCRICAO, LOCALIZACAO, CATEGORIA,
                                             STATUS, SOLUCAO_ADMIN, AREA_RESPONSAVEL, PRAZO_ESTIMADO,
                                             DATA_CRIACAO, SOLUCAO_IA_COMPLEXA, MENSAGEM_USUARIO)
                       VALUES (?, ?, ?, ?, ?, ?, 'PENDENTE', ?, ?, ?, ?, ?, ?)
                       """, (novo_id, session['usuario_id'], titulo, descricao, localizacao, categoria,
                             solucao_simples['solucao'], solucao_simples['area'], solucao_simples['prazo'],
                             datetime.now(), solucao_complexa,
                             "Recebemos sua demanda. Em breve, a sede analisará e dará um retorno."))

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
                   SELECT d.ID,
                          d.TITULO,
                          d.DESCRICAO,
                          d.LOCALIZACAO,
                          d.CATEGORIA,
                          d.STATUS,
                          d.SOLUCAO_ADMIN,
                          d.AREA_RESPONSAVEL,
                          d.PRAZO_ESTIMADO,
                          d.DATA_CRIACAO,
                          u.NOME,
                          u.EMAIL,
                          u.DEFICIENCIA
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
    cursor.execute("UPDATE DEMANDAS SET SOLUCAO_ADMIN = ? WHERE ID = ?", (nova_solucao, demanda_id))
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


@app.route('/api/libras')
def api_libras():
    return render_template('libras.html')


if __name__ == '__main__':
    app.run(debug=True, host='127.0.0.1', port=5000)