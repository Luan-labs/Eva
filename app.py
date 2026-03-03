import os
import requests
import pandas as pd
import numpy as np
from flask import Flask, render_template, request, jsonify, redirect, session
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

# ===========================
# CONFIGURAÇÃO
# ===========================
app = Flask(__name__)

app.secret_key = os.getenv("SECRET_KEY")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

if not app.secret_key:
    raise ValueError("SECRET_KEY não configurada!")

if not ANTHROPIC_API_KEY:
    raise ValueError("ANTHROPIC_API_KEY não configurada!")

UPLOAD_FOLDER = os.path.join(os.getcwd(), "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

usuarios = {}

# ===========================
# IA EVA
# ===========================
def perguntar_eva(mensagem):

    url = "https://api.anthropic.com/v1/messages"

    headers = {
        "x-api-key": ANTHROPIC_API_KEY,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json"
    }

    data = {
        "model": "claude-3-haiku-20240307",
        "max_tokens": 300,
        "system": "Você é Eva, assistente analítica especializada em dados públicos e análise estatística.",
        "messages": [
            {
                "role": "user",
                "content": [{"type": "text", "text": mensagem}]
            }
        ]
    }

    try:
        response = requests.post(url, headers=headers, json=data, timeout=30)
        if response.status_code != 200:
            return f"Erro API ({response.status_code})"
        return response.json()["content"][0]["text"]
    except Exception as e:
        return f"Erro IA: {str(e)}"


# ===========================
# FUNÇÕES ESTATÍSTICAS
# ===========================
def zscore(a):
    a = np.array(a)
    return (a - a.mean()) / a.std(ddof=1)


def interpretar_dados(df):
    comentarios = []

    for coluna in df.select_dtypes(include=np.number).columns:
        media = df[coluna].mean()
        desvio = df[coluna].std()

        comentarios.append(f"Coluna {coluna}: média {media:.2f}, desvio {desvio:.2f}.")

        if desvio > media * 0.5:
            comentarios.append(f"Alta variabilidade detectada em {coluna}.")

        zs = zscore(df[coluna].dropna())
        outliers = np.sum(np.abs(zs) > 3)

        if outliers > 0:
            comentarios.append(f"{outliers} possíveis outliers em {coluna}.")

    return "\n".join(comentarios)


# ===========================
# MÓDULO ANTICORRUPÇÃO
# ===========================
def detectar_concentracao(df):
    if "Fornecedor" not in df.columns or "Valor" not in df.columns:
        return 0, None

    df["Valor"] = pd.to_numeric(df["Valor"], errors="coerce")
    total = df["Valor"].sum()
    grupo = df.groupby("Fornecedor")["Valor"].sum()

    maior_valor = grupo.max()
    maior_fornecedor = grupo.idxmax()

    percentual = (maior_valor / total) * 100
    return percentual, maior_fornecedor


def detectar_fracionamento(df):
    if "Valor" not in df.columns:
        return 0

    valores_repetidos = df["Valor"].value_counts()
    suspeitos = valores_repetidos[valores_repetidos > 3]

    return len(suspeitos)


def detectar_excesso_dispensa(df):
    if "Modalidade" not in df.columns:
        return 0

    total = len(df)
    dispensas = df["Modalidade"].str.contains("Dispensa|Inexigibilidade", case=False, na=False).sum()
    return (dispensas / total) * 100


def calcular_indice_risco_corrupcao(df):

    score = 0
    motivos = []

    # Concentração
    percentual_conc, fornecedor = detectar_concentracao(df)
    if percentual_conc > 50:
        score += 30
        motivos.append(f"Alta concentração: {percentual_conc:.1f}% com {fornecedor}.")

    # Fracionamento
    fracionamento = detectar_fracionamento(df)
    if fracionamento > 0:
        score += 20
        motivos.append("Possível fracionamento detectado.")

    # Dispensa excessiva
    percentual_dispensa = detectar_excesso_dispensa(df)
    if percentual_dispensa > 40:
        score += 25
        motivos.append(f"Alta taxa de dispensa/inexigibilidade: {percentual_dispensa:.1f}%.")

    # Outliers
    if "Valor" in df.columns:
        df["Valor"] = pd.to_numeric(df["Valor"], errors="coerce")
        zs = zscore(df["Valor"].dropna())
        outliers = np.sum(np.abs(zs) > 3)

        if outliers > 0:
            score += 15
            motivos.append(f"{outliers} valores atípicos detectados.")

    score = min(score, 100)

    if score <= 30:
        classificacao = "Baixo Risco"
    elif score <= 60:
        classificacao = "Risco Moderado"
    else:
        classificacao = "Alto Risco"

    return score, classificacao, motivos


# ===========================
# CSV
# ===========================
def analisar_csv(caminho):
    df = pd.read_csv(caminho)
    session["ultimo_csv"] = caminho

    resumo = df.describe().to_string()
    comentario = interpretar_dados(df)

    score, classificacao, motivos = calcular_indice_risco_corrupcao(df)

    relatorio_risco = f"""
===== ANÁLISE DE RISCO ANTICORRUPÇÃO =====

Índice Composto de Risco: {score}/100
Classificação: {classificacao}

Fatores Identificados:
{chr(10).join(motivos)}

Observação:
Esta análise identifica padrões estatísticos.
Não constitui acusação formal.
Recomenda-se auditoria técnica complementar.
"""

    return f"""
Arquivo analisado com sucesso.

Resumo estatístico:
{resumo}

Análise estatística:
{comentario}

{relatorio_risco}
"""


# ===========================
# ROTAS
# ===========================
@app.route("/")
def home():
    if "usuario" in session:
        return render_template("chat.html")
    return redirect("/login")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        if username in usuarios and check_password_hash(usuarios[username], password):
            session["usuario"] = username
            return redirect("/")
        else:
            return "Usuário ou senha inválidos."

    return render_template("login.html")


@app.route("/register", methods=["POST"])
def register():
    username = request.form["username"]
    password = request.form["password"]

    if username in usuarios:
        return "Usuário já existe."

    usuarios[username] = generate_password_hash(password)
    session["usuario"] = username
    return redirect("/")


@app.route("/chat", methods=["POST"])
def chat():
    mensagem = request.json["message"]
    resposta = perguntar_eva(mensagem)
    return jsonify({"response": resposta})


@app.route("/upload_csv", methods=["POST"])
def upload_csv():

    if "file" not in request.files:
        return jsonify({"response": "Nenhum arquivo enviado."})

    file = request.files["file"]
    filename = secure_filename(file.filename)
    caminho = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    file.save(caminho)

    resultado = analisar_csv(caminho)

    return jsonify({"response": resultado})


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")


# ===========================
# EXECUÇÃO
# ===========================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
