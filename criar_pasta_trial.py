import shutil
import sqlite3
import zipfile
from datetime import date
from pathlib import Path

from licenciamento import gerar_licenca


BASE_PATH = Path(__file__).resolve().parent
TRIAL_DIR = BASE_PATH / "trial"
DIST_CLIENTE = BASE_PATH / "dist_cliente"


def criar_banco_vazio(db_path: Path):
    if db_path.exists():
        db_path.unlink()
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE receitas (
            id INTEGER PRIMARY KEY,
            descricao TEXT,
            valor REAL,
            data DATETIME,
            pago BOOLEAN,
            categoria TEXT,
            recorrente BOOLEAN,
            data_vencimento DATE
        )
    """)
    cursor.execute("""
        CREATE TABLE despesas (
            id INTEGER PRIMARY KEY,
            descricao TEXT,
            valor REAL,
            data DATETIME,
            pago BOOLEAN,
            categoria TEXT,
            recorrente BOOLEAN,
            data_vencimento DATE
        )
    """)
    cursor.execute("""
        CREATE TABLE poupanca (
            id INTEGER PRIMARY KEY,
            tipo TEXT,
            valor REAL,
            data DATETIME,
            tipo_investimento_id INTEGER,
            taxa_mensal REAL,
            prazo_meses INTEGER
        )
    """)
    cursor.execute("""
        CREATE TABLE tipos_investimento (
            id INTEGER PRIMARY KEY,
            nome TEXT NOT NULL UNIQUE,
            taxa_sugerida_mensal REAL NOT NULL DEFAULT 0
        )
    """)
    cursor.executemany(
        "INSERT INTO tipos_investimento (nome, taxa_sugerida_mensal) VALUES (?, ?)",
        [
            ("Poupanca", 0.005),
            ("CDB", 0.008),
            ("Tesouro Direto", 0.007),
            ("Fundo de Investimento", 0.006),
            ("Acoes/FIIs", 0.010),
        ],
    )
    conn.commit()
    conn.close()


def criar_trial():
    exe_origem = DIST_CLIENTE / "OrcamentoApp.exe"
    if not exe_origem.exists():
        raise FileNotFoundError("Execute o build do cliente antes: PyInstaller main_cliente.spec")

    if TRIAL_DIR.exists():
        shutil.rmtree(TRIAL_DIR)
    TRIAL_DIR.mkdir()

    shutil.copy2(exe_origem, TRIAL_DIR / "OrcamentoApp.exe")
    shutil.copytree(BASE_PATH / "templates", TRIAL_DIR / "templates")
    shutil.copytree(BASE_PATH / "static", TRIAL_DIR / "static")
    shutil.copy2(BASE_PATH / "favicon.ico", TRIAL_DIR / "favicon.ico")
    criar_banco_vazio(TRIAL_DIR / "budget_app.db")

    conteudo, payload = gerar_licenca(
        "Cliente Trial",
        "trial@cliente.local",
        "TRIAL",
        7,
        date.today().isoformat(),
    )
    (TRIAL_DIR / "license.key").write_text(conteudo, encoding="utf-8")
    (TRIAL_DIR / "LEIA-ME.txt").write_text(
        "OrcamentoApp - Trial\n\n"
        "1. Execute OrcamentoApp.exe.\n"
        "2. Nao apague o arquivo license.key.\n"
        "3. O banco budget_app.db fica nesta pasta e guarda os dados do teste.\n"
        f"4. Esta licenca trial vence em {payload['expira_em'][:10]}.\n\n"
        "Para ativar por 1 ano, substitua o license.key pelo arquivo de licenca enviado apos a compra.\n",
        encoding="utf-8",
    )
    (TRIAL_DIR / "TERMO_DE_USO_TRIAL.txt").write_text(
        "TERMO DE USO - APP ORCAMENTO FAMILIAR TRIAL\n\n"
        "Este pacote e fornecido para avaliacao por prazo limitado.\n"
        "Os dados inseridos ficam armazenados localmente no arquivo budget_app.db.\n"
        "O usuario e responsavel por manter copia de seguranca dos seus dados.\n"
        "A ativacao anual depende de uma license.key valida emitida pelo fornecedor.\n"
        "Nao apague nem altere os arquivos license.key e budget_app.db sem antes fazer backup.\n",
        encoding="utf-8",
    )

    licencas_dir = TRIAL_DIR / "licenses"
    licencas_dir.mkdir(exist_ok=True)
    (licencas_dir / "AVISOS_BIBLIOTECAS.txt").write_text(
        "AVISOS DE BIBLIOTECAS\n\n"
        "Este aplicativo usa Python, FastAPI, PyInstaller, PySide6/Qt for Python e outras bibliotecas de terceiros.\n"
        "PySide6/Qt for Python pode ser usado sob termos LGPL/GPL ou licenca comercial da Qt, conforme o caso.\n"
        "Os avisos completos das bibliotecas devem ser mantidos junto ao pacote distribuido.\n",
        encoding="utf-8",
    )

    zip_path = BASE_PATH / "OrcamentoApp_TRIAL.zip"
    if zip_path.exists():
        zip_path.unlink()
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for arquivo in TRIAL_DIR.rglob("*"):
            if arquivo.is_file():
                zf.write(arquivo, arquivo.relative_to(TRIAL_DIR))
    return zip_path


if __name__ == "__main__":
    pacote = criar_trial()
    print(f"Trial criado em: {TRIAL_DIR}")
    print(f"ZIP criado em: {pacote}")
