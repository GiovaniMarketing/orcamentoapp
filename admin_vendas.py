import shutil
import sqlite3
import zipfile
from datetime import date, datetime, timedelta
from pathlib import Path

import uvicorn
from fastapi import FastAPI, Form, HTTPException, Query
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse

from licenciamento import gerar_licenca


BASE_PATH = Path(__file__).resolve().parent
ADMIN_DB = BASE_PATH / "admin_vendas.db"
PACOTES_DIR = BASE_PATH / "pacotes_clientes"
TRIAL_DIR = BASE_PATH / "trial"

app = FastAPI(title="OrcamentoApp - Admin de Vendas")


def get_conn():
    conn = sqlite3.connect(ADMIN_DB)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    PACOTES_DIR.mkdir(exist_ok=True)
    with get_conn() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS vendas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                cliente_nome TEXT NOT NULL,
                cliente_email TEXT NOT NULL,
                documento TEXT,
                telefone TEXT,
                ambiente TEXT,
                tipo TEXT NOT NULL,
                status TEXT NOT NULL,
                valor REAL DEFAULT 0,
                data_venda TEXT,
                data_implantacao TEXT NOT NULL,
                data_vencimento TEXT NOT NULL,
                observacoes TEXT,
                licenca_atual TEXT,
                pacote_zip TEXT,
                criado_em TEXT NOT NULL,
                atualizado_em TEXT NOT NULL
            )
            """
        )


def row_to_dict(row):
    return dict(row) if row else None


def nome_seguro(texto: str) -> str:
    return "".join(c if c.isalnum() or c in ["-", "_"] else "_" for c in texto.strip()) or "cliente"


def criar_pacote_cliente(venda: dict, conteudo_licenca: str) -> Path:
    if not TRIAL_DIR.exists():
        raise RuntimeError("Pasta trial ainda nao existe. Gere a pasta trial primeiro.")

    nome_base = f"{venda['id']:04d}_{nome_seguro(venda['cliente_nome'])}_{venda['tipo'].lower()}"
    work_dir = PACOTES_DIR / nome_base
    zip_path = PACOTES_DIR / f"{nome_base}.zip"

    if work_dir.exists():
        shutil.rmtree(work_dir)
    shutil.copytree(TRIAL_DIR, work_dir)
    (work_dir / "license.key").write_text(conteudo_licenca, encoding="utf-8")

    if zip_path.exists():
        zip_path.unlink()
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for arquivo in work_dir.rglob("*"):
            if arquivo.is_file():
                zf.write(arquivo, arquivo.relative_to(work_dir))
    return zip_path


def salvar_licenca(venda_id: int, tipo: str, dias: int, data_base: str | None = None) -> dict:
    with get_conn() as conn:
        venda = row_to_dict(conn.execute("SELECT * FROM vendas WHERE id = ?", (venda_id,)).fetchone())
        if not venda:
            raise HTTPException(status_code=404, detail="Venda nao encontrada.")

        conteudo, payload = gerar_licenca(
            venda["cliente_nome"],
            venda["cliente_email"],
            tipo,
            dias,
            data_base or venda["data_implantacao"],
        )
        zip_path = criar_pacote_cliente({**venda, "tipo": tipo}, conteudo)
        vencimento = datetime.fromisoformat(payload["expira_em"]).date().isoformat()
        agora = datetime.now().isoformat(timespec="seconds")
        conn.execute(
            """
            UPDATE vendas
            SET tipo = ?, status = ?, data_vencimento = ?, licenca_atual = ?, pacote_zip = ?, atualizado_em = ?
            WHERE id = ?
            """,
            (tipo.upper(), "ATIVO", vencimento, conteudo, str(zip_path), agora, venda_id),
        )
        return {"zip_path": zip_path, "payload": payload}


def listar_vendas():
    with get_conn() as conn:
        return [dict(row) for row in conn.execute("SELECT * FROM vendas ORDER BY data_vencimento ASC, id DESC").fetchall()]


def html_page() -> str:
    vendas = listar_vendas()
    hoje = date.today()
    linhas = []
    for venda in vendas:
        venc = date.fromisoformat(venda["data_vencimento"])
        dias = (venc - hoje).days
        classe = "critico" if dias < 0 else "alerta" if dias <= 30 else "ok"
        pacote = ""
        if venda.get("pacote_zip") and Path(venda["pacote_zip"]).exists():
            pacote = f'<a href="/download/{venda["id"]}">baixar pacote</a>'
        linhas.append(
            f"""
            <tr class="{classe}">
                <td>{venda['id']}</td>
                <td>{venda['cliente_nome']}<br><small>{venda['cliente_email']}</small></td>
                <td>{venda['tipo']}</td>
                <td>{venda['status']}</td>
                <td>{venda['data_implantacao']}</td>
                <td>{venda['data_vencimento']}<br><small>{dias} dias</small></td>
                <td>{pacote}</td>
                <td>
                    <form method="post" action="/vendas/{venda['id']}/renovar">
                        <button>Renovar 1 ano</button>
                    </form>
                </td>
            </tr>
            """
        )

    return f"""
    <!doctype html>
    <html lang="pt-BR">
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <title>Admin de Vendas - OrcamentoApp</title>
        <style>
            body {{ font-family: Segoe UI, Arial, sans-serif; margin: 0; background: #f4f6f8; color: #243041; }}
            main {{ max-width: 1180px; margin: 24px auto; padding: 0 16px; }}
            section {{ background: white; border-radius: 8px; padding: 18px; margin-bottom: 18px; box-shadow: 0 2px 10px #0001; }}
            h1, h2 {{ color: #2457c5; margin-top: 0; }}
            form.grid {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; }}
            label {{ font-size: 13px; font-weight: 600; color: #5c6675; }}
            input, select, textarea {{ width: 100%; box-sizing: border-box; padding: 9px; border: 1px solid #cfd6e0; border-radius: 6px; }}
            textarea {{ grid-column: 1 / -1; min-height: 70px; }}
            button {{ background: #2457c5; color: white; border: 0; border-radius: 6px; padding: 9px 12px; cursor: pointer; font-weight: 700; }}
            table {{ width: 100%; border-collapse: collapse; }}
            th, td {{ padding: 10px; border-bottom: 1px solid #edf0f4; text-align: left; vertical-align: top; }}
            th {{ font-size: 12px; text-transform: uppercase; color: #5c6675; }}
            .ok td {{ background: #f7fff9; }}
            .alerta td {{ background: #fff8e7; }}
            .critico td {{ background: #fff1f1; }}
            small {{ color: #6b7280; }}
            .actions {{ display: flex; gap: 8px; align-items: end; }}
        </style>
    </head>
    <body><main>
        <h1>Admin de Vendas - OrcamentoApp</h1>
        <section>
            <h2>Nova venda / trial</h2>
            <form class="grid" method="post" action="/vendas">
                <div><label>Cliente</label><input name="cliente_nome" required></div>
                <div><label>Email</label><input name="cliente_email" type="email" required></div>
                <div><label>Documento</label><input name="documento"></div>
                <div><label>Telefone</label><input name="telefone"></div>
                <div><label>Ambiente</label><input name="ambiente" placeholder="Ex: notebook financeiro"></div>
                <div><label>Valor</label><input name="valor" type="number" step="0.01" value="0"></div>
                <div><label>Tipo</label><select name="tipo"><option>TRIAL</option><option>PAGO</option></select></div>
                <div><label>Data implantacao</label><input name="data_implantacao" type="date" value="{hoje.isoformat()}" required></div>
                <div><label>Dias validade</label><input name="dias_validade" type="number" value="7" required></div>
                <textarea name="observacoes" placeholder="Observacoes comerciais, instalacao, contato..."></textarea>
                <div class="actions"><button>Cadastrar e gerar pacote</button></div>
            </form>
        </section>
        <section>
            <h2>Clientes e vencimentos</h2>
            <table>
                <thead><tr><th>ID</th><th>Cliente</th><th>Tipo</th><th>Status</th><th>Implantacao</th><th>Vencimento</th><th>Pacote</th><th>Acao</th></tr></thead>
                <tbody>{''.join(linhas) or '<tr><td colspan="8">Nenhuma venda cadastrada.</td></tr>'}</tbody>
            </table>
        </section>
    </main></body></html>
    """


@app.get("/", response_class=HTMLResponse)
def index():
    return HTMLResponse(html_page())


@app.post("/vendas")
def criar_venda(
    cliente_nome: str = Form(...),
    cliente_email: str = Form(...),
    documento: str = Form(""),
    telefone: str = Form(""),
    ambiente: str = Form(""),
    valor: float = Form(0),
    tipo: str = Form("TRIAL"),
    data_implantacao: str = Form(...),
    dias_validade: int = Form(7),
    observacoes: str = Form(""),
):
    tipo = tipo.upper()
    implantacao = date.fromisoformat(data_implantacao)
    vencimento = implantacao + timedelta(days=dias_validade)
    agora = datetime.now().isoformat(timespec="seconds")
    with get_conn() as conn:
        cursor = conn.execute(
            """
            INSERT INTO vendas (
                cliente_nome, cliente_email, documento, telefone, ambiente, tipo, status, valor,
                data_venda, data_implantacao, data_vencimento, observacoes, criado_em, atualizado_em
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                cliente_nome.strip(),
                cliente_email.strip().lower(),
                documento.strip(),
                telefone.strip(),
                ambiente.strip(),
                tipo,
                "CADASTRADO",
                valor,
                hoje_iso(),
                implantacao.isoformat(),
                vencimento.isoformat(),
                observacoes.strip(),
                agora,
                agora,
            ),
        )
        venda_id = cursor.lastrowid
    salvar_licenca(venda_id, tipo, dias_validade)
    return RedirectResponse("/", status_code=303)


def hoje_iso() -> str:
    return date.today().isoformat()


@app.post("/vendas/{venda_id}/renovar")
def renovar(venda_id: int):
    with get_conn() as conn:
        venda = row_to_dict(conn.execute("SELECT data_vencimento FROM vendas WHERE id = ?", (venda_id,)).fetchone())
    if not venda:
        raise HTTPException(status_code=404, detail="Venda nao encontrada.")
    vencimento_atual = date.fromisoformat(venda["data_vencimento"])
    data_base = max(vencimento_atual, date.today()).isoformat()
    salvar_licenca(venda_id, "PAGO", 365, data_base=data_base)
    return RedirectResponse("/", status_code=303)


@app.get("/download/{venda_id}")
def download(venda_id: int):
    with get_conn() as conn:
        venda = row_to_dict(conn.execute("SELECT pacote_zip FROM vendas WHERE id = ?", (venda_id,)).fetchone())
    if not venda or not venda.get("pacote_zip") or not Path(venda["pacote_zip"]).exists():
        raise HTTPException(status_code=404, detail="Pacote nao encontrado.")
    return FileResponse(venda["pacote_zip"], filename=Path(venda["pacote_zip"]).name)


if __name__ == "__main__":
    init_db()
    uvicorn.run(app, host="127.0.0.1", port=8020)
