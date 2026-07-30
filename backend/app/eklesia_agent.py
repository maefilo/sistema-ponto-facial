import httpx
import os
from datetime import datetime


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
        data = resp.json()
        return data["token"]


async def eklesia_get_alunos(token: str, turma_id: int) -> list:
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{EKLESIA_BASE}/ensino/EnsinoTurmaAlunoGradePresenca/ObterAlunosPresenca",
            params={"codigocEnsinoTurma": turma_id},
            headers={"Authorization": f"Bearer {token}"},
            timeout=15.0,
        )
        resp.raise_for_status()
        return resp.json()


async def eklesia_get_grades(token: str, turma_id: int) -> list:
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{EKLESIA_BASE}/ensino/EnsinoTurmaAlunoGradePresenca/ObterPresentes",
            params={"codigocEnsinoTurma": turma_id, "codGrade": 0, "data": datetime.now().strftime("%Y-%m-%dT%H:%M:%S")},
            headers={"Authorization": f"Bearer {token}"},
            timeout=15.0,
        )
        resp.raise_for_status()
        return resp.json()


async def eklesia_salvar_presenca(
    token: str,
    turma_id: int,
    grade_id: int,
    pessoas: list,
    data: str,
) -> dict:
    payload = {
        "pessoasAtuais": [],
        "pessoas": pessoas,
        "codEnsinoCursoGrade": grade_id,
        "codEnsinoTurma": turma_id,
        "data": data,
    }
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{EKLESIA_BASE}/ensino/EnsinoTurmaAlunoGradePresenca/Salvar",
            json=payload,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
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
    now = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")

    result = await eklesia_salvar_presenca(
        token=token,
        turma_id=turma_id,
        grade_id=grade_id,
        pessoas=present_students,
        data=now,
    )
    return result
