import sys
import os
from pathlib import Path
from datetime import datetime, timedelta, date
import uvicorn
import sqlite3
import json
import logging
import csv
import io
import socket
import shutil
import re
from html import escape
from calendar import monthrange
from logging.handlers import RotatingFileHandler
import multiprocessing
from PyQt6.QtWidgets import QApplication, QMainWindow, QMessageBox
from PyQt6.QtCore import QUrl, QTimer, QCoreApplication
from PyQt6.QtGui import QIcon
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import QWebEnginePage
from typing import List, Optional, Dict, Any, Literal 
from fastapi import FastAPI, HTTPException, Query, Body, Path as FastApiPath, APIRouter, UploadFile, File
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

# Versao interna/pessoal.

# ============================================================
# Diretórios de Base e Recursos
# ============================================================
def get_base_dir():
    """Retorna o diretório base do app, compatível com .exe (PyInstaller)."""
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent

BASE_PATH = get_base_dir()

# ============================================================
# Logging
# ============================================================
LOG_FILE_PATH = BASE_PATH / "app_log.txt"

def setup_logging(log_path):
    """Configura o logging para escrever num ficheiro."""
    try:
        if multiprocessing.current_process().name == 'MainProcess' and os.path.exists(log_path):
            try:
                # Evita que o log cresça demais em ambientes de desenvolvimento/teste
                # Manter esta remoção se o log for apenas para debug.
                pass 
                # os.remove(log_path) # Comentei a remoção para não apagar logs de debug
            except OSError as e:
                print(f"Aviso: Não foi possível remover o log antigo: {e}")

        handler = RotatingFileHandler(log_path, maxBytes=1024*1024, backupCount=1, encoding='utf-8')
        handler.setFormatter(logging.Formatter('%(asctime)s [%(levelname)-8s] [%(processName)-15s] %(message)s', datefmt='%Y-%m-%d %H:%M:%S'))

        logger = logging.getLogger()
        if not logger.hasHandlers():
            logger.setLevel(logging.INFO)
            logger.addHandler(handler)
        logging.getLogger().propagate = True

    except Exception as e:
        print(f"Erro ao configurar o logger: {e}")

setup_logging(LOG_FILE_PATH)
logging.info("="*50)
logging.info(f"Log iniciado. BASE_PATH: {BASE_PATH}")

# ============================================================
# Licenciamento
# ============================================================

def verificar_licenca_local():
    logging.info("Verificando licenca (uso interno ilimitado)...")
    return {"valido": True, "mensagem": "Licenca interna ilimitada", "dias_restantes": None, "payload": {"tipo_licenca": "INTERNA", "cliente_nome": "Uso interno", "cliente_email": ""}}


# ============================================================
# Banco de Dados Local
# ============================================================
def resolve_db_path() -> Path:
    default_path = BASE_PATH / "budget_app.db"
    if default_path.exists() or getattr(sys, 'frozen', False):
        return default_path

    dist_path = BASE_PATH / "dist" / "budget_app.db"
    if dist_path.exists():
        return dist_path

    legacy_path = BASE_PATH / "data" / "orcamento.db"
    if legacy_path.exists():
        return legacy_path

    return default_path

DB_PATH = resolve_db_path()
logging.info(f"Caminhos definidos. DB_PATH: {DB_PATH}")

def criar_banco():
    """
    Cria ou atualiza o banco local sem apagar dados existentes.
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS receitas (
                id INTEGER PRIMARY KEY,
                descricao TEXT,
                valor REAL,
                data DATETIME,
                pago BOOLEAN,
                categoria TEXT,
                recorrente BOOLEAN,
                data_vencimento DATE
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS despesas (
                id INTEGER PRIMARY KEY,
                descricao TEXT,
                valor REAL,
                data DATETIME,
                pago BOOLEAN,
                categoria TEXT,
                recorrente BOOLEAN,
                data_vencimento DATE
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS poupanca (
                id INTEGER PRIMARY KEY,
                tipo TEXT,
                valor REAL,
                data DATETIME,
                tipo_investimento_id INTEGER,
                taxa_mensal REAL,
                prazo_meses INTEGER
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS tipos_investimento (
                id INTEGER PRIMARY KEY,
                nome TEXT NOT NULL UNIQUE,
                taxa_sugerida_mensal REAL NOT NULL DEFAULT 0
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS metas (
                id INTEGER PRIMARY KEY,
                nome TEXT NOT NULL,
                valor_alvo REAL NOT NULL,
                valor_atual REAL NOT NULL DEFAULT 0,
                data_limite DATE,
                observacoes TEXT,
                criado_em DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        cursor.execute("PRAGMA table_info(poupanca)")
        colunas_poupanca = {row[1] for row in cursor.fetchall()}
        for nome_coluna, ddl in {
            "tipo_investimento_id": "ALTER TABLE poupanca ADD COLUMN tipo_investimento_id INTEGER",
            "taxa_mensal": "ALTER TABLE poupanca ADD COLUMN taxa_mensal REAL",
            "prazo_meses": "ALTER TABLE poupanca ADD COLUMN prazo_meses INTEGER",
        }.items():
            if nome_coluna not in colunas_poupanca:
                cursor.execute(ddl)

        tipos_padrao = [
            ("Poupanca", 0.005),
            ("CDB", 0.008),
            ("Tesouro Direto", 0.007),
            ("Fundo de Investimento", 0.006),
            ("Acoes/FIIs", 0.010),
        ]
        cursor.executemany(
            "INSERT OR IGNORE INTO tipos_investimento (nome, taxa_sugerida_mensal) VALUES (?, ?)",
            tipos_padrao
        )
        conn.commit()
        conn.close()
        logging.info("Banco de dados verificado/atualizado com sucesso.")
    except Exception as e:
        logging.error(f"!!! ERRO AO CONECTAR À BASE DE DADOS !!!: {e}", exc_info=True)
        raise

def encontrar_porta_livre(porta_inicial: int = 8000, tentativas: int = 50) -> int:
    for porta in range(porta_inicial, porta_inicial + tentativas):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                sock.bind(("127.0.0.1", porta))
                return porta
            except OSError:
                continue
    raise RuntimeError("Nao foi possivel encontrar porta local livre para iniciar o app.")

# ============================================================
# Modelos Pydantic
# ============================================================
try:
    from pydantic import BaseModel, Field
except ImportError:
    logging.error("Pydantic não encontrado. Instale com 'pip install pydantic'")
    class BaseModel: pass
    def Field(*args, **kwargs): return None

class TransacaoBase(BaseModel):
    descricao: str
    valor: float
    categoria: Optional[str] = None
    recorrente: Optional[bool] = False
    data_vencimento: Optional[date] = None

class TransacaoCreate(TransacaoBase):
    pago: Optional[bool] = None
    data: Optional[datetime] = Field(default_factory=datetime.now)

class TransacaoUpdate(BaseModel):
    descricao: Optional[str] = None
    valor: Optional[float] = None
    categoria: Optional[str] = None
    recorrente: Optional[bool] = None
    data_vencimento: Optional[date] = None
    pago: Optional[bool] = None
    data: Optional[datetime] = None

class Transacao(TransacaoBase): 
    id: int
    pago: bool
    data: datetime

# =======================================================
# MÓDULO POUPANÇA / INVESTIMENTOS (ATUALIZADO)
# =======================================================
class PoupancaMovimento(BaseModel):
    tipo: Literal["deposito", "retirada"] 
    valor: float = Field(..., gt=0, description="Valor do movimento (deve ser positivo)")
    tipo_investimento_id: int = Field(..., description="ID do tipo de investimento (Ex: 1 para Poupança)")
    data: Optional[date] = None

    # (Req 1) Campos adicionados
    taxa_mensal: Optional[float] = Field(None, description="Taxa de rendimento mensal (Ex: 0.01 para 1%)") 
    prazo_meses: Optional[int] = Field(None, ge=1, description="Duração do investimento em meses (mínimo 1)") 

    # (NOVO) Campo para lógica de transferência
    transferir_saldo: Optional[bool] = Field(False, description="Se True, afeta o Saldo Real")

class PoupancaMovimentoRegistro(PoupancaMovimento):
    id: int

class TipoInvestimento(BaseModel):
    nome: str
    # (CORRIGIDO) Nome da coluna atualizado
    taxa_sugerida_mensal: float = Field(..., description="Taxa de rendimento mensal sugerida")
    
class TipoInvestimentoRegistro(TipoInvestimento):
    id: int
# =======================================================

class SaldoAtual(BaseModel):
    total_receitas: float
    total_despesas: float
    receitas_confirmadas: float
    despesas_confirmadas: float
    total_poupanca: float
    saldo_real_confirmado: float
    saldo_previsto: float
    patrimonio_atual: float

class AnaliseCategoria(BaseModel):
    categoria: str
    total: float
    percentual_da_receita: float

class AnaliseDespesas(BaseModel):
    analise_por_categoria: List[AnaliseCategoria]
    total_receitas: float
    total_despesas: float

class DetalhesVariaveis(BaseModel):
    receitas: List = []
    despesas: List = []
class ProjecaoMensal(BaseModel):
    detalhes_recorrentes: List = []
    detalhes_variaveis: DetalhesVariaveis = Field(default_factory=DetalhesVariaveis)

class MetaCreate(BaseModel):
    nome: str
    valor_alvo: float = Field(..., gt=0)
    valor_atual: Optional[float] = Field(0, ge=0)
    data_limite: Optional[date] = None
    observacoes: Optional[str] = None

class MetaUpdate(BaseModel):
    nome: Optional[str] = None
    valor_alvo: Optional[float] = Field(None, gt=0)
    valor_atual: Optional[float] = Field(None, ge=0)
    data_limite: Optional[date] = None
    observacoes: Optional[str] = None

class MetaRegistro(MetaCreate):
    id: int
    criado_em: Optional[datetime] = None

# ============================================================
# Funções DB (usadas pela API) - INCLUINDO RELATÓRIOS
# ============================================================
def get_db_conn():
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.execute("PRAGMA foreign_keys = ON")
        conn.row_factory = sqlite3.Row
        return conn
    except Exception as e:
        logging.error(f"Erro ao conectar à BD: {e}", exc_info=True)
        return None

# -------------------------------------------------------------
# 1. FUNÇÕES DE CÁLCULO DE SALDO (DEVE ESTAR NO TOPO)
# -------------------------------------------------------------

def db_get_saldo_atual() -> Optional[dict]:
    conn = get_db_conn()
    if not conn: return None
    try:
        cursor = conn.cursor()
        
        # (ATUALIZADO) Saldo de Investimentos agora usa a tabela 'poupanca'
        cursor.execute("SELECT SUM(CASE WHEN tipo='deposito' THEN valor WHEN tipo='retirada' THEN -valor ELSE 0 END) FROM poupanca")
        total_poupanca = cursor.fetchone()[0] or 0.0
        
        # Saldo Real (Confirmado)
        cursor.execute("SELECT SUM(valor) FROM receitas WHERE pago=1")
        receitas_confirmadas = cursor.fetchone()[0] or 0.0
        cursor.execute("SELECT SUM(valor) FROM despesas WHERE pago=1")
        despesas_confirmadas = cursor.fetchone()[0] or 0.0
        
        # Saldo Total (Previsto)
        cursor.execute("SELECT SUM(valor) FROM receitas")
        total_receitas = cursor.fetchone()[0] or 0.0
        cursor.execute("SELECT SUM(valor) FROM despesas")
        total_despesas = cursor.fetchone()[0] or 0.0
        
        return {
            "total_receitas": round(total_receitas, 2),
            "total_despesas": round(total_despesas, 2),
            "receitas_confirmadas": round(receitas_confirmadas, 2),
            "despesas_confirmadas": round(despesas_confirmadas, 2),
            "total_poupanca": round(total_poupanca, 2),
            "saldo_real_confirmado": round(receitas_confirmadas - despesas_confirmadas, 2),
            "saldo_previsto": round(total_receitas - total_despesas, 2),
            "patrimonio_atual": round(receitas_confirmadas - despesas_confirmadas + total_poupanca, 2),
        }
    except Exception as e:
        logging.error(f"Erro ao calcular saldo atual: {e}", exc_info=True)
        return None
    finally:
        if conn: conn.close()

# -------------------------------------------------------------
# 2. FUNÇÕES DE TRANSAÇÃO (ORDEM INTERMEDIÁRIA)
# -------------------------------------------------------------

def db_get_receitas() -> List[dict]:
    conn = get_db_conn()
    if not conn: return []
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM receitas ORDER BY data DESC")
        receitas = [dict(row) for row in cursor.fetchall()]
        return receitas
    except Exception as e:
        logging.error(f"Erro ao buscar receitas: {e}", exc_info=True)
        return []
    finally:
        if conn: conn.close()

def db_get_receita_by_id(item_id: int) -> Optional[dict]:
    conn = get_db_conn()
    if not conn: return None
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM receitas WHERE id = ?", (item_id,))
        receita = cursor.fetchone()
        return dict(receita) if receita else None
    except Exception as e:
        logging.error(f"Erro ao buscar receita ID {item_id}: {e}", exc_info=True)
        return None
    finally:
        if conn: conn.close()

def db_add_receita(receita: TransacaoCreate) -> Optional[dict]:
    conn = get_db_conn()
    if not conn: return None
    pago_default = receita.pago if receita.pago is not None else True
    try:
        cursor = conn.cursor()
        data_db = receita.data if isinstance(receita.data, datetime) else datetime.now()
        cursor.execute(
            """INSERT INTO receitas (descricao, valor, data, pago, categoria, recorrente, data_vencimento)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (receita.descricao, receita.valor, data_db, pago_default,
             receita.categoria, receita.recorrente, receita.data_vencimento)
        )
        conn.commit()
        new_id = cursor.lastrowid
        return db_get_receita_by_id(new_id)
    except Exception as e:
        logging.error(f"Erro ao adicionar receita: {e}", exc_info=True)
        conn.rollback()
        return None
    finally:
        if conn: conn.close()

def db_update_receita(item_id: int, receita_update: TransacaoUpdate) -> Optional[dict]:
    conn = get_db_conn()
    if not conn: return None
    update_fields = receita_update.model_dump(exclude_unset=True) 
    if not update_fields:
        logging.warning("Tentativa de update de receita sem dados.")
        return db_get_receita_by_id(item_id)

    set_clause = ", ".join([f"{key} = ?" for key in update_fields.keys()])
    values = list(update_fields.values())
    values.append(item_id)
    query = f"UPDATE receitas SET {set_clause} WHERE id = ?"

    try:
        cursor = conn.cursor()
        logging.info(f"Executando SQL Update Receita: {query} com valores {tuple(values)}")
        cursor.execute(query, tuple(values))
        conn.commit()
        if cursor.rowcount == 0:
            logging.warning(f"Receita ID {item_id} não encontrada para update.")
            return None
        return db_get_receita_by_id(item_id)
    except Exception as e:
        logging.error(f"Erro ao atualizar receita ID {item_id}: {e}", exc_info=True)
        conn.rollback()
        return None
    finally:
        if conn: conn.close()

def db_delete_receita(item_id: int) -> bool:
    conn = get_db_conn()
    if not conn: return False
    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM receitas WHERE id = ?", (item_id,))
        conn.commit()
        return cursor.rowcount > 0
    except Exception as e:
        logging.error(f"Erro ao deletar receita {item_id}: {e}", exc_info=True)
        conn.rollback()
        return False
    finally:
        if conn: conn.close()

def db_get_despesas() -> List[dict]:
    conn = get_db_conn()
    if not conn: return []
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM despesas ORDER BY data DESC")
        despesas = [dict(row) for row in cursor.fetchall()]
        return despesas
    except Exception as e:
        logging.error(f"Erro ao buscar despesas: {e}", exc_info=True)
        return []
    finally:
        if conn: conn.close()

def db_get_despesa_by_id(item_id: int) -> Optional[dict]:
    conn = get_db_conn()
    if not conn: return None
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM despesas WHERE id = ?", (item_id,))
        despesa = cursor.fetchone()
        return dict(despesa) if despesa else None
    except Exception as e:
        logging.error(f"Erro ao buscar despesa ID {item_id}: {e}", exc_info=True)
        return None
    finally:
        if conn: conn.close()

def db_add_despesa(despesa: TransacaoCreate) -> Optional[dict]:
    conn = get_db_conn()
    if not conn: return None
    pago_default = despesa.pago if despesa.pago is not None else False
    try:
        cursor = conn.cursor()
        data_db = despesa.data if isinstance(despesa.data, datetime) else datetime.now()
        cursor.execute(
            """INSERT INTO despesas (descricao, valor, data, pago, categoria, recorrente, data_vencimento)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (despesa.descricao, despesa.valor, data_db, pago_default,
             despesa.categoria, despesa.recorrente, despesa.data_vencimento)
        )
        conn.commit()
        new_id = cursor.lastrowid
        return db_get_despesa_by_id(new_id)
    except Exception as e:
        logging.error(f"Erro ao adicionar despesa: {e}", exc_info=True)
        conn.rollback()
        return None
    finally:
        if conn: conn.close()

def db_update_despesa(item_id: int, despesa_update: TransacaoUpdate) -> Optional[dict]:
    conn = get_db_conn()
    if not conn: return None
    update_fields = despesa_update.model_dump(exclude_unset=True) 
    if not update_fields:
        logging.warning("Tentativa de update de despesa sem dados.")
        return db_get_despesa_by_id(item_id)

    set_clause = ", ".join([f"{key} = ?" for key in update_fields.keys()])
    values = list(update_fields.values())
    values.append(item_id)
    query = f"UPDATE despesas SET {set_clause} WHERE id = ?"

    try:
        cursor = conn.cursor()
        logging.info(f"Executando SQL Update Despesa: {query} com valores {tuple(values)}")
        cursor.execute(query, tuple(values))
        conn.commit()
        if cursor.rowcount == 0:
            logging.warning(f"Despesa ID {item_id} não encontrada para update.")
            return None
        return db_get_despesa_by_id(item_id)
    except Exception as e:
        logging.error(f"Erro ao atualizar despesa ID {item_id}: {e}", exc_info=True)
        conn.rollback()
        return None
    finally:
        if conn: conn.close()

def db_delete_despesa(item_id: int) -> bool:
    conn = get_db_conn()
    if not conn: return False
    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM despesas WHERE id = ?", (item_id,))
        conn.commit()
        return cursor.rowcount > 0
    except Exception as e:
        logging.error(f"Erro ao deletar despesa {item_id}: {e}", exc_info=True)
        conn.rollback()
        return False
    finally:
        if conn: conn.close()

def db_toggle_pago(tipo: str, item_id: int) -> bool:
    tabela = "receitas" if tipo == "receita" else "despesas"
    conn = get_db_conn()
    if not conn: return False
    try:
        cursor = conn.cursor()
        cursor.execute(f"UPDATE {tabela} SET pago = CASE pago WHEN 1 THEN 0 ELSE 1 END WHERE id = ?", (item_id,))
        conn.commit()
        if cursor.rowcount == 0: return False
        return True
    except Exception as e:
        logging.error(f"Erro ao alterar status pago ({tipo} {item_id}): {e}", exc_info=True)
        conn.rollback()
        return False
    finally:
        if conn: conn.close()

# --- Funções de Poupança/Investimento (CORRIGIDAS) ---
def db_add_poupanca(movimento: PoupancaMovimento) -> Optional[PoupancaMovimentoRegistro]:
    conn = get_db_conn()
    if not conn: return None
    
    # Validação (Req 7) - A lógica de validação principal está na API
    if movimento.tipo == 'deposito' and (movimento.taxa_mensal is None or movimento.prazo_meses is None):
        logging.error(f"Erro DB: Depósitos DEVEM ter taxa_mensal e prazo_meses. {movimento.model_dump()}")
        return None
        
    try:
        cursor = conn.cursor()
        data_db = movimento.data.isoformat() if movimento.data else datetime.now().strftime('%Y-%m-%d')
        
        # (CORRIGIDO) Query de inserção atualizada com todos os campos
        cursor.execute(
            """INSERT INTO poupanca (tipo, valor, data, tipo_investimento_id, taxa_mensal, prazo_meses) 
             VALUES (?, ?, ?, ?, ?, ?)""",
            (
                movimento.tipo, 
                movimento.valor, 
                data_db, 
                movimento.tipo_investimento_id,
                movimento.taxa_mensal,     # Salva a taxa
                movimento.prazo_meses      # Salva o prazo
            )
        )
        conn.commit()
        
        new_id = cursor.lastrowid
        cursor.execute("SELECT * FROM poupanca WHERE id = ?", (new_id,))
        novo_movimento_db = cursor.fetchone()

        if not novo_movimento_db:
            logging.error("Falha ao recuperar movimento após INSERT.")
            return None

        # (CORRIGIDO) Converte o dict do DB para o modelo Pydantic
        novo_movimento_dict = dict(novo_movimento_db)
        
        # (CORRIGIDO) Converte a data string de volta para date ANTES de passar ao Pydantic
        if novo_movimento_dict.get('data'):
              novo_movimento_dict['data'] = datetime.strptime(novo_movimento_dict['data'].split(' ')[0], '%Y-%m-%d').date()

        # Isso corrige o Pydantic Warning
        return PoupancaMovimentoRegistro(**novo_movimento_dict)

    except Exception as e:
        logging.error(f"Erro ao registar poupança: {e}", exc_info=True)
        conn.rollback()
        return None
    finally:
        if conn: conn.close()

# --- Funções de Tipos de Investimento (CORRIGIDAS) ---
def db_get_tipos_investimento() -> List[dict]:
    conn = get_db_conn()
    if not conn: return []
    try:
        cursor = conn.cursor()
        # (CORRIGIDO) Busca a coluna com o nome correto 'taxa_sugerida_mensal'
        cursor.execute("SELECT id, nome, taxa_sugerida_mensal FROM tipos_investimento ORDER BY nome")
        return [dict(row) for row in cursor.fetchall()]
    except Exception as e:
        logging.error(f"Erro ao buscar tipos de investimento: {e}", exc_info=True)
        return []
    finally:
        if conn: conn.close()

# -------------------------------------------------------------
# 3. FUNÇÕES DE RELATÓRIO QUE DEPENDEM DE OUTRAS FUNÇÕES DB
# -------------------------------------------------------------

def db_get_transacoes_recorrentes() -> Dict[str, List[Dict[str, Any]]]:
    """Busca todas as receitas e despesas recorrentes ativas."""
    conn = get_db_conn()
    if not conn: return {'receitas': [], 'despesas': []}
    
    recorrentes = {'receitas': [], 'despesas': []}
    
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM receitas WHERE recorrente = 1")
        recorrentes['receitas'] = [dict(row) for row in cursor.fetchall()]
        cursor.execute("SELECT * FROM despesas WHERE recorrente = 1")
        recorrentes['despesas'] = [dict(row) for row in cursor.fetchall()]
    except Exception as e:
        logging.error(f"Erro ao buscar transações recorrentes: {e}", exc_info=True)
    finally:
        if conn: conn.close()
        
    return recorrentes

def db_get_projecao_mensal_data(num_meses: int = 6, taxa_investimento: float = 0.005) -> List[Dict[str, Any]]:
    """
    Calcula a projeção do saldo para os próximos 'num_meses' com base no saldo real atual, 
    recorrências e transações futuras com data de vencimento.
    """
    saldo_atual_data = db_get_saldo_atual() 
    if not saldo_atual_data:
        logging.error("Não foi possível obter o saldo inicial para a projeção.")
        return []
        
    # Projeção começa do Saldo Real + Saldo de Investimentos
    saldo_inicial = saldo_atual_data['saldo_real_confirmado'] + saldo_atual_data['total_poupanca']
    
    recorrentes = db_get_transacoes_recorrentes()
    projecao = []
    
    data_inicio_projecao = date.today().replace(day=1) + timedelta(days=32)
    data_inicio_projecao = data_inicio_projecao.replace(day=1)
    
    saldo_projetado_acumulado = saldo_inicial
    
    conn = get_db_conn()
    if not conn: return []
    
    try:
        cursor = conn.cursor()
        
        for i in range(num_meses):
            mes_projecao = data_inicio_projecao + timedelta(days=i * 30)
            ano_projecao = mes_projecao.year
            mes_numero = mes_projecao.month
            
            total_receita_mes = 0.0
            total_despesa_mes = 0.0
            
            # 2. Transações Recorrentes
            for r in recorrentes['receitas']:
                total_receita_mes += r['valor']
                
            for d in recorrentes['despesas']:
                total_despesa_mes += d['valor']

            # 3. Transações Fixas (Não recorrentes, com Data de Vencimento no Mês)
            query_mes_str = f"{ano_projecao}-{mes_numero:02d}"
            
            cursor.execute(
                "SELECT SUM(valor) FROM receitas WHERE recorrente = 0 AND data_vencimento IS NOT NULL AND strftime('%Y-%m', data_vencimento) = ?",
                (query_mes_str,)
            )
            receitas_fixas_unicas = cursor.fetchone()[0] or 0.0
            total_receita_mes += receitas_fixas_unicas
            
            cursor.execute(
                "SELECT SUM(valor) FROM despesas WHERE recorrente = 0 AND data_vencimento IS NOT NULL AND strftime('%Y-%m', data_vencimento) = ?",
                (query_mes_str,)
            )
            despesas_fixas_unicas = cursor.fetchone()[0] or 0.0
            total_despesa_mes += despesas_fixas_unicas
            
            # 4. Evolução de Investimentos (Usa a taxa fornecida pelo cliente)
            
            # (CORREÇÃO LÓGICA) Só aplica rendimento se o saldo for positivo
            rendimento_projetado = 0.0
            if saldo_projetado_acumulado > 0:
                rendimento_projetado = saldo_projetado_acumulado * taxa_investimento
                
            total_receita_mes += rendimento_projetado

            # 5. Calcular o Novo Saldo
            saldo_projetado_mensal = total_receita_mes - total_despesa_mes
            saldo_projetado_acumulado += saldo_projetado_mensal
            
            projecao.append({
                "mes": mes_projecao.strftime("%Y-%m"),
                "saldo_inicial": round(saldo_projetado_acumulado - saldo_projetado_mensal, 2),
                "total_receita": round(total_receita_mes, 2),
                "total_despesa": round(total_despesa_mes, 2),
                "saldo_final_acumulado": round(saldo_projetado_acumulado, 2),
                "detalhes": f"Rend. Proj. R$ {round(rendimento_projetado, 2)}"
            })

    except Exception as e:
        logging.error(f"Erro ao calcular projeção mensal: {e}", exc_info=True)
        return []
    finally:
        if conn: conn.close()
        
    return projecao

def db_get_analise_despesas(ano: int, mes: int) -> Optional[dict]:
    conn = get_db_conn()
    if not conn: return None
    try:
        cursor = conn.cursor()
        query_mes_str = f"{ano}-{mes:02d}"

        cursor.execute("SELECT SUM(valor) FROM receitas WHERE strftime('%Y-%m', data) = ?", (query_mes_str,))
        total_receitas_mes = cursor.fetchone()[0] or 0.0

        cursor.execute("SELECT categoria, SUM(valor) as total FROM despesas WHERE strftime('%Y-%m', data) = ? GROUP BY categoria", (query_mes_str,))
        analise = []
        total_despesas_mes = 0.0
        for row in cursor.fetchall():
            categoria = dict(row)["categoria"] if dict(row)["categoria"] else "Sem Categoria"
            total_categoria = dict(row)["total"] or 0.0
            total_despesas_mes += total_categoria
            percentual = (total_categoria / total_receitas_mes * 100) if total_receitas_mes > 0 else 0.0
            analise.append({
                "categoria": categoria,
                "total": total_categoria,
                "percentual_da_receita": round(percentual, 2)
            })

        return {
            "analise_por_categoria": analise,
            "total_receitas": total_receitas_mes,
            "total_despesas": total_despesas_mes
        }
    except Exception as e:
        logging.error(f"Erro na análise de despesas para {mes}/{ano}: {e}", exc_info=True)
        return None
    finally:
        if conn: conn.close()


def db_get_dados_anual_ir(ano: int) -> List[dict]:
    conn = get_db_conn()
    if not conn: return []
    try:
        cursor = conn.cursor()
        ano_str = str(ano)

        cursor.execute("""
            SELECT 'Receita' as tipo, categoria, descricao, valor, data, pago
            FROM receitas
            WHERE strftime('%Y', data) = ?
            ORDER BY data ASC
        """, (ano_str,))
        receitas = [dict(row) for row in cursor.fetchall()]

        cursor.execute("""
            SELECT 'Despesa' as tipo, categoria, descricao, valor, data, pago
            FROM despesas
            WHERE strftime('%Y', data) = ?
            ORDER BY data ASC
        """, (ano_str,))
        despesas = [dict(row) for row in cursor.fetchall()]

        dados = receitas + despesas

        def get_date_obj(item):
            data_item = item.get('data')
            if isinstance(data_item, str):
                try:
                    return datetime.fromisoformat(data_item)
                except ValueError:
                    return datetime.min
            if isinstance(data_item, datetime):
                return data_item
            if isinstance(data_item, date):
                return datetime.combine(data_item, datetime.min.time())
            return datetime.min

        dados.sort(key=get_date_obj)
        return dados
    except Exception as e:
        logging.error(f"Erro ao gerar relatorio IR para {ano}: {e}", exc_info=True)
        return []
    finally:
        if conn: conn.close()

def db_listar_metas() -> List[dict]:
    conn = get_db_conn()
    if not conn: return []
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM metas ORDER BY criado_em DESC")
        return [dict(row) for row in cursor.fetchall()]
    except Exception as e:
        logging.error(f"Erro ao listar metas: {e}", exc_info=True)
        return []
    finally:
        if conn: conn.close()

def db_add_meta(meta: MetaCreate) -> Optional[dict]:
    conn = get_db_conn()
    if not conn: return None
    try:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO metas (nome, valor_alvo, valor_atual, data_limite, observacoes) VALUES (?, ?, ?, ?, ?)",
            (meta.nome.strip(), meta.valor_alvo, meta.valor_atual or 0, meta.data_limite, meta.observacoes)
        )
        conn.commit()
        new_id = cursor.lastrowid
        cursor.execute("SELECT * FROM metas WHERE id = ?", (new_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    except Exception as e:
        logging.error(f"Erro ao criar meta: {e}", exc_info=True)
        conn.rollback()
        return None
    finally:
        if conn: conn.close()

def db_update_meta(meta_id: int, meta_update: MetaUpdate) -> Optional[dict]:
    conn = get_db_conn()
    if not conn: return None
    campos = meta_update.model_dump(exclude_unset=True)
    if not campos:
        return next((m for m in db_listar_metas() if m["id"] == meta_id), None)
    try:
        set_clause = ", ".join([f"{key} = ?" for key in campos.keys()])
        valores = list(campos.values()) + [meta_id]
        cursor = conn.cursor()
        cursor.execute(f"UPDATE metas SET {set_clause} WHERE id = ?", valores)
        conn.commit()
        if cursor.rowcount == 0:
            return None
        cursor.execute("SELECT * FROM metas WHERE id = ?", (meta_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    except Exception as e:
        logging.error(f"Erro ao atualizar meta {meta_id}: {e}", exc_info=True)
        conn.rollback()
        return None
    finally:
        if conn: conn.close()

def db_delete_meta(meta_id: int) -> bool:
    conn = get_db_conn()
    if not conn: return False
    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM metas WHERE id = ?", (meta_id,))
        conn.commit()
        return cursor.rowcount > 0
    except Exception as e:
        logging.error(f"Erro ao deletar meta {meta_id}: {e}", exc_info=True)
        conn.rollback()
        return False
    finally:
        if conn: conn.close()

def criar_backup_db(motivo: str = "manual") -> Path:
    backup_dir = BASE_PATH / "backups"
    backup_dir.mkdir(exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    destino = backup_dir / f"budget_app_{motivo}_{stamp}.db"
    shutil.copy2(DB_PATH, destino)
    return destino

def listar_backups_db() -> List[dict]:
    backup_dir = BASE_PATH / "backups"
    if not backup_dir.exists():
        return []
    backups = []
    for arquivo in sorted(backup_dir.glob("budget_app_*.db"), key=lambda p: p.stat().st_mtime, reverse=True):
        backups.append({
            "nome": arquivo.name,
            "caminho": str(arquivo),
            "tamanho": arquivo.stat().st_size,
            "criado_em": datetime.fromtimestamp(arquivo.stat().st_mtime).isoformat(timespec="seconds")
        })
    return backups

def categorizar_importacao(descricao: str) -> str:
    texto = descricao.lower()
    regras = [
        ("mercado|supermercado|padaria|hortifruti", "Supermercado"),
        ("farmacia|drogaria|medico|hospital", "Saúde"),
        ("uber|99|posto|combustivel|metro|onibus", "Transporte"),
        ("netflix|spotify|cinema|restaurante|ifood", "Lazer"),
        ("salario|pix recebido|ted recebida|credito", "Renda Extra"),
        ("luz|energia", "Luz"),
        ("agua|saneamento", "Água"),
        ("internet|telefone|celular", "Internet"),
    ]
    for padrao, categoria in regras:
        if re.search(padrao, texto):
            return categoria
    return "Importado"

def parse_valor_importado(valor_raw: str) -> float:
    valor = str(valor_raw or "0").strip().replace("R$", "").replace(" ", "")
    if "," in valor and "." in valor:
        valor = valor.replace(".", "").replace(",", ".")
    else:
        valor = valor.replace(",", ".")
    return float(valor)

def parse_csv_extrato(conteudo: bytes) -> List[dict]:
    texto = conteudo.decode("utf-8-sig", errors="ignore")
    amostra = texto[:2048]
    dialect = csv.Sniffer().sniff(amostra, delimiters=";,")
    reader = csv.DictReader(io.StringIO(texto), dialect=dialect)
    itens = []
    for row in reader:
        normalizado = {str(k).strip().lower(): v for k, v in row.items() if k}
        data_raw = normalizado.get("data") or normalizado.get("date") or normalizado.get("dt")
        desc = normalizado.get("descricao") or normalizado.get("descrição") or normalizado.get("historico") or normalizado.get("histórico") or normalizado.get("memo")
        valor_raw = normalizado.get("valor") or normalizado.get("amount") or normalizado.get("vlr")
        if not data_raw or not desc or valor_raw is None:
            continue
        try:
            data_txt = str(data_raw).strip()
            if "/" in data_txt:
                data_obj = datetime.strptime(data_txt[:10], "%d/%m/%Y")
            else:
                data_obj = datetime.fromisoformat(data_txt[:10])
            valor = parse_valor_importado(valor_raw)
            itens.append({"data": data_obj, "descricao": str(desc).strip(), "valor": valor})
        except Exception:
            continue
    return itens

def parse_ofx_extrato(conteudo: bytes) -> List[dict]:
    texto = conteudo.decode("latin-1", errors="ignore")
    transacoes = re.findall(r"<STMTTRN>(.*?)(?=<STMTTRN>|</BANKTRANLIST>)", texto, flags=re.S | re.I)
    itens = []
    for bloco in transacoes:
        data_match = re.search(r"<DTPOSTED>([0-9]{8})", bloco, flags=re.I)
        valor_match = re.search(r"<TRNAMT>([-0-9.,]+)", bloco, flags=re.I)
        memo_match = re.search(r"<MEMO>([^\r\n<]+)", bloco, flags=re.I)
        name_match = re.search(r"<NAME>([^\r\n<]+)", bloco, flags=re.I)
        if not data_match or not valor_match:
            continue
        data_obj = datetime.strptime(data_match.group(1), "%Y%m%d")
        desc = (memo_match.group(1) if memo_match else name_match.group(1) if name_match else "Lancamento importado").strip()
        valor = parse_valor_importado(valor_match.group(1))
        itens.append({"data": data_obj, "descricao": desc, "valor": valor})
    return itens

def importar_lancamentos(itens: List[dict]) -> dict:
    conn = get_db_conn()
    if not conn: return {"importados": 0, "ignorados": 0}
    importados = 0
    ignorados = 0
    try:
        cursor = conn.cursor()
        for item in itens:
            tabela = "receitas" if item["valor"] >= 0 else "despesas"
            valor_abs = abs(float(item["valor"]))
            data_db = item["data"]
            descricao = item["descricao"][:180]
            categoria = categorizar_importacao(descricao)
            cursor.execute(
                f"SELECT id FROM {tabela} WHERE descricao = ? AND ABS(valor - ?) < 0.01 AND date(data) = date(?)",
                (descricao, valor_abs, data_db)
            )
            if cursor.fetchone():
                ignorados += 1
                continue
            cursor.execute(
                f"""INSERT INTO {tabela} (descricao, valor, data, pago, categoria, recorrente, data_vencimento)
                    VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (descricao, valor_abs, data_db, True, categoria, False, data_db.date())
            )
            importados += 1
        conn.commit()
        return {"importados": importados, "ignorados": ignorados}
    except Exception as e:
        logging.error(f"Erro ao importar lancamentos: {e}", exc_info=True)
        conn.rollback()
        return {"importados": importados, "ignorados": ignorados, "erro": str(e)}
    finally:
        if conn: conn.close()

def db_get_alertas(ano: int, mes: int) -> dict:
    conn = get_db_conn()
    if not conn: return {}
    try:
        cursor = conn.cursor()
        hoje = date.today()
        limite = hoje + timedelta(days=7)
        cursor.execute(
            "SELECT * FROM despesas WHERE pago = 0 AND data_vencimento IS NOT NULL AND date(data_vencimento) BETWEEN date(?) AND date(?) ORDER BY data_vencimento ASC",
            (hoje, limite)
        )
        vencendo = [dict(row) for row in cursor.fetchall()]
        cursor.execute("SELECT SUM(valor) FROM despesas WHERE pago = 0 AND data_vencimento IS NOT NULL AND strftime('%Y-%m', data_vencimento)=?", (f"{ano}-{mes:02d}",))
        total_a_vencer_mes = cursor.fetchone()[0] or 0
        cursor.execute("SELECT SUM(valor) FROM despesas WHERE pago = 1 AND strftime('%Y-%m', data)=?", (f"{ano}-{mes:02d}",))
        total_pago_mes = cursor.fetchone()[0] or 0
        cursor.execute("SELECT SUM(valor) FROM receitas WHERE pago = 1 AND strftime('%Y-%m', data)=?", (f"{ano}-{mes:02d}",))
        receitas_pagas_mes = cursor.fetchone()[0] or 0
        cursor.execute("SELECT categoria, SUM(valor) total FROM despesas WHERE strftime('%Y-%m', data)=? GROUP BY categoria ORDER BY total DESC LIMIT 1", (f"{ano}-{mes:02d}",))
        maior = cursor.fetchone()
        return {
            "contas_vencendo_7_dias": vencendo,
            "total_a_vencer_mes": total_a_vencer_mes,
            "total_pago_mes": total_pago_mes,
            "receitas_pagas_mes": receitas_pagas_mes,
            "sobra_prevista_mes": receitas_pagas_mes - total_pago_mes - total_a_vencer_mes,
            "maior_categoria": dict(maior) if maior else None,
        }
    except Exception as e:
        logging.error(f"Erro ao gerar alertas: {e}", exc_info=True)
        return {}
    finally:
        if conn: conn.close()

def gerar_relatorio_periodo_html(ano: int, tipo: str, mes: int | None = None, semestre: int | None = None) -> str:
    if tipo == "mensal":
        if mes is None or mes < 1 or mes > 12:
            raise ValueError("Mes invalido.")
        inicio, fim = f"{ano}-{mes:02d}-01", f"{ano}-{mes:02d}-{monthrange(ano, mes)[1]:02d}"
        titulo = f"Relatorio mensal - {mes:02d}/{ano}"
    elif tipo == "semestral":
        if semestre not in {1, 2}:
            raise ValueError("Semestre invalido.")
        inicio = f"{ano}-{'01' if semestre == 1 else '07'}-01"
        fim = f"{ano}-{'06-30' if semestre == 1 else '12-31'}"
        titulo = f"Relatorio semestral - {semestre}o semestre/{ano}"
    elif tipo == "anual":
        inicio, fim = f"{ano}-01-01", f"{ano}-12-31"
        titulo = f"Relatorio anual - {ano}"
    else:
        raise ValueError("Tipo de relatorio invalido.")

    conn = get_db_conn()
    if not conn:
        raise RuntimeError("Nao foi possivel acessar o banco de dados.")
    try:
        cursor = conn.cursor()
        transacoes = []
        for tabela, rotulo in [("receitas", "Receita"), ("despesas", "Despesa")]:
            cursor.execute(
                f"""SELECT descricao, valor, pago, categoria, data, data_vencimento
                    FROM {tabela}
                    WHERE date(COALESCE(data_vencimento, data)) BETWEEN date(?) AND date(?)
                    ORDER BY date(COALESCE(data_vencimento, data)), id""",
                (inicio, fim),
            )
            for row in cursor.fetchall():
                item = dict(row)
                item["tipo"] = rotulo
                transacoes.append(item)
    finally:
        conn.close()

    transacoes.sort(key=lambda item: item.get("data_vencimento") or item.get("data") or "")
    totais = {
        "receitas": sum(float(item["valor"]) for item in transacoes if item["tipo"] == "Receita"),
        "despesas": sum(float(item["valor"]) for item in transacoes if item["tipo"] == "Despesa"),
        "receitas_confirmadas": sum(float(item["valor"]) for item in transacoes if item["tipo"] == "Receita" and item["pago"]),
        "despesas_confirmadas": sum(float(item["valor"]) for item in transacoes if item["tipo"] == "Despesa" and item["pago"]),
    }
    categorias = {}
    for item in transacoes:
        if item["tipo"] == "Despesa":
            categoria = item.get("categoria") or "Sem categoria"
            categorias[categoria] = categorias.get(categoria, 0) + float(item["valor"])

    def moeda(valor: float) -> str:
        return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

    linhas = "".join(
        "<tr>"
        f"<td>{escape(str(item.get('data_vencimento') or item.get('data') or '-'))[:10]}</td>"
        f"<td>{item['tipo']}</td>"
        f"<td>{escape(str(item.get('descricao') or '-'))}</td>"
        f"<td>{escape(str(item.get('categoria') or 'Sem categoria'))}</td>"
        f"<td>{'Confirmado' if item.get('pago') else 'Pendente'}</td>"
        f"<td>{moeda(float(item['valor']))}</td>"
        "</tr>"
        for item in transacoes
    ) or "<tr><td colspan='6'>Nenhum lancamento neste periodo.</td></tr>"
    linhas_categorias = "".join(
        f"<tr><td>{escape(categoria)}</td><td>{moeda(total)}</td></tr>"
        for categoria, total in sorted(categorias.items(), key=lambda item: item[1], reverse=True)
    ) or "<tr><td colspan='2'>Nenhuma despesa neste periodo.</td></tr>"
    saldo_periodo = totais["receitas"] - totais["despesas"]

    return f"""<!doctype html><html><head><meta charset='utf-8'><title>{titulo}</title>
    <style>body{{font-family:Arial,sans-serif;margin:32px;color:#243041}}h1{{color:#2457c5}}table{{border-collapse:collapse;width:100%;margin-bottom:24px}}td,th{{border-bottom:1px solid #ddd;padding:8px;text-align:left}}.box{{background:#f4f6f8;padding:14px;margin:10px 0 22px;line-height:1.7}}button{{background:#2457c5;color:#fff;border:0;padding:10px 14px;border-radius:6px;font-weight:700;cursor:pointer}}@media print{{button{{display:none}}}}</style></head>
    <body><button onclick='history.back()'>Voltar ao painel</button> <button onclick='window.print()'>Imprimir ou salvar em PDF</button>
    <h1>App Orcamento Familiar - {titulo}</h1>
    <div class='box'><strong>Periodo:</strong> {inicio} a {fim}<br>
    <strong>Receitas:</strong> {moeda(totais['receitas'])} | <strong>Confirmadas:</strong> {moeda(totais['receitas_confirmadas'])}<br>
    <strong>Despesas:</strong> {moeda(totais['despesas'])} | <strong>Confirmadas:</strong> {moeda(totais['despesas_confirmadas'])}<br>
    <strong>Saldo do periodo:</strong> {moeda(saldo_periodo)}</div>
    <h2>Despesas por categoria</h2><table><tr><th>Categoria</th><th>Total</th></tr>{linhas_categorias}</table>
    <h2>Lancamentos do periodo</h2><table><tr><th>Data</th><th>Tipo</th><th>Descricao</th><th>Categoria</th><th>Status</th><th>Valor</th></tr>{linhas}</table>
    <p>Gerado em {datetime.now().strftime('%d/%m/%Y %H:%M')}.</p></body></html>"""

# ============================================================
# FastAPI Local (Servidor) - Refatorado para Exposição Global
# ============================================================
TEMPLATES_DIR = BASE_PATH / "templates"
STATIC_DIR = BASE_PATH / "static"
FAVICON_PATH = BASE_PATH / "favicon.ico"

def create_fastapi_app() -> FastAPI:
    """Cria e configura a instância do FastAPI com todas as rotas."""
    
    app_fastapi_server = FastAPI(title="Orçamento Familiar - Painel Local")

    app_fastapi_server.add_middleware(
        CORSMiddleware,
        allow_origins=["null", "http://127.0.0.1:8000", "file://"], # Adicionado file:// para testes locais
        allow_credentials=True,
        allow_methods=["*"], 
        allow_headers=["*"],
    )

    STATIC_PATH_ABSOLUTO = BASE_PATH / "static"
    
    if STATIC_PATH_ABSOLUTO.exists():
        logging.info(f"PROCESSO SERVIDOR: Montando diretório estático em: {STATIC_PATH_ABSOLUTO}")
        app_fastapi_server.mount("/static", StaticFiles(directory=str(STATIC_PATH_ABSOLUTO)), name="static")
    else:
        logging.warning(f"PROCESSO SERVIDOR: Diretório estático NÃO encontrado em {STATIC_PATH_ABSOLUTO}")

    api_router = APIRouter()

    # --- Rota Principal para Servir o Painel ---
    @app_fastapi_server.get("/", response_class=FileResponse)
    async def serve_painel():
        painel_path = BASE_PATH / "painel.html" # Assumindo que o painel.html está na raiz
        if not painel_path.exists():
             painel_path = TEMPLATES_DIR / "painel.html" # Tenta no /templates
             if not painel_path.exists():
                 return HTMLResponse("<h1>Erro 500: painel.html não encontrado.</h1>", status_code=500)
        return FileResponse(painel_path)

    # --- Rota do Favicon ---
    @app_fastapi_server.get("/favicon.ico", include_in_schema=False)
    async def favicon():
        if FAVICON_PATH.exists(): return FileResponse(FAVICON_PATH)
        else: return Response(status_code=204)

    # --- Rotas API (Transações, Poupança, Relatórios) ---
    # (As rotas completas que você enviou estão aqui)
    
    # --- (CORRIGIDO) Rota GET /api/receitas ---
    @api_router.get("/receitas", response_model=List[Transacao])
    async def get_receitas():
        logging.info("API: GET /api/receitas")
        receitas_db = db_get_receitas()
        for r in receitas_db: 
            if isinstance(r.get('data'), (datetime, date)): r['data'] = r['data'].isoformat()
            if isinstance(r.get('data_vencimento'), date): r['data_vencimento'] = r['data_vencimento'].isoformat()
        return receitas_db

    @api_router.get("/receitas/{item_id}", response_model=Transacao)
    async def get_receita(item_id: int):
        logging.info(f"API: GET /api/receitas/{item_id}")
        receita_db = db_get_receita_by_id(item_id)
        if receita_db is None: raise HTTPException(status_code=404, detail="Receita não encontrada.")
        if isinstance(receita_db.get('data'), (datetime, date)): receita_db['data'] = receita_db['data'].isoformat()
        if isinstance(receita_db.get('data_vencimento'), date): receita_db['data_vencimento'] = receita_db['data_vencimento'].isoformat()
        return receita_db

    @api_router.post("/receitas", response_model=Transacao, status_code=201)
    async def add_receita(receita: TransacaoCreate):
        logging.info(f"API: POST /api/receitas - {receita.model_dump(exclude_unset=True)}")
        nova_receita = db_add_receita(receita)
        if nova_receita is None: raise HTTPException(status_code=500, detail="Erro ao adicionar receita.")
        if isinstance(nova_receita.get('data'), (datetime, date)): nova_receita['data'] = nova_receita['data'].isoformat()
        if isinstance(nova_receita.get('data_vencimento'), date): nova_receita['data_vencimento'] = nova_receita['data_vencimento'].isoformat()
        return nova_receita

    @api_router.put("/receitas/{item_id}", response_model=Transacao)
    async def update_receita(item_id: int, receita_update: TransacaoUpdate):
        logging.info(f"API: PUT /api/receitas/{item_id} - {receita_update.model_dump(exclude_unset=True)}")
        updated_receita = db_update_receita(item_id, receita_update)
        if updated_receita is None: raise HTTPException(status_code=404, detail="Receita não encontrada ou erro ao atualizar.")
        if isinstance(updated_receita.get('data'), (datetime, date)): updated_receita['data'] = updated_receita['data'].isoformat()
        if isinstance(updated_receita.get('data_vencimento'), date): updated_receita['data_vencimento'] = updated_receita['data_vencimento'].isoformat()
        return updated_receita

    @api_router.delete("/receitas/{item_id}", status_code=200, response_model=Dict[str, str])
    async def delete_receita(item_id: int = FastApiPath(..., title="ID da receita a deletar")):
        logging.info(f"API: DELETE /api/receitas/{item_id}")
        success = db_delete_receita(item_id)
        if not success: raise HTTPException(status_code=404, detail="Receita não encontrada ou erro ao deletar.")
        return JSONResponse(content={"status": "success"}, status_code=200)

    # --- Rotas de Despesas (Sem mudanças) ---
    @api_router.get("/despesas", response_model=List[Transacao])
    async def get_despesas():
        logging.info("API: GET /api/despesas")
        despesas_db = db_get_despesas()
        for d in despesas_db:
            if isinstance(d.get('data'), (datetime, date)): d['data'] = d['data'].isoformat()
            if isinstance(d.get('data_vencimento'), date): d['data_vencimento'] = d['data_vencimento'].isoformat()
        return despesas_db

    @api_router.get("/despesas/{item_id}", response_model=Transacao)
    async def get_despesa(item_id: int):
        logging.info(f"API: GET /api/despesas/{item_id}")
        despesa_db = db_get_despesa_by_id(item_id)
        if despesa_db is None: raise HTTPException(status_code=404, detail="Despesa não encontrada.")
        if isinstance(despesa_db.get('data'), (datetime, date)): despesa_db['data'] = despesa_db['data'].isoformat()
        if isinstance(despesa_db.get('data_vencimento'), date): despesa_db['data_vencimento'] = despesa_db['data_vencimento'].isoformat()
        return despesa_db

    @api_router.post("/despesas", response_model=Transacao, status_code=201)
    async def add_despesa(despesa: TransacaoCreate):
        logging.info(f"API: POST /api/despesas - {despesa.model_dump(exclude_unset=True)}")
        nova_despesa = db_add_despesa(despesa)
        if nova_despesa is None: raise HTTPException(status_code=500, detail="Erro ao adicionar despesa.")
        if isinstance(nova_despesa.get('data'), (datetime, date)): nova_despesa['data'] = nova_despesa['data'].isoformat()
        if isinstance(nova_despesa.get('data_vencimento'), date): nova_despesa['data_vencimento'] = nova_despesa['data_vencimento'].isoformat()
        return nova_despesa

    @api_router.put("/despesas/{item_id}", response_model=Transacao)
    async def update_despesa(item_id: int, despesa_update: TransacaoUpdate):
        logging.info(f"API: PUT /api/despesas/{item_id} - {despesa_update.model_dump(exclude_unset=True)}")
        updated_despesa = db_update_despesa(item_id, despesa_update)
        if updated_despesa is None: raise HTTPException(status_code=404, detail="Despesa não encontrada ou erro ao atualizar.")
        if isinstance(updated_despesa.get('data'), (datetime, date)): updated_despesa['data'] = updated_despesa['data'].isoformat()
        if isinstance(updated_despesa.get('data_vencimento'), date): updated_despesa['data_vencimento'] = updated_despesa['data_vencimento'].isoformat()
        return updated_despesa

    @api_router.delete("/despesas/{item_id}", status_code=200, response_model=Dict[str, str])
    async def delete_despesa(item_id: int = FastApiPath(..., title="ID da despesa a deletar")):
        logging.info(f"API: DELETE /api/despesas/{item_id}")
        success = db_delete_despesa(item_id)
        if not success: raise HTTPException(status_code=404, detail="Despesa não encontrada ou erro ao deletar.")
        return JSONResponse(content={"status": "success"}, status_code=200)

    @api_router.patch("/transacoes/{tipo}/{item_id}/toggle-pago", response_model=Dict[str, str])
    async def toggle_pago(
        tipo: str = FastApiPath(..., description="'receita' ou 'despesa'"),
        item_id: int = FastApiPath(..., title="ID da transação")
    ):
        logging.info(f"API: PATCH /api/transacoes/{tipo}/{item_id}/toggle-pago")
        if tipo not in ["receita", "despesa"]: raise HTTPException(status_code=400, detail="Tipo inválido.")
        success = db_toggle_pago(tipo, item_id)
        if not success: raise HTTPException(status_code=404, detail="Transação não encontrada ou erro.")
        return {"status": "success"}

    # --- (ATUALIZADO) Rota de Poupança/Investimento ---
    @api_router.post("/poupanca", response_model=PoupancaMovimentoRegistro, status_code=201)
    async def add_poupanca(movimento: PoupancaMovimento):
        logging.info(f"API: POST /api/poupanca - {movimento.model_dump()}")
        
        # (Req 7) Validação
        if movimento.tipo == 'deposito' and (movimento.taxa_mensal is None or movimento.prazo_meses is None):
            raise HTTPException(status_code=422, detail="Depósitos exigem 'taxa_mensal' e 'prazo_meses'.")

        # 1. Registra o movimento na tabela 'poupanca'
        novo_movimento = db_add_poupanca(movimento)
        if novo_movimento is None: 
            raise HTTPException(status_code=500, detail="Erro ao registar movimento de poupança.")

        # 2. (NOVO) Se for 'transferência', cria a transação oposta no Saldo Real
        if movimento.transferir_saldo:
            try:
                if movimento.tipo == 'deposito':
                    # Cria uma DESPESA automática
                    despesa = TransacaoCreate(
                        descricao=f"Aporte Investimento (ID: {novo_movimento.id})",
                        valor=movimento.valor,
                        categoria="Investimento",
                        pago=True # Transferências são sempre 'pagas'
                    )
                    db_add_despesa(despesa)
                    logging.info("Transferência (Despesa) criada com sucesso.")
                
                elif movimento.tipo == 'retirada':
                    # Cria uma RECEITA automática
                    receita = TransacaoCreate(
                        descricao=f"Resgate Investimento (ID: {novo_movimento.id})",
                        valor=movimento.valor,
                        categoria="Investimento",
                        pago=True # Transferências são sempre 'pagas'
                    )
                    db_add_receita(receita)
                    logging.info("Transferência (Receita) criada com sucesso.")
                
            except Exception as e:
                # Se a transação principal (poupanca) funcionou mas a transferência falhou,
                # não falha a requisição, mas loga o erro.
                logging.error(f"ERRO CRÍTICO: Movimento de poupança {novo_movimento.id} registrado, mas a transferência de saldo falhou: {e}")
                # Opcional: Você poderia tentar deletar o movimento de poupança aqui para 'reverter'

        # Garante que a data seja formatada corretamente para o retorno JSON
        # (O Pydantic V2 deve lidar com isso, mas garantindo)
        if isinstance(novo_movimento.data, date):
            novo_movimento.data = novo_movimento.data.isoformat()
            
        return novo_movimento

    # (CORRIGIDO) ROTA DE TIPOS DE INVESTIMENTO
    @api_router.get("/tipos_investimento", response_model=List[TipoInvestimentoRegistro])
    async def get_tipos_investimento():
        logging.info("API: GET /api/tipos_investimento")
        # (CORRIGIDO) Chama a função correta
        tipos = db_get_tipos_investimento()
        return tipos

    # --- Rotas de Relatórios ---
    @api_router.get("/relatorio/saldo_atual", response_model=SaldoAtual)
    async def get_saldo_atual():
        logging.info("API: GET /api/relatorio/saldo_atual")
        saldo = db_get_saldo_atual()
        if saldo is None: raise HTTPException(status_code=500, detail="Erro ao calcular saldo.")
        return saldo

    @api_router.get("/licenca/status", response_model=Dict[str, Any])
    async def get_status_licenca():
        status = verificar_licenca_local()
        payload = status.get("payload") or {}
        return {
            "valido": bool(status.get("valido")),
            "mensagem": status.get("mensagem", ""),
            "dias_restantes": status.get("dias_restantes"),
            "cliente_nome": payload.get("cliente_nome", ""),
            "cliente_email": payload.get("cliente_email", ""),
            "tipo_licenca": payload.get("tipo_licenca", ""),
            "implantado_em": payload.get("implantado_em", ""),
            "expira_em": payload.get("expira_em", ""),
        }

    @api_router.get("/relatorio/analise_despesas", response_model=AnaliseDespesas)
    async def get_analise_despesas(
        ano: int = Query(..., description="Ano"),
        mes: int = Query(..., ge=1, le=12, description="Mês")
    ):
        logging.info(f"API: GET /api/relatorio/analise_despesas?ano={ano}&mes={mes}")
        analise = db_get_analise_despesas(ano, mes)
        if analise is None: raise HTTPException(status_code=500, detail="Erro ao gerar análise.")
        return analise

    @api_router.get("/relatorio/projecao_mensal", response_model=List[Dict[str, Any]])
    async def get_projecao_mensal(
        num_meses: int = Query(6, ge=1, le=12, description="Número de meses para projetar"),
        taxa_investimento: float = Query(0.005, description="Taxa de rendimento mensal (Ex: 0.008 para 0.8%)") 
    ):
        logging.info(f"API: GET /api/relatorio/projecao_mensal?num_meses={num_meses}&taxa={taxa_investimento}")
        projecao = db_get_projecao_mensal_data(num_meses, taxa_investimento)
        if not projecao: raise HTTPException(status_code=500, detail="Erro ao gerar projeção.")
        return projecao

    @api_router.get("/relatorio/exportar_ir")
    async def exportar_ir(ano: int = Query(..., ge=2000, le=2100, description="Ano base")):
        logging.info(f"API: GET /api/relatorio/exportar_ir?ano={ano}")
        dados = db_get_dados_anual_ir(ano)

        output = io.StringIO()
        writer = csv.writer(output, delimiter=';', quoting=csv.QUOTE_MINIMAL)
        writer.writerow(['Data', 'Tipo', 'Categoria', 'Descricao', 'Valor', 'Status'])

        total_receitas = 0.0
        total_despesas = 0.0

        for item in dados:
            data_iso = item.get('data')
            data_fmt = ""
            if isinstance(data_iso, str):
                try:
                    data_fmt = datetime.fromisoformat(data_iso).strftime('%d/%m/%Y')
                except ValueError:
                    data_fmt = data_iso[:10]
            elif isinstance(data_iso, (datetime, date)):
                data_fmt = data_iso.strftime('%d/%m/%Y')

            valor = float(item.get('valor') or 0)
            status = "Confirmado" if item.get('pago') else "Pendente"
            writer.writerow([
                data_fmt,
                item.get('tipo', ''),
                item.get('categoria') or "Sem Categoria",
                item.get('descricao') or "",
                f"{valor:.2f}".replace('.', ','),
                status
            ])

            if item.get('tipo') == 'Receita':
                total_receitas += valor
            else:
                total_despesas += valor

        writer.writerow([])
        writer.writerow(['', '', '', 'TOTAL RECEITAS', f"{total_receitas:.2f}".replace('.', ','), ''])
        writer.writerow(['', '', '', 'TOTAL DESPESAS', f"{total_despesas:.2f}".replace('.', ','), ''])
        writer.writerow(['', '', '', 'SALDO ANUAL', f"{(total_receitas - total_despesas):.2f}".replace('.', ','), ''])

        response = Response(content=output.getvalue().encode('utf-8-sig'), media_type="text/csv")
        response.headers["Content-Disposition"] = f"attachment; filename=Relatorio_IR_{ano}.csv"
        return response

    @api_router.get("/dashboard/alertas", response_model=Dict[str, Any])
    async def get_dashboard_alertas(
        ano: int = Query(..., description="Ano"),
        mes: int = Query(..., ge=1, le=12, description="Mes")
    ):
        return db_get_alertas(ano, mes)

    @api_router.get("/relatorio/mensal")
    async def exportar_relatorio_mensal(
        ano: int = Query(..., ge=2000, le=2100),
        mes: int = Query(..., ge=1, le=12)
    ):
        html = gerar_relatorio_periodo_html(ano, "mensal", mes=mes)
        response = Response(content=html.encode("utf-8"), media_type="text/html")
        response.headers["Content-Disposition"] = f"attachment; filename=Relatorio_Mensal_{ano}_{mes:02d}.html"
        return response

    @api_router.get("/relatorio/periodo")
    async def exportar_relatorio_periodo(
        ano: int = Query(..., ge=2000, le=2100),
        tipo: Literal["mensal", "semestral", "anual"] = Query(...),
        mes: Optional[int] = Query(None, ge=1, le=12),
        semestre: Optional[int] = Query(None, ge=1, le=2),
    ):
        try:
            html = gerar_relatorio_periodo_html(ano, tipo, mes=mes, semestre=semestre)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return HTMLResponse(content=html)

    @api_router.post("/backup/criar", response_model=Dict[str, Any])
    async def criar_backup():
        caminho = criar_backup_db("manual")
        return {"status": "success", "caminho": str(caminho), "nome": caminho.name}

    @api_router.get("/backup/listar", response_model=List[Dict[str, Any]])
    async def listar_backups():
        return listar_backups_db()

    @api_router.get("/metas", response_model=List[Dict[str, Any]])
    async def listar_metas():
        return db_listar_metas()

    @api_router.post("/metas", response_model=Dict[str, Any], status_code=201)
    async def criar_meta(meta: MetaCreate):
        nova = db_add_meta(meta)
        if not nova:
            raise HTTPException(status_code=500, detail="Erro ao criar meta.")
        return nova

    @api_router.put("/metas/{meta_id}", response_model=Dict[str, Any])
    async def atualizar_meta(meta_id: int, meta_update: MetaUpdate):
        meta = db_update_meta(meta_id, meta_update)
        if not meta:
            raise HTTPException(status_code=404, detail="Meta nao encontrada.")
        return meta

    @api_router.delete("/metas/{meta_id}", response_model=Dict[str, str])
    async def deletar_meta(meta_id: int):
        if not db_delete_meta(meta_id):
            raise HTTPException(status_code=404, detail="Meta nao encontrada.")
        return {"status": "success"}

    @api_router.post("/importar/extrato", response_model=Dict[str, Any])
    async def importar_extrato(arquivo: UploadFile = File(...)):
        nome = arquivo.filename or ""
        conteudo = await arquivo.read()
        if nome.lower().endswith(".ofx"):
            itens = parse_ofx_extrato(conteudo)
        elif nome.lower().endswith(".csv"):
            itens = parse_csv_extrato(conteudo)
        else:
            raise HTTPException(status_code=400, detail="Formato nao suportado. Use OFX ou CSV.")
        resultado = importar_lancamentos(itens)
        resultado["lidos"] = len(itens)
        return resultado

    app_fastapi_server.include_router(api_router, prefix="/api")

    return app_fastapi_server

# ============================================================
# EXPOSIÇÃO GLOBAL PARA UVICORN (SOLUÇÃO DO ERRO)
# ============================================================
try:
    # A instância é criada no MainProcess para ser acessível pelo Uvicorn
    app = create_fastapi_app() 
except Exception as e:
    logging.error(f"Falha ao criar a instância FastAPI (app global): {e}", exc_info=True)
    # Define app como None para que a interface possa exibir a mensagem de erro
    app = None 


def start_server_process(log_path, port):
    """Função alvo para o processo do servidor (Executa uvicorn.run)."""
    global app 
    # Configura o logging novamente no processo filho
    setup_logging(log_path) 
    if app is None:
        logging.error("PROCESSO SERVIDOR: Não foi possível iniciar Uvicorn pois 'app' é None.")
        sys.exit(1)
        
    logging.info(f"PROCESSO SERVIDOR: Tentando iniciar Uvicorn em 127.0.0.1:{port}...")
    try:
        # Passa o objeto app, não a string
        uvicorn.run(app, host="127.0.0.1", port=port, log_level="info", reload=False, log_config=None)
        logging.info("PROCESSO SERVIDOR: Uvicorn encerrado.")
    except Exception as e:
        logging.error(f"!!! ERRO FATAL NO PROCESSO DO SERVIDOR !!!: {e}", exc_info=True)
        sys.exit(1)


# ============================================================
# Interface Gráfica (PyQt6) - Processo Principal
# ============================================================
class CustomWebEnginePage(QWebEnginePage):
    # Desativa menu de contexto
    def contextMenuEvent(self, event): pass

class MainWindow(QMainWindow):
    def __init__(self, server_process, server_port):
        super().__init__()
        self.server_process = server_process
        self.server_port = server_port
        self.setWindowTitle("Orçamento Familiar - Painel Pessoal")
        self.setGeometry(100, 100, 1300, 800)
        logging.info("Verificando favicon...");
        if FAVICON_PATH.exists(): self.setWindowIcon(QIcon(str(FAVICON_PATH))); logging.info("Favicon carregado.")
        else: logging.warning(f"Favicon não encontrado: {FAVICON_PATH}")
        self.browser = QWebEngineView()
        self.browser.setPage(CustomWebEnginePage(self.browser))
        
        # Timer para esperar o servidor iniciar
        self.retry_timer = QTimer(self)
        self.retry_timer.timeout.connect(self.load_url)
        self.retry_count = 0
        
        self.load_url()
        self.setCentralWidget(self.browser)

    def load_url(self):
        logging.info(f"Tentando carregar URL ({self.retry_count + 1})...")
        if self.server_process and not self.server_process.is_alive() and self.retry_count > 0:
            logging.error("Processo servidor morreu."); self.retry_timer.stop()
            QMessageBox.critical(self, "Erro Crítico", "Servidor falhou.\nConsulte app_log.txt."); QApplication.quit(); os._exit(1); return
        self.browser.setUrl(QUrl(f"http://127.0.0.1:{self.server_port}"))
        self.retry_count += 1
        # Tenta carregar 10 vezes (5 segundos)
        if self.retry_count < 10: self.retry_timer.start(500)
        else:
            logging.warning("Máximo de tentativas atingido.")
            if self.server_process and not self.server_process.is_alive():
                QMessageBox.critical(self, "Erro Crítico", "Não foi possível conectar.\nConsulte app_log.txt."); QApplication.quit(); os._exit(1)
        if self.retry_count == 1: self.browser.loadFinished.connect(self.on_load_finished)

    def on_load_finished(self, ok):
        if ok: 
            logging.info("Página carregada!")
            self.retry_timer.stop()
        else: 
            logging.warning("Falha ao carregar página.")

    def closeEvent(self, event):
        logging.info("Evento 'close'.");
        if self.server_process and self.server_process.is_alive():
            logging.info("Encerrando processo servidor..."); 
            self.server_process.terminate(); 
            self.server_process.join(timeout=1)
            if self.server_process.is_alive(): 
                logging.warning("Forçando kill..."); 
                self.server_process.kill()
            logging.info("Processo servidor encerrado.")
        QApplication.quit(); os._exit(0)

# ============================================================
# Bloco Principal (__main__)
# ============================================================
if __name__ == "__main__":
    multiprocessing.freeze_support()
    server_p = None
    try:
        setup_logging(LOG_FILE_PATH)
        
        # 1. Validação da licença (AGORA ILIMITADA)
        status_licenca = verificar_licenca_local()
        # A verificação abaixo NUNCA falhará, pois a função retorna True
        if not status_licenca["valido"]:
            # ESTE BLOCO NUNCA SERÁ EXECUTADO EM MODO PESSOAL
            logging.error(f"Licença inválida: {status_licenca['mensagem']}")
            try:
                app_qt_err = QApplication(sys.argv)
                mb = QMessageBox(QMessageBox.Icon.Critical, "Licença Inválida", status_licenca["mensagem"] + "\n\nContacte o suporte.")
                mb.exec()
            except Exception as e:
                logging.error(f"Não mostrou QMessageBox: {e}")
            sys.exit(1)
        
        logging.info("Licença OK.")
        
        # 2. Criação BD (Apenas verifica a conexão)
        try:
            criar_banco()

        except Exception as e:
            logging.error(f"Erro fatal BD: {e}", exc_info=True)
            try:
                app_qt_err = QApplication(sys.argv)
                mb = QMessageBox(QMessageBox.Icon.Critical, "Erro Crítico BD", f"Não foi possível acessar a BD.\nErro: {e}\n\nConsulte app_log.txt.")
                mb.exec()
            except Exception as e2:
                logging.error(f"Não mostrou QMessageBox: {e2}")
            sys.exit(1)
            
        
        # 3. Inicia servidor 
        server_port = encontrar_porta_livre()
        logging.info(f"Iniciando processo servidor na porta {server_port}...")
        # O Uvicorn roda em outro processo para não bloquear a UI (PyQt)
        server_p = multiprocessing.Process(target=start_server_process, args=(LOG_FILE_PATH, server_port), name="ServidorUvicorn")
        server_p.daemon = True
        server_p.start()
        logging.info(f"Processo servidor PID: {server_p.pid}")
        
        # 4. Inicia UI
        logging.info("Iniciando QApplication...")
        app_qt = QApplication(sys.argv)
        os.environ["QTWEBENGINE_DISABLE_SANDBOX"] = "1"
        logging.info("Criando MainWindow...")
        window = MainWindow(server_p, server_port)
        logging.info("Exibindo MainWindow...")
        window.show()
        exit_code = app_qt.exec()
        logging.info(f"QApplication finalizado: {exit_code}")
        sys.exit(exit_code)
        
    except Exception as e:
        logging.error(f"!!! ERRO FATAL (MAIN) !!!: {e}", exc_info=True)
        try:
            app_qt_err = QApplication.instance()
            if app_qt_err is None:
                app_qt_err = QApplication(sys.argv)
            mb = QMessageBox(QMessageBox.Icon.Critical, "Erro Crítico", f"Erro fatal.\nErro: {e}\n\nConsulte app_log.txt.")
            mb.exec()
        except Exception as e2:
            logging.error(f"Não mostrou QMessageBox final: {e2}")
        sys.exit(1)
        
    finally:
        if server_p and server_p.is_alive():
            logging.info("Encerrando processo servidor (finally)...")
            server_p.terminate()
            server_p.join(timeout=1)
            if server_p.is_alive():
                server_p.kill()

