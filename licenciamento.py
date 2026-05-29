import json
import os
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from itsdangerous import BadSignature, TimestampSigner


SECRET_KEY_LICENCA = os.getenv("SECRET_KEY_LICENCA", "segredo-padrao-orcamento-familiar-2025")
signer_licenca = TimestampSigner(SECRET_KEY_LICENCA)


def gerar_licenca(
    nome: str,
    email: str,
    tipo: str,
    dias_validade: int,
    implantado_em: Optional[str] = None,
) -> tuple[str, dict]:
    criado_em = datetime.now()
    if implantado_em:
        data_base = datetime.fromisoformat(implantado_em)
    else:
        data_base = criado_em

    expira_em = data_base + timedelta(days=dias_validade)
    payload = {
        "licenca_id": str(uuid.uuid4()),
        "cliente_nome": nome.strip(),
        "cliente_email": email.strip().lower(),
        "tipo_licenca": tipo.strip().upper(),
        "data_criacao": criado_em.isoformat(timespec="seconds"),
        "implantado_em": data_base.isoformat(timespec="seconds"),
        "expira_em": expira_em.isoformat(timespec="seconds"),
        "dias_validade": dias_validade,
        "produto": "OrcamentoApp",
        "versao_licenca": 2,
    }
    conteudo = signer_licenca.sign(json.dumps(payload, ensure_ascii=False).encode("utf-8")).decode("utf-8")
    return conteudo, payload


def ler_payload_licenca(conteudo: str) -> dict:
    payload_bytes = signer_licenca.unsign(conteudo)
    return json.loads(payload_bytes.decode("utf-8"))


def verificar_licenca_arquivo(base_path: Path) -> dict:
    caminho_licenca = Path(base_path) / "license.key"
    if not caminho_licenca.exists():
        return {"valido": False, "mensagem": "Licenca nao encontrada. Solicite uma licenca valida."}

    try:
        payload = ler_payload_licenca(caminho_licenca.read_text(encoding="utf-8").strip())
        expira_em = datetime.fromisoformat(payload["expira_em"])
        agora = datetime.now()
        dias_restantes = (expira_em.date() - agora.date()).days
        if agora > expira_em:
            return {
                "valido": False,
                "mensagem": f"Licenca expirada em {expira_em.strftime('%d/%m/%Y')}. Solicite renovacao.",
                "payload": payload,
            }

        tipo = payload.get("tipo_licenca", "LICENCA")
        return {
            "valido": True,
            "mensagem": f"{tipo} valido ate {expira_em.strftime('%d/%m/%Y')} ({dias_restantes} dias restantes).",
            "payload": payload,
            "dias_restantes": dias_restantes,
        }
    except (BadSignature, KeyError, ValueError, json.JSONDecodeError):
        return {"valido": False, "mensagem": "Licenca invalida ou corrompida."}
