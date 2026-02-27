import os
import requests
import pandas as pd
import numpy as np
from flask import Flask, render_template, request, jsonify, redirect, session
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

# ===========================
# CONFIGURAÇÃO DO APP
# ===========================
app = Flask(__name__)
API_KEY = os.getenv("ANTHROPIC_API_KEY")
client = anthropic.Anthropic(api_key=API_KEY)
UPLOAD_FOLDER = os.path.join(os.getcwd(), "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

usuarios = {}  # Usuários em memória (para teste simples)

# ===========================
# FUNÇÃO EVA (IA)
# ===========================
def perguntar_eva(mensagem):
    if "seu nome" in mensagem.lower():
        return "Eu sou Eva, uma inteligência artificial criada por Luan."

    if not ANTHROPIC_API_KEY:
        return "IA não configurada. Sem chave da API."

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
        response = requests.post(url, headers=headers, json=data, timeout=15)
        resposta = response.json()
        if "content" in resposta and len(resposta["content"]) > 0:
            return resposta["content"][0].get("text", "Sem resposta da IA.")
        return "Sem resposta da IA."
    except Exception as e:
        print("Erro na API:", e)
        return "Erro ao conectar com a IA."

# ===========================
# FUNÇÕES ESTATÍSTICAS SEM SCIPY
# ===========================
def zscore(a):
    a = np.array(a)
    return (a - a.mean()) / a.std(ddof=1)

def ttest_ind(a, b):
    a, b = np.array(a), np.array(b)
    var_a = a.var(ddof=1)
    var_b = b.var(ddof=1)
    t_stat = (a.mean() - b.mean()) / np.sqrt(var_a/len(a) + var_b/len(b))
    # p-valor aproximado usando distribuição normal
    p_val = 2 * (1 - 0.5 * (1 + np.math.erf(np.abs(t_stat)/np.sqrt(2))))
    return t_stat, p_val

# ===========================
# ANÁLISE DE DADOS
# ===========================
def interpretar_dados(df):
    comentarios = []
    for coluna in df.select_dtypes(include=np.number).columns:
        media = df[coluna].mean()
        desvio = df[coluna].std()
        comentarios.append(f"Coluna {coluna}: média {media:.2f}, desvio padrão {desvio:.2f}.")
        if desvio > media * 0.5:
            comentarios.append(f"A coluna {coluna} apresenta alta variabilidade.")
        # Outliers via Z-score
        zs = zscore(df[coluna].dropna())
        outliers = np.sum(np.abs(zs) > 3)
        if outliers > 0:
            comentarios.append(f"Foram detectados {outliers} possíveis outliers na coluna {coluna}.")
    if len(df.select_dtypes(include=np.number).columns) > 1:
        corr = df.corr().to_string()
        comentarios.append("\nMatriz de correlação:\n" + corr)
    return "\n".join(comentarios)

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

def comparar_csv(caminho1, caminho2):
    df1 = pd.read_csv(caminho1)
    df2 = pd.read_csv(caminho2)
    colunas_comuns = list(set(df1.columns) & set(df2.columns))
    resultado = []
    for coluna in colunas_comuns:
        if df1[coluna].dtype in [np.float64, np.int64]:
            media1 = df1[coluna].mean()
            media2 = df2[coluna].mean()
            t_stat, p_val = ttest_ind(df1[coluna].dropna(), df2[coluna].dropna())
            resultado.append(f"""
Coluna: {coluna}
Média Arquivo 1: {media1:.2f}
Média Arquivo 2: {media2:.2f}
Teste t: t = {t_stat:.2f}
p-valor = {p_val:.4f}
""")
            if p_val < 0.05:
                resultado.append("Diferença estatisticamente significativa (p < 0.05).")
            else:
                resultado.append("Não há diferença estatisticamente significativa.")
    return "\n".join(resultado)

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

# ===========================
# EXECUÇÃO
# ===========================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
