# Sistema Ponto Facial

Sistema de controle de presença por reconhecimento facial com gestão de alunos, turmas e notificações WhatsApp.

## Stack
- Frontend: HTML/CSS/JS (PWA Responsivo)
- Backend: Python FastAPI + InsightFace + FAISS
- Banco: TiDB Cloud (schema: facial_attendance)
- Deploy: Vercel (frontend) + Render (backend)

## Funcionalidades
- Reconhecimento facial via câmera do navegador
- Cadastro de alunos com rosto
- Registro de presença automático
- Gestão de turmas
- Login do admin via reconhecimento facial
- Notificações WhatsApp

## Deploy
- Frontend: Vercel
- Backend: Render (Docker)

## Configuração
Copie backend/.env.example para backend/.env e preencha as variáveis de ambiente.
