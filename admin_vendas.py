import shutil
import sqlite3
import zipfile
from datetime import date, datetime, timedelta
from html import escape
import os
from pathlib import Path
from threading import Timer

import uvicorn
from fastapi import FastAPI, Form, HTTPException, Query
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse

from licenciamento import gerar_licenca


BASE_PATH = Path(__file__).resolve().parent
ADMIN_DB = BASE_PATH / "admin_vendas.db"
COMERCIAL_DIR = Path(os.getenv("ORCAMENTOAPP_COMERCIAL_DIR", r"E:\App Orcamento Familiar Comercial"))
PACOTES_DIR = COMERCIAL_DIR / "pacotes_temporarios"
BASE_CLIENTE_DIR = BASE_PATH / "base_cliente"
GUIA_CLIENTE_PATH = BASE_PATH / "GUIA_DO_CLIENTE.html"
RETENCAO_PACOTES_DIAS = 15

app = FastAPI(title="OrcamentoApp - Admin de Vendas")


def get_conn():
    conn = sqlite3.connect(ADMIN_DB)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    PACOTES_DIR.mkdir(parents=True, exist_ok=True)
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
                entrega_tipo TEXT NOT NULL DEFAULT 'INSTALACAO_COMPLETA',
                pagamento_confirmado_em TEXT,
                pasta_pacote TEXT,
                pacote_zip TEXT,
                criado_em TEXT NOT NULL,
                atualizado_em TEXT NOT NULL
            )
            """
        )
        colunas = {row["name"] for row in conn.execute("PRAGMA table_info(vendas)").fetchall()}
        for nome, ddl in {
            "entrega_tipo": "ALTER TABLE vendas ADD COLUMN entrega_tipo TEXT NOT NULL DEFAULT 'INSTALACAO_COMPLETA'",
            "pagamento_confirmado_em": "ALTER TABLE vendas ADD COLUMN pagamento_confirmado_em TEXT",
            "pasta_pacote": "ALTER TABLE vendas ADD COLUMN pasta_pacote TEXT",
        }.items():
            if nome not in colunas:
                conn.execute(ddl)


def row_to_dict(row):
    return dict(row) if row else None


def nome_seguro(texto: str) -> str:
    return "".join(c if c.isalnum() or c in ["-", "_"] else "_" for c in texto.strip()) or "cliente"


def remover_caminho_controlado(caminho: str | Path | None):
    if not caminho:
        return
    path = Path(caminho)
    if not path.exists():
        return
    root = PACOTES_DIR.resolve()
    resolved = path.resolve()
    if resolved != root and root not in resolved.parents:
        raise RuntimeError(f"Caminho fora da pasta temporaria: {resolved}")
    if resolved.is_dir():
        shutil.rmtree(resolved)
    else:
        resolved.unlink()


def tamanho_pasta(caminho: Path) -> int:
    if not caminho.exists():
        return 0
    return sum(arquivo.stat().st_size for arquivo in caminho.rglob("*") if arquivo.is_file())


def formatar_tamanho(bytes_total: int) -> str:
    if bytes_total >= 1024 ** 3:
        return f"{bytes_total / (1024 ** 3):.2f} GB"
    if bytes_total >= 1024 ** 2:
        return f"{bytes_total / (1024 ** 2):.2f} MB"
    if bytes_total >= 1024:
        return f"{bytes_total / 1024:.2f} KB"
    return f"{bytes_total} bytes"


def limpar_pacotes_antigos(dias: int = RETENCAO_PACOTES_DIAS) -> int:
    limite = datetime.now() - timedelta(days=dias)
    removidos = 0
    if not PACOTES_DIR.exists():
        return removidos
    for item in PACOTES_DIR.iterdir():
        modificado_em = datetime.fromtimestamp(item.stat().st_mtime)
        if modificado_em < limite:
            remover_caminho_controlado(item)
            removidos += 1
    return removidos


def criar_zip(pasta: Path) -> Path:
    zip_path = pasta.with_suffix(".zip")
    if zip_path.exists():
        zip_path.unlink()
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for arquivo in pasta.rglob("*"):
            if arquivo.is_file():
                zf.write(arquivo, arquivo.relative_to(pasta))
    return zip_path


def criar_pacote_cliente(venda: dict, conteudo_licenca: str, tipo: str) -> tuple[Path, Path]:
    entrega_tipo = venda.get("entrega_tipo") or "INSTALACAO_COMPLETA"
    sufixo = "trial" if tipo.upper() == "TRIAL" else "ativacao" if entrega_tipo == "ATIVACAO_TRIAL" else "vendido"
    nome_base = f"{venda['id']:04d}_{nome_seguro(venda['cliente_nome'])}_{sufixo}"
    work_dir = PACOTES_DIR / nome_base

    if work_dir.exists():
        remover_caminho_controlado(work_dir)
    if entrega_tipo == "ATIVACAO_TRIAL" and tipo.upper() != "TRIAL":
        work_dir.mkdir(parents=True)
    else:
        if not BASE_CLIENTE_DIR.exists():
            raise RuntimeError("Base cliente ainda nao existe. Execute criar_pasta_trial.py primeiro.")
        shutil.copytree(BASE_CLIENTE_DIR, work_dir)

    (work_dir / "license.key").write_text(conteudo_licenca, encoding="utf-8")
    if GUIA_CLIENTE_PATH.exists():
        shutil.copy2(GUIA_CLIENTE_PATH, work_dir / "GUIA_DO_CLIENTE.html")
    if entrega_tipo == "ATIVACAO_TRIAL" and tipo.upper() != "TRIAL":
        texto = (
            "ATIVAÇÃO - APP ORÇAMENTO FAMILIAR\n\n"
            "1. Feche o aplicativo.\n"
            "2. Faça backup do arquivo budget_app.db antes da ativação.\n"
            "3. Substitua somente o arquivo license.key da pasta atual por este novo arquivo.\n"
            "4. Abra o aplicativo novamente. Seus dados cadastrados no trial permanecem preservados.\n"
            "5. Consulte GUIA_DO_CLIENTE.html sempre que precisar revisar as funções.\n"
            "6. Se aparecer uma janela preta do sistema, deixe essa janela aberta enquanto usa o app.\n"
        )
        (work_dir / "LEIA-ME_ATIVACAO.txt").write_text(texto, encoding="utf-8")
    else:
        texto = (
            "APP ORÇAMENTO FAMILIAR\n\n"
            "1. Extraia todos os arquivos para uma pasta do computador.\n"
            "2. Execute OrcamentoApp.exe.\n"
            "3. Não apague license.key nem budget_app.db.\n"
            "4. Use o botão Backup dentro do aplicativo para preservar seus dados.\n"
            "5. Abra GUIA_DO_CLIENTE.html ou use o botão Guia de Uso dentro do aplicativo.\n"
            "6. Se aparecer uma janela preta do sistema, deixe essa janela aberta enquanto usa o app.\n"
        )
        (work_dir / "LEIA-ME.txt").write_text(texto, encoding="utf-8")

    return work_dir, criar_zip(work_dir)


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
        pasta_pacote, zip_path = criar_pacote_cliente({**venda, "tipo": tipo}, conteudo, tipo)
        vencimento = datetime.fromisoformat(payload["expira_em"]).date().isoformat()
        agora = datetime.now().isoformat(timespec="seconds")
        pagamento_confirmado_em = agora if tipo.upper() == "PAGO" else venda.get("pagamento_confirmado_em")
        conn.execute(
            """
            UPDATE vendas
            SET tipo = ?, status = ?, data_vencimento = ?, licenca_atual = ?,
                pagamento_confirmado_em = ?, pasta_pacote = ?, pacote_zip = ?, atualizado_em = ?
            WHERE id = ?
            """,
            (tipo.upper(), "ATIVO", vencimento, conteudo, pagamento_confirmado_em, str(pasta_pacote), str(zip_path), agora, venda_id),
        )
        return {"zip_path": zip_path, "payload": payload}


def listar_vendas():
    with get_conn() as conn:
        return [dict(row) for row in conn.execute("SELECT * FROM vendas ORDER BY data_vencimento ASC, id DESC").fetchall()]


def regerar_pacote(venda_id: int) -> dict:
    with get_conn() as conn:
        venda = row_to_dict(conn.execute("SELECT * FROM vendas WHERE id = ?", (venda_id,)).fetchone())
    if not venda:
        raise HTTPException(status_code=404, detail="Venda nao encontrada.")
    if not venda.get("licenca_atual"):
        raise HTTPException(status_code=400, detail="Esta venda ainda nao possui licenca gerada.")
    pasta_pacote, zip_path = criar_pacote_cliente(venda, venda["licenca_atual"], venda["tipo"])
    agora = datetime.now().isoformat(timespec="seconds")
    with get_conn() as conn:
        conn.execute(
            "UPDATE vendas SET pasta_pacote = ?, pacote_zip = ?, atualizado_em = ? WHERE id = ?",
            (str(pasta_pacote), str(zip_path), agora, venda_id),
        )
    return {"pasta_pacote": pasta_pacote, "zip_path": zip_path}


def excluir_pacote(venda_id: int):
    with get_conn() as conn:
        venda = row_to_dict(conn.execute("SELECT pasta_pacote, pacote_zip FROM vendas WHERE id = ?", (venda_id,)).fetchone())
    if not venda:
        raise HTTPException(status_code=404, detail="Venda nao encontrada.")
    remover_caminho_controlado(venda.get("pasta_pacote"))
    remover_caminho_controlado(venda.get("pacote_zip"))
    with get_conn() as conn:
        conn.execute(
            "UPDATE vendas SET pasta_pacote = NULL, pacote_zip = NULL, atualizado_em = ? WHERE id = ?",
            (datetime.now().isoformat(timespec="seconds"), venda_id),
        )


def html_page() -> str:
    vendas = listar_vendas()
    hoje = date.today()
    uso_pacotes = tamanho_pasta(PACOTES_DIR)
    linhas = []
    for venda in vendas:
        venc = date.fromisoformat(venda["data_vencimento"])
        dias = (venc - hoje).days
        classe = "critico" if dias < 0 else "alerta" if dias <= 30 else "ok"
        pacote = ""
        if venda.get("pacote_zip") and Path(venda["pacote_zip"]).exists():
            pacote = f'<a href="/download/{venda["id"]}">baixar pacote</a>'
            pacote += f"""
                <form method="post" action="/vendas/{venda['id']}/excluir-pacote">
                    <button class="secundario">Excluir apos envio</button>
                </form>
            """
        elif venda.get("licenca_atual"):
            pacote = f"""
                <form method="post" action="/vendas/{venda['id']}/regerar-pacote">
                    <button class="secundario">Gerar novamente</button>
                </form>
            """
        else:
            pacote = "<small>Ainda nao gerado</small>"
        if venda["status"] == "AGUARDANDO_PIX":
            acao = f"""
                <form method="post" action="/vendas/{venda['id']}/confirmar-pix">
                    <button>Confirmar PIX e gerar licenca</button>
                </form>
            """
        elif venda["tipo"] == "PAGO":
            acao = f"""
                <form method="post" action="/vendas/{venda['id']}/renovar">
                    <button>Confirmar PIX e renovar 1 ano</button>
                </form>
            """
        else:
            acao = "<small>Aguardando conversao em venda</small>"
        linhas.append(
            f"""
            <tr class="{classe}">
                <td>{venda['id']}</td>
                <td>{escape(venda['cliente_nome'])}<br><small>{escape(venda['cliente_email'])}</small></td>
                <td>{venda['tipo']}</td>
                <td>{venda['status']}</td>
                <td>{venda.get('entrega_tipo') or '-'}</td>
                <td>{venda.get('pagamento_confirmado_em') or '-'}</td>
                <td>{venda['data_implantacao']}</td>
                <td>{venda['data_vencimento']}<br><small>{dias} dias</small></td>
                <td>{pacote}</td>
                <td>{acao}</td>
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
            button.secundario {{ background: #5f6b7a; margin-top: 6px; }}
            table {{ width: 100%; border-collapse: collapse; }}
            th, td {{ padding: 10px; border-bottom: 1px solid #edf0f4; text-align: left; vertical-align: top; }}
            th {{ font-size: 12px; text-transform: uppercase; color: #5c6675; }}
            .ok td {{ background: #f7fff9; }}
            .alerta td {{ background: #fff8e7; }}
            .critico td {{ background: #fff1f1; }}
            small {{ color: #6b7280; }}
            .actions {{ display: flex; gap: 8px; align-items: end; }}
            .nota {{ margin-top: -4px; color: #4b5563; font-size: 14px; line-height: 1.45; }}
            .topo {{ display: flex; align-items: center; justify-content: space-between; gap: 16px; }}
            .perigo {{ background: #b42318; }}
        </style>
    </head>
    <body><main>
        <div class="topo">
            <h1>Admin de Vendas - OrcamentoApp</h1>
            <form method="post" action="/finalizar">
                <button class="perigo">Finalizar painel</button>
            </form>
        </div>
        <section>
            <h2>Armazenamento temporario</h2>
            <p><strong>Pasta:</strong> {escape(str(PACOTES_DIR))}</p>
            <p><strong>Espaco ocupado:</strong> {formatar_tamanho(uso_pacotes)}</p>
            <p class="nota">Pacotes completos sao temporarios. Depois de enviar ao cliente, use Excluir apos envio. Licencas e dados comerciais continuam registrados no banco administrativo.</p>
            <form method="post" action="/limpar-pacotes-antigos">
                <button class="secundario">Excluir pacotes com mais de {RETENCAO_PACOTES_DIAS} dias</button>
            </form>
        </section>
        <section>
            <h2>Novo trial ou venda</h2>
            <p class="nota">TRIAL gera pacote completo por 7 dias. PAGO fica aguardando PIX e so gera a entrega depois da confirmacao no extrato.</p>
            <form class="grid" method="post" action="/vendas">
                <div><label>Cliente</label><input name="cliente_nome" required></div>
                <div><label>Email</label><input name="cliente_email" type="email" required></div>
                <div><label>Documento</label><input name="documento"></div>
                <div><label>Telefone</label><input name="telefone"></div>
                <div><label>Ambiente</label><input name="ambiente" placeholder="Ex: notebook financeiro"></div>
                <div><label>Valor</label><input name="valor" type="number" step="0.01" value="0"></div>
                <div><label>Tipo</label><select name="tipo"><option>TRIAL</option><option>PAGO</option></select></div>
                <div><label>Entrega</label><select name="entrega_tipo"><option value="INSTALACAO_COMPLETA">Instalacao completa</option><option value="ATIVACAO_TRIAL">Cliente ja possui trial: somente licenca</option></select></div>
                <div><label>Data implantacao</label><input name="data_implantacao" type="date" value="{hoje.isoformat()}" required></div>
                <div><label>Dias validade</label><input name="dias_validade" type="number" value="7" required></div>
                <textarea name="observacoes" placeholder="Observacoes comerciais, instalacao, contato..."></textarea>
                <div class="actions"><button>Cadastrar</button></div>
            </form>
        </section>
        <section>
            <h2>Clientes e vencimentos</h2>
            <table>
                <thead><tr><th>ID</th><th>Cliente</th><th>Tipo</th><th>Status</th><th>Entrega</th><th>PIX confirmado</th><th>Implantacao</th><th>Vencimento</th><th>Pacote</th><th>Acao</th></tr></thead>
                <tbody>{''.join(linhas) or '<tr><td colspan="10">Nenhuma venda cadastrada.</td></tr>'}</tbody>
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
    entrega_tipo: str = Form("INSTALACAO_COMPLETA"),
    data_implantacao: str = Form(...),
    dias_validade: int = Form(7),
    observacoes: str = Form(""),
):
    tipo = tipo.upper()
    entrega_tipo = entrega_tipo.upper()
    if tipo == "TRIAL":
        dias_validade = 7
        entrega_tipo = "INSTALACAO_COMPLETA"
    elif tipo == "PAGO":
        dias_validade = 365
    else:
        raise HTTPException(status_code=400, detail="Tipo de venda invalido.")
    if entrega_tipo not in {"INSTALACAO_COMPLETA", "ATIVACAO_TRIAL"}:
        raise HTTPException(status_code=400, detail="Tipo de entrega invalido.")
    implantacao = date.fromisoformat(data_implantacao)
    vencimento = implantacao + timedelta(days=dias_validade)
    agora = datetime.now().isoformat(timespec="seconds")
    with get_conn() as conn:
        cursor = conn.execute(
            """
            INSERT INTO vendas (
                cliente_nome, cliente_email, documento, telefone, ambiente, tipo, status, valor,
                data_venda, data_implantacao, data_vencimento, observacoes, entrega_tipo, criado_em, atualizado_em
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                cliente_nome.strip(),
                cliente_email.strip().lower(),
                documento.strip(),
                telefone.strip(),
                ambiente.strip(),
                tipo,
                "ATIVO" if tipo == "TRIAL" else "AGUARDANDO_PIX",
                valor,
                hoje_iso(),
                implantacao.isoformat(),
                vencimento.isoformat(),
                observacoes.strip(),
                entrega_tipo,
                agora,
                agora,
            ),
        )
        venda_id = cursor.lastrowid
    if tipo == "TRIAL":
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
    with get_conn() as conn:
        conn.execute("UPDATE vendas SET entrega_tipo = 'ATIVACAO_TRIAL' WHERE id = ?", (venda_id,))
    salvar_licenca(venda_id, "PAGO", 365, data_base=data_base)
    return RedirectResponse("/", status_code=303)


@app.post("/vendas/{venda_id}/confirmar-pix")
def confirmar_pix(venda_id: int):
    with get_conn() as conn:
        venda = row_to_dict(conn.execute("SELECT status FROM vendas WHERE id = ?", (venda_id,)).fetchone())
    if not venda:
        raise HTTPException(status_code=404, detail="Venda nao encontrada.")
    if venda["status"] != "AGUARDANDO_PIX":
        raise HTTPException(status_code=400, detail="Esta venda nao esta aguardando confirmacao de PIX.")
    salvar_licenca(venda_id, "PAGO", 365, data_base=date.today().isoformat())
    return RedirectResponse("/", status_code=303)


@app.get("/download/{venda_id}")
def download(venda_id: int):
    with get_conn() as conn:
        venda = row_to_dict(conn.execute("SELECT pacote_zip FROM vendas WHERE id = ?", (venda_id,)).fetchone())
    if not venda or not venda.get("pacote_zip") or not Path(venda["pacote_zip"]).exists():
        raise HTTPException(status_code=404, detail="Pacote nao encontrado.")
    return FileResponse(venda["pacote_zip"], filename=Path(venda["pacote_zip"]).name)


@app.post("/vendas/{venda_id}/excluir-pacote")
def excluir_pacote_rota(venda_id: int):
    excluir_pacote(venda_id)
    return RedirectResponse("/", status_code=303)


@app.post("/vendas/{venda_id}/regerar-pacote")
def regerar_pacote_rota(venda_id: int):
    regerar_pacote(venda_id)
    return RedirectResponse("/", status_code=303)


@app.post("/limpar-pacotes-antigos")
def limpar_pacotes_antigos_rota():
    limpar_pacotes_antigos()
    return RedirectResponse("/", status_code=303)


@app.post("/finalizar", response_class=HTMLResponse)
def finalizar():
    Timer(0.7, lambda: os._exit(0)).start()
    return HTMLResponse(
        """
        <!doctype html>
        <html lang="pt-BR">
        <head><meta charset="utf-8"><title>Painel finalizado</title></head>
        <body style="font-family:Segoe UI,Arial,sans-serif;padding:32px;color:#243041">
            <h1>Painel administrativo finalizado.</h1>
            <p>Voce pode fechar esta aba do navegador.</p>
        </body>
        </html>
        """
    )


if __name__ == "__main__":
    init_db()
    limpar_pacotes_antigos()
    uvicorn.run(app, host="127.0.0.1", port=8020)
