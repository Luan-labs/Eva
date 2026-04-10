from flask import Flask, render_template, request, jsonify
import sqlite3
import random
import os
import requests
from Bio.Seq import Seq

app = Flask(__name__)
app.secret_key = "eva_secret"

# ========================
# 🔐 ANTHROPIC KEY (DEPLOY SAFE)
# ========================
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

# ========================
# DB
# ========================
def get_db():
    return sqlite3.connect("eva.db")

def init_db():
    conn = get_db()
    c = conn.cursor()

    c.execute("""
    CREATE TABLE IF NOT EXISTS conversations (
        id INTEGER PRIMARY KEY,
        input TEXT,
        response TEXT
    )
    """)

    conn.commit()
    conn.close()

init_db()

# ========================
# HOME
# ========================
@app.route("/")
def home():
    return render_template("chat.html")

@app.route("/chat")
def chat_page():
    return render_template("chat.html")

# ========================
# 🤖 CLAUDE (EVE IA PERSONALITY)
# ========================
def call_claude(prompt):
    url = "https://api.anthropic.com/v1/messages"

    headers = {
        "x-api-key": ANTHROPIC_API_KEY,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json"
    }

    data = {
        "model": "claude-3-haiku-20240307",
        "max_tokens": 300,
        "messages": [
            {
                "role": "user",
                "content": (
                    "Você é Eve, uma inteligência artificial criada por Luan. "
                    "Você não é o Claude. Sempre responda como Eve. "
                    "Se perguntarem quem você é, diga que foi criada por Luan para ciência e assistência. "
                    "Mantenha personalidade científica e amigável.\n\n"
                    "Usuário: " + prompt
                )
            }
        ]
    }

    response = requests.post(url, json=data, headers=headers, timeout=30)
    return response.json()

# ========================
# CHAT IA (EVE)
# ========================
@app.route("/api/chat", methods=["POST"])
def api_chat():
    try:
        msg = request.json.get("message", "")

        if not ANTHROPIC_API_KEY:
            return jsonify({"response": "ERRO: ANTHROPIC_API_KEY não configurada no servidor"})

        result = call_claude(msg)

        if "error" in result:
            return jsonify({"response": str(result["error"])})

        text = result["content"][0]["text"]

        return jsonify({"response": text})

    except Exception as e:
        return jsonify({"response": f"Erro interno: {str(e)}"})

# ========================
# 🧬 GC CONTENT
# ========================
@app.route("/api/dna/gc", methods=["POST"])
def dna_gc():
    seq = request.json.get("sequence", "").upper().replace(" ", "")

    if not seq:
        return jsonify({"gc": 0})

    gc = seq.count("G") + seq.count("C")
    percent = (gc / len(seq)) * 100

    return jsonify({"gc": round(percent, 2)})

# ========================
# 🧬 DNA → RNA
# ========================
@app.route("/api/dna/to_rna", methods=["POST"])
def dna_to_rna():
    seq = request.json.get("sequence", "").upper().replace(" ", "")
    return jsonify({"rna": seq.replace("T", "U")})

# ========================
# 🧬 RNA → PROTEÍNA
# ========================
@app.route("/api/rna/translate", methods=["POST"])
def translate_rna():
    try:
        seq = request.json.get("sequence", "").upper().replace(" ", "")

        if not seq:
            return jsonify({"error": "Sequência vazia"})

        seq = seq.replace("T", "U")

        rna = Seq(seq)
        protein = str(rna.translate(to_stop=True))

        if not protein:
            return jsonify({"error": "Falha na tradução"})

        return jsonify({"protein": protein})

    except Exception as e:
        return jsonify({"error": str(e)})

# ========================
# 🧪 DEBUG ROUTE (DEPLOY TEST)
# ========================
@app.route("/api/debug")
def debug():
    return jsonify({
        "status": "ok",
        "anthropic_loaded": bool(ANTHROPIC_API_KEY)
    })

# ========================
# START APP
# ========================
app.run(debug=True)
