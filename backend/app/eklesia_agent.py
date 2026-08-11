import httpx
import os
import json
from datetime import datetime, date


EKLESIA_BASE = "https://gestaoweb.eklesiaonline.com.br/webapi/api"
EKLESIA_EMAIL = os.getenv("EKLESIA_EMAIL", "Claudiova2023@gmail.com")
EKLESIA_PASSWORD = os.getenv("EKLESIA_PASSWORD", "c1t2d3s4")


async def eklesia_login() -> str:
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{EKLESIA_BASE}/Token/Autenticar",
            json={"nome": EKLESIA_EMAIL, "password": EKLESIA_PASSWORD},
            timeout=15.0,
        )
        resp.raise_for_status()
        basic_token = resp.json()["token"]

        resp2 = await client.get(
            f"{EKLESIA_BASE}/Token/Autorizar?manterLogado=false",
            headers={"Authorization": f"Bearer {basic_token}"},
            timeout=15.0,
        )
        resp2.raise_for_status()
        return resp2.json()["token"]


def eklesia_headers(token: str) -> dict:
    return {
        "Authorization": f"Bearer {token}",
        "eks-igreja-selecionada": "1",
        "accept": "application/json",
    }


async def eklesia_get_commitment_time(token: str, turma_id: int, grade_id: int, target_date: str) -> str:
    """Get the commitment start time for a specific date from Eklesia grade schedule."""
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{EKLESIA_BASE}/ensino/EnsinoAgenda/ObterCompromissosDaGrade",
            params={
                "codTurma": turma_id,
                "codGrade": grade_id,
                "dataInicial": target_date,
                "dataFinal": target_date,
            },
            headers=eklesia_headers(token),
            timeout=15.0,
        )
        resp.raise_for_status()
        commitments = resp.json()
        if commitments:
            return commitments[0].get("inicio", f"{target_date}T00:00:00")
        return f"{target_date}T00:00:00"


async def eklesia_get_presences(token: str, turma_id: int, grade_id: int) -> list:
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{EKLESIA_BASE}/ensino/EnsinoTurmaAlunoGradePresenca/ObterTodos",
            headers=eklesia_headers(token),
            timeout=30.0,
        )
        resp.raise_for_status()
        all_data = resp.json()
        return [
            d for d in all_data
            if d.get("codEnsinoTurma") == turma_id
            and d.get("codEnsinoCursoGrade") == grade_id
        ]


async def eklesia_salvar_presenca(
    token: str,
    turma_id: int,
    grade_id: int,
    pessoas: list,
    pessoas_atuais_ids: list,
    data: str,
) -> dict:
    payload = {
        "pessoasAtuais": pessoas_atuais_ids,
        "pessoas": pessoas,
        "codEnsinoCursoGrade": grade_id,
        "codEnsinoTurma": turma_id,
        "data": data,
    }
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{EKLESIA_BASE}/ensino/EnsinoTurmaAlunoGradePresenca/Salvar",
            json=payload,
            headers=eklesia_headers(token),
            timeout=15.0,
        )
        resp.raise_for_status()
        return resp.json()


async def sync_attendance_to_eklesia(
    turma_id: int,
    grade_id: int,
    present_students: list[dict],
) -> dict:
    """
    present_students: list of {"codPessoa": int, "codEnsinoTurmaAluno": int}
    """
    token = await eklesia_login()
    today = date.today().isoformat()

    commitment_time = await eklesia_get_commitment_time(token, turma_id, grade_id, today)

    existing = await eklesia_get_presences(token, turma_id, grade_id)
    pessoas_atuais_ids = [d["codigo"] for d in existing]

    result = await eklesia_salvar_presenca(
        token=token,
        turma_id=turma_id,
        grade_id=grade_id,
        pessoas=present_students,
        pessoas_atuais_ids=pessoas_atuais_ids,
        data=commitment_time,
    )
    return result


async def eklesia_get_students(turma_id: int) -> list:
    token = await eklesia_login()
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{EKLESIA_BASE}/ensino/EnsinoTurmaAluno/ObterAlunosPresenca",
            params={
                "codigoEnsinoTurma": turma_id,
                "dataPresenca": f"{date.today().isoformat()}T00:00:00",
                "skip": 0,
                "limit": 500,
                "searchTerm": "",
                "searchableColumns": "CodPessoa",
                "searchableColumns": "Nome",
            },
            headers=eklesia_headers(token),
            timeout=30.0,
        )
        resp.raise_for_status()
        data = resp.json()
        return data.get("linhas", [])
