import os
import requests
import pandas as pd
import numpy as np
from flask import Flask, render_template, request, jsonify, redirect, session
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = "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"

ANTHROPIC_API_KEY = "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"

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

usuarios = {}

# =====================================================
# FUNÇÃO EVA (IA CONVERSACIONAL)
# =====================================================

def perguntar_eva(mensagem):

    if "seu nome" in mensagem.lower():
        return "Eu sou Eva, uma inteligência artificial criada por Luan."

    url = "https://api.anthropic.com/v1/messages"

    headers = {
        "x-api-key": ANTHROPIC_API_KEY,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json"
    }

    data = {
        "model": "claude-3-haiku-20240307",
        "max_tokens": 300,
        "system": """
Você é Eva, uma IA analista científica criada por Luan.
Nunca diga que é Claude ou que foi criada pela Anthropic.
Seja técnica, analítica e clara.
""",
        "messages": [
            {"role": "user", "content": mensagem}
        ]
    }

    try:
        response = requests.post(url, headers=headers, json=data)
        resposta = response.json()
        return resposta["content"][0]["text"]
    except:
        return "Erro ao conectar com a IA."

# =====================================================
# INTERPRETAÇÃO AUTOMÁTICA
# =====================================================

def interpretar_dados(df):

    comentarios = []

    for coluna in df.select_dtypes(include=np.number).columns:

        media = df[coluna].mean()
        desvio = df[coluna].std()

        comentarios.append(
            f"Coluna {coluna}: média {media:.2f}, desvio padrão {desvio:.2f}."
        )

        # Outliers usando Z-score manual
        z_scores = (df[coluna] - media) / desvio
        outliers = np.sum(np.abs(z_scores) > 3)

        if outliers > 0:
            comentarios.append(
                f"Foram detectados {outliers} possíveis outliers na coluna {coluna}."
            )

    # Correlação
    colunas_numericas = df.select_dtypes(include=np.number)
    if len(colunas_numericas.columns) > 1:
        corr = colunas_numericas.corr().to_string()
        comentarios.append("\nMatriz de correlação:\n" + corr)

    return "\n".join(comentarios)

# =====================================================
# ANÁLISE SIMPLES
# =====================================================

def analisar_csv(caminho):

    df = pd.read_csv(caminho)
    session["ultimo_csv"] = caminho

    resumo = df.describe().to_string()
    comentario = interpretar_dados(df)

    return f"""
Arquivo analisado com sucesso.

Resumo estatístico:
{resumo}

Análise detalhada:
{comentario}
"""

# =====================================================
# COMPARAÇÃO ENTRE ARQUIVOS
# =====================================================

def comparar_csv(caminho1, caminho2):

    df1 = pd.read_csv(caminho1)
    df2 = pd.read_csv(caminho2)

    colunas_comuns = list(set(df1.columns) & set(df2.columns))
    resultado = []

    for coluna in colunas_comuns:

        if df1[coluna].dtype in [np.float64, np.int64]:

            x1 = df1[coluna].dropna()
            x2 = df2[coluna].dropna()

            media1 = x1.mean()
            media2 = x2.mean()

            var1 = x1.var(ddof=1)
            var2 = x2.var(ddof=1)

            n1 = len(x1)
            n2 = len(x2)

            # Teste t manual (Welch)
            t_stat = (media1 - media2) / np.sqrt((var1/n1) + (var2/n2))

            resultado.append(f"""
Coluna: {coluna}
Média Arquivo 1: {media1:.2f}
Média Arquivo 2: {media2:.2f}
t calculado: {t_stat:.2f}
""")

    return "\n".join(resultado)

# =====================================================
# ROTAS
# =====================================================

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

    if "ultimo_csv" in session:
        anterior = session["ultimo_csv"]
        comparacao = comparar_csv(anterior, caminho)
        session["ultimo_csv"] = caminho

        return jsonify({
            "response": f"""
Novo arquivo recebido.

Comparação com arquivo anterior:
{comparacao}
"""
        })

    else:
        resultado = analisar_csv(caminho)
        return jsonify({"response": resultado})

@app.route("/logout")
def logout():
    session.pop("usuario", None)
    session.pop("ultimo_csv", None)
    return redirect("/login")

# =====================================================
# EXECUÇÃO
# =====================================================

if __name__ == "__main__":
    app.run(debug=True)