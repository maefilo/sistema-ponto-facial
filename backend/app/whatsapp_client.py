import httpx
from .config import config


async def send_whatsapp_message(phone: str, message: str) -> bool:
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{config.WHATSAPP_SERVICE_URL}/send-message",
                json={"phone": phone, "message": message},
                timeout=10.0,
            )
            return response.status_code == 200
    except Exception:
        return False


async def send_attendance_notification(
    student_name: str,
    parent_phone: str,
    status: str,
    date_str: str,
) -> bool:
    if not parent_phone:
        return False

    status_text = "presente" if status == "present" else "atrasado"
    message = (
        f"Olá! O(a) aluno(a) *{student_name}* foi registrado(a) como *{status_text}* "
        f"na data de {date_str}.\n\n"
        f"Para mais informações, acesse o painel de controle."
    )
    return await send_whatsapp_message(parent_phone, message)


async def send_daily_report(parent_phone: str, report: str) -> bool:
    if not parent_phone:
        return False
    return await send_whatsapp_message(parent_phone, report)
