import csv
import os
from flask import Flask, render_template, request, redirect, send_from_directory, session, url_for

app = Flask(__name__, template_folder='.', static_folder='static', static_url_path='/static')
app.secret_key = os.environ.get("SECRET_KEY", "chave-secreta-trocar")

# 🔐 Usuário e senha definidos via variáveis de ambiente (mantidos)
ADMIN_USER = os.environ.get("ADMIN_USER", "admin")
ADMIN_PASS = os.environ.get("ADMIN_PASS", "fcee2025")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.environ.get("DATA_DIR", os.getcwd())
os.makedirs(DATA_DIR, exist_ok=True)

DEFAULT_CSV = os.path.join(BASE_DIR, "dados.csv")
DEFAULT_DEMOGRAFIA = os.path.join(BASE_DIR, "demografia.csv")

CSV_FILE = os.path.join(DATA_DIR, "dados.csv")
DEMO_FILE = os.path.join(DATA_DIR, "demografia.csv")

# 🧮 Campos de quantidade específicos do CERTA
QUANT_FIELDS = [
    ("quantidade_oficinas", "Qt Oficinas"),
    ("quantidade_ta", "Qt Recursos de TA"),
    ("quantidade_recursos_pedagogicos", "Qt Recursos Pedagógicos"),
    ("quantidade_open_day", "Qt Open Day"),
]
QUANT_KEYS = [name for name, _ in QUANT_FIELDS]


# -------- CORS PARA PERMITIR ACESSO DO GITHUB PAGES -------- #
@app.after_request
def add_cors_headers(response):
    """
    Garante que qualquer resposta (incluindo /dados.csv, /demografia.csv e /sc_municipios.geojson)
    possa ser consumida via navegador a partir de outro domínio (ex: GitHub Pages).
    """
    response.headers.setdefault("Access-Control-Allow-Origin", "*")
    response.headers.setdefault("Access-Control-Allow-Methods", "GET, OPTIONS")
    response.headers.setdefault("Access-Control-Allow-Headers", "Content-Type")
    return response


# -------- Funções utilitárias -------- #
def to_non_negative_int(value, default=0):
    try:
        return max(int(str(value).strip() or default), 0)
    except (TypeError, ValueError):
        return default


def ensure_seed_file(target_path, default_source):
    if os.path.exists(target_path):
        return
    if default_source and os.path.exists(default_source):
        with open(default_source, 'rb') as src, open(target_path, 'wb') as dst:
            dst.write(src.read())


def normalize_numeric_field(value):
    return str(to_non_negative_int(value, 0))


def normalize_tipo(valor):
    """
    Para o CERTA, o tipo é categórico:
    - Todos
    - Oficinas
    - Recursos de TA
    - Open Day
    (mantemos o 'Todos' como no painel original)
    """
    tipo = (valor or "").strip()
    if tipo.lower() == "ambos":
        return "Todos"
    return tipo


def load_dados():
    """
    Carrega as instituições do CERTA a partir do CSV.
    Mantém:
      - municipio, regiao, nome, tipo, endereco, telefone, email
    E usa os novos campos de quantidade:
      - quantidade_oficinas
      - quantidade_ta
      - quantidade_recursos_pedagogicos
      - quantidade_open_day
    """
    ensure_seed_file(CSV_FILE, DEFAULT_CSV)
    instituicoes = {}
    todos_municipios = set()
    municipios_totais = {}
    municipio_regiao = {}

    def safe_str(row, key):
        return (row.get(key) or "").strip()

    if os.path.exists(CSV_FILE):
        with open(CSV_FILE, newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                municipio = safe_str(row, "municipio")
                if not municipio:
                    continue
                todos_municipios.add(municipio)

                inst_nome = safe_str(row, "nome")
                if inst_nome:
                    regiao = safe_str(row, "regiao")
                    if regiao:
                        municipio_regiao[municipio] = regiao

                    # Lê todas as quantidades do CERTA
                    quantidades = {}
                    for q_key in QUANT_KEYS:
                        quantidades[q_key] = to_non_negative_int(row.get(q_key, 0), 0)

                    inst = {
                        "nome": inst_nome,
                        "regiao": regiao,
                        "tipo": normalize_tipo(safe_str(row, "tipo")),
                        "endereco": safe_str(row, "endereco"),
                        "telefone": safe_str(row, "telefone"),
                        "email": safe_str(row, "email"),
                    }
                    # adiciona campos de quantidade normalizados (como string)
                    for q_key, value in quantidades.items():
                        inst[q_key] = normalize_numeric_field(value)

                    if municipio not in instituicoes:
                        instituicoes[municipio] = []
                    instituicoes[municipio].append(inst)

                    total_muni = sum(quantidades.values())
                    municipios_totais[municipio] = municipios_totais.get(municipio, 0) + total_muni

    # Status por município: se recebeu qualquer capacitação/recurso ou não
    municipiosStatus = {}
    for municipio in todos_municipios:
        insts = instituicoes.get(municipio, [])
        total_muni = 0
        for inst in insts:
            for q_key in QUANT_KEYS:
                total_muni += to_non_negative_int(inst.get(q_key, 0), 0)

        if total_muni > 0:
            status = "Com capacitações/recursos"
        else:
            status = "Nenhum"
        municipiosStatus[municipio] = status

    return municipiosStatus, instituicoes, municipios_totais, municipio_regiao


def load_demografia_rows():
    """
    Mantém a estrutura demográfica:
    tipo_deficiencia, faixa_etaria, quantidade
    Agora, quantidade = número de capacitações/recursos vinculados àquela deficiência/faixa.
    """
    ensure_seed_file(DEMO_FILE, DEFAULT_DEMOGRAFIA)
    registros = []
    if os.path.exists(DEMO_FILE):
        with open(DEMO_FILE, newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                tipo = (row.get("tipo_deficiencia") or "").strip()
                faixa = (row.get("faixa_etaria") or row.get("faixa") or "").strip()
                quantidade = to_non_negative_int(row.get("quantidade", 0), 0)

                if not tipo or not faixa:
                    continue

                registros.append({
                    "tipo_deficiencia": tipo,
                    "faixa_etaria": faixa,
                    "quantidade": quantidade
                })

    return registros


def montar_grade_demografia(registros, tipos_padrao, faixas_padrao):
    """
    Mantido para a tela Admin: grade de edição por tipo x faixa.
    """
    grade = {tipo: {faixa: 0 for faixa in faixas_padrao} for tipo in tipos_padrao}

    for registro in registros:
        tipo = (registro.get("tipo_deficiencia") or "").strip()
        faixa = (registro.get("faixa_etaria") or "").strip()
        if tipo in grade and faixa in grade[tipo]:
            grade[tipo][faixa] += to_non_negative_int(registro.get("quantidade", 0), 0)

    return grade


def preparar_demografia_por_deficiencia(registros):
    """
    Gera estrutura de demografia por tipo de deficiência x faixa etária.
    Usado para fins analíticos; o front lê diretamente o CSV demografia.csv.
    """
    faixas_padrao = ["0-12", "13-17", "18-59", "60+"]
    tipos = sorted({r["tipo_deficiencia"] for r in registros})
    estrutura = {tipo: {faixa: 0 for faixa in faixas_padrao} for tipo in tipos}

    total = 0
    for registro in registros:
        tipo = registro["tipo_deficiencia"]
        faixa = registro["faixa_etaria"]
        if faixa not in faixas_padrao:
            continue
        quantidade = to_non_negative_int(registro["quantidade"], 0)
        estrutura[tipo][faixa] = estrutura[tipo].get(faixa, 0) + quantidade
        total += quantidade

    return {
        "faixas": faixas_padrao,
        "tipos": tipos,
        "data": estrutura,
        "total": total
    }


def resumir_instituicoes(instituicoes):
    """
    Resume quantidades do CERTA:
      - Totais por tipo de ação (oficinas, TA, recursos pedagógicos, open day)
      - Totais por região (soma de todas as ações)
    """
    totais_por_campo = {q_key: 0 for q_key in QUANT_KEYS}
    regioes = {}

    for insts in instituicoes.values():
        for inst in insts:
            regiao = (inst.get("regiao") or "").strip()
            total_inst = 0
            for q_key in QUANT_KEYS:
                val = to_non_negative_int(inst.get(q_key, 0), 0)
                totais_por_campo[q_key] += val
                total_inst += val

            if not regiao or regiao.lower() in {"não informada", "nao informada", "não informado", "nao informado"}:
                continue

            regioes[regiao] = regioes.get(regiao, 0) + total_inst

    total_geral = sum(totais_por_campo.values())

    # Estrutura amigável para o front
    totais = {
        "oficinas": totais_por_campo.get("quantidade_oficinas", 0),
        "ta": totais_por_campo.get("quantidade_ta", 0),
        "recursos_pedagogicos": totais_por_campo.get("quantidade_recursos_pedagogicos", 0),
        "open_day": totais_por_campo.get("quantidade_open_day", 0),
        "total_geral": total_geral,
    }

    return {"totais": totais, "regioes": regioes}


def resumir_por_municipio(instituicoes):
    """
    Mantém um resumo por município (ainda não exibido no front, mas pronto para uso futuro).
    """
    resumo = {}
    for municipio, insts in instituicoes.items():
        dados = {
            "regiao": "",
            "instituicoes": len(insts),
        }
        for q_key in QUANT_KEYS:
            dados[q_key] = 0

        for inst in insts:
            dados["regiao"] = inst.get("regiao") or dados["regiao"]
            for q_key in QUANT_KEYS:
                dados[q_key] += to_non_negative_int(inst.get(q_key, 0), 0)

        resumo[municipio] = dados

    return resumo


def save_demografia(linhas):
    with open(DEMO_FILE, 'w', newline='', encoding='utf-8') as f:
        fieldnames = ["tipo_deficiencia", "faixa_etaria", "quantidade"]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for linha in linhas:
            writer.writerow({
                "tipo_deficiencia": linha.get("tipo_deficiencia", ""),
                "faixa_etaria": linha.get("faixa_etaria", ""),
                "quantidade": normalize_numeric_field(linha.get("quantidade", 0))
            })


def save_instituicoes(instituicoes):
    with open(CSV_FILE, 'w', newline='', encoding='utf-8') as f:
        fieldnames = [
            "municipio", "regiao", "nome", "tipo", "endereco", "telefone", "email",
        ] + QUANT_KEYS
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for municipio, insts in instituicoes.items():
            for inst in insts:
                row = {"municipio": municipio}
                row.update({
                    "regiao": inst.get("regiao", ""),
                    "nome": inst.get("nome", ""),
                    "tipo": inst.get("tipo", ""),
                    "endereco": inst.get("endereco", ""),
                    "telefone": inst.get("telefone", ""),
                    "email": inst.get("email", ""),
                })
                for q_key in QUANT_KEYS:
                    row[q_key] = normalize_numeric_field(inst.get(q_key, 0))
                writer.writerow(row)


# -------- Rotas -------- #

@app.route('/')
def index():
    municipiosStatus, municipiosInstituicoes, municipios_totais, municipio_regiao = load_dados()
    demografia_registros = load_demografia_rows()
    instituicoes_resumo = resumir_instituicoes(municipiosInstituicoes)
    municipios_resumo = resumir_por_municipio(municipiosInstituicoes)
    return render_template(
        'index.html',
        municipiosStatus=municipiosStatus,
        municipiosInstituicoes=municipiosInstituicoes,
        municipiosTotais=municipios_totais,
        demografia_distribuicao=preparar_demografia_por_deficiencia(demografia_registros),
        instituicoes_resumo=instituicoes_resumo,
        municipios_resumo=municipios_resumo,
        municipio_regiao=municipio_regiao,
    )


# --- Tela de Login ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = request.form['username']
        password = request.form['password']

        if user == ADMIN_USER and password == ADMIN_PASS:
            session['logged_in'] = True
            return redirect(url_for('admin'))
        else:
            return render_template('login.html', error="Usuário ou senha incorretos.")

    return render_template('login.html')


# --- Logout ---
@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    return redirect(url_for('login'))


# --- Painel Administrativo ---
@app.route('/admin', methods=['GET', 'POST'])
def admin():
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    municipiosStatus, instituicoes, _, municipio_regiao = load_dados()
    demografia_registros = load_demografia_rows()

    regiao_opcoes = [
        "Grande Florianópolis", "Sul", "Norte", "Vale do Itajaí", "Serra", "Oeste"
    ]
    faixas_opcoes = ["0-12", "13-17", "18-59", "60+"]
    # Tipos possíveis no CERTA
    tipos_opcoes = ["Todos", "Oficinas", "Recursos de TA", "Open Day"]
    demografia_grade = montar_grade_demografia(demografia_registros, tipos_opcoes, faixas_opcoes)

    if request.method == 'POST':
        form_type = request.form.get("form_type")

        if form_type == "instituicoes":
            # exclusão
            deletes = request.form.getlist("delete")
            if deletes:
                new_instituicoes = {}
                for municipio, insts in instituicoes.items():
                    new_instituicoes[municipio] = []
                    for i, inst in enumerate(insts):
                        if f"{municipio}_{i}" not in deletes:
                            new_instituicoes[municipio].append(inst)
                instituicoes = new_instituicoes

            # edição
            for key in request.form:
                if key.startswith("nome_"):
                    parts = key.split("_")
                    municipio = parts[1]
                    idx = int(parts[2])
                    if municipio in instituicoes and idx < len(instituicoes[municipio]):
                        instituicoes[municipio][idx]["nome"] = request.form[key].strip()
                        regiao_informada = request.form.get(f"regiao_{municipio}_{idx}", "").strip()
                        instituicoes[municipio][idx]["regiao"] = regiao_informada or municipio_regiao.get(municipio, "")
                        instituicoes[municipio][idx]["tipo"] = normalize_tipo(request.form.get(f"tipo_{municipio}_{idx}", ""))
                        instituicoes[municipio][idx]["endereco"] = request.form.get(f"endereco_{municipio}_{idx}", "").strip()
                        instituicoes[municipio][idx]["telefone"] = request.form.get(f"telefone_{municipio}_{idx}", "").strip()
                        instituicoes[municipio][idx]["email"] = request.form.get(f"email_{municipio}_{idx}", "").strip()

                        # atualiza todos os campos de quantidade
                        for q_key in QUANT_KEYS:
                            field_name = f"{q_key}_{municipio}_{idx}"
                            instituicoes[municipio][idx][q_key] = normalize_numeric_field(
                                request.form.get(field_name, "")
                            )

            # adicionar nova instituição
            if request.form.get("add"):
                municipio = request.form.get("municipio", "").strip()
                if municipio:
                    regiao_informada = request.form.get("regiao", "").strip()
                    inst = {
                        "nome": request.form.get("nome", "").strip(),
                        "regiao": regiao_informada or municipio_regiao.get(municipio, ""),
                        "tipo": normalize_tipo(request.form.get("tipo", "")),
                        "endereco": request.form.get("endereco", "").strip(),
                        "telefone": request.form.get("telefone", "").strip(),
                        "email": request.form.get("email", "").strip(),
                    }
                    for q_key in QUANT_KEYS:
                        inst[q_key] = normalize_numeric_field(request.form.get(q_key, ""))

                    if municipio not in instituicoes:
                        instituicoes[municipio] = []
                    instituicoes[municipio].append(inst)

            save_instituicoes(instituicoes)

        if form_type == "demografia":
            linhas = []
            for tipo in tipos_opcoes:
                for faixa in faixas_opcoes:
                    quantidade = request.form.get(f"demografia[{tipo}][{faixa}]", "0")
                    linhas.append({
                        "tipo_deficiencia": tipo,
                        "faixa_etaria": faixa,
                        "quantidade": quantidade,
                    })

            save_demografia(linhas)

        return redirect(url_for('admin'))

    return render_template(
        "admin.html",
        instituicoes=instituicoes,
        demografia_registros=demografia_registros,
        demografia_grade=demografia_grade,
        regiao_opcoes=regiao_opcoes,
        faixas_opcoes=faixas_opcoes,
        tipos_opcoes=tipos_opcoes,
        instituicoes_resumo=resumir_instituicoes(instituicoes),
        municipio_regiao=municipio_regiao,
        municipios_lista=sorted(municipio_regiao.keys()),
    )


# --- Rotas para arquivos de dados --- #
@app.route('/dados.csv')
def dados_csv():
    ensure_seed_file(CSV_FILE, DEFAULT_CSV)
    return send_from_directory(DATA_DIR, os.path.basename(CSV_FILE))


@app.route('/demografia.csv')
def demografia_csv():
    ensure_seed_file(DEMO_FILE, DEFAULT_DEMOGRAFIA)
    return send_from_directory(DATA_DIR, os.path.basename(DEMO_FILE))


@app.route('/sc_municipios.geojson')
def geojson():
    return send_from_directory(BASE_DIR, 'sc_municipios.geojson')


# --- Executa no Render / localmente ---
if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
