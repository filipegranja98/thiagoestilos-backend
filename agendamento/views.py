import json
import urllib.parse
from datetime import datetime, time, timedelta

from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from .models import Cliente, Agendamento, Servico


# ===============================
# CONFIGURAÇÃO
# ===============================

BARBEIRO_PHONE = "5581993113251"
BARBEIRO_TOKEN = "supersecreto123"


def verificar_admin(request):
    auth = request.headers.get("Authorization")
    return auth == f"Bearer {BARBEIRO_TOKEN}"


# ===============================
# WHATSAPP - AGENDAMENTO
# ===============================

def gerar_link_whatsapp_agendamento(agendamento):
    mensagem = f"""
Novo Agendamento

Cliente: {agendamento.cliente.nome}
Telefone: {agendamento.cliente.telefone}

Servico: {agendamento.servico.nome}
Data: {agendamento.data}
Horario: {agendamento.horario}

Token do agendamento:
{agendamento.token}

Guarde este token para reagendar ou cancelar futuramente.
"""

    mensagem_codificada = urllib.parse.quote(mensagem)
    return f"https://wa.me/{BARBEIRO_PHONE}?text={mensagem_codificada}"


# ===============================
# WHATSAPP - REAGENDAMENTO
# ===============================

def gerar_link_whatsapp_reagendamento(agendamento):
    mensagem = f"""
Reagendamento solicitado

Cliente: {agendamento.cliente.nome}
Telefone: {agendamento.cliente.telefone}

Servico: {agendamento.servico.nome}

Nova data: {agendamento.data}
Novo horario: {agendamento.horario}

Token do agendamento:
{agendamento.token}

Reagendamento informado pelo cliente.
"""

    mensagem_codificada = urllib.parse.quote(mensagem)
    return f"https://wa.me/{BARBEIRO_PHONE}?text={mensagem_codificada}"


# ===============================
# WHATSAPP - CANCELAMENTO
# ===============================

def gerar_link_whatsapp_cancelamento(agendamento):
    mensagem = f"""
Cancelamento de agendamento

Cliente: {agendamento.cliente.nome}
Telefone: {agendamento.cliente.telefone}

Servico: {agendamento.servico.nome}
Data: {agendamento.data}
Horario: {agendamento.horario}

Token:
{agendamento.token}

Agendamento cancelado pelo cliente.
"""

    mensagem_codificada = urllib.parse.quote(mensagem)
    return f"https://wa.me/{BARBEIRO_PHONE}?text={mensagem_codificada}"


# ===============================
# LISTAR SERVIÇOS
# ===============================

@require_http_methods(["GET"])
def listar_servicos(request):
    servicos = Servico.objects.all()

    dados = [{
        "id": s.id,
        "nome": s.nome,
        "duracao": s.duracao_minutos,
        "preco": str(s.preco)
    } for s in servicos]

    return JsonResponse({"servicos": dados})


# ===============================
# CRIAR AGENDAMENTO
# ===============================

@csrf_exempt
@require_http_methods(["POST"])
def criar_agendamento(request):
    try:
        payload = json.loads(request.body)

        nome = payload.get("nome")
        telefone = payload.get("telefone")
        data_agendamento = payload.get("data")
        horario = payload.get("horario")
        servico_id = payload.get("servico_id")

        if not all([nome, telefone, data_agendamento, horario, servico_id]):
            return JsonResponse({"error": "Dados incompletos"}, status=400)

        cliente, _ = Cliente.objects.get_or_create(
            telefone=telefone,
            defaults={"nome": nome}
        )

        servico = get_object_or_404(Servico, id=servico_id)

        agendamento = Agendamento.objects.create(
            cliente=cliente,
            servico=servico,
            data=data_agendamento,
            horario=horario
        )

        whatsapp_url = gerar_link_whatsapp_agendamento(agendamento)

        return JsonResponse({
            "success": "Agendamento criado com sucesso",
            "token": str(agendamento.token),
            "whatsapp_url": whatsapp_url
        }, status=201)

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)


# ===============================
# DETALHAR AGENDAMENTO (TOKEN)
# ===============================

@require_http_methods(["GET"])
def detalhe_agendamento(request, token):
    agendamento = get_object_or_404(Agendamento, token=token)

    return JsonResponse({
        "nome": agendamento.cliente.nome,
        "telefone": agendamento.cliente.telefone,
        "servico": agendamento.servico.nome,
        "duracao": agendamento.servico.duracao_minutos,
        "data": agendamento.data,
        "horario": agendamento.horario,
        "token": str(agendamento.token)
    })


# ===============================
# REAGENDAR
# ===============================

@csrf_exempt
@require_http_methods(["PUT"])
def reagendar(request, token):
    try:
        # 1. Busca o agendamento atual
        agendamento = Agendamento.objects.get(token=token)
        cliente = agendamento.cliente
    except Agendamento.DoesNotExist:
        return JsonResponse({"error": "Token inválido"}, status=404)

    try:
        payload = json.loads(request.body)

        # 2. ATUALIZAÇÃO PARCIAL: Só altera se o campo vier no payload e não for vazio
        # Se o usuário não mexer no campo, o 'get' mantém o que já está no banco
        nome_novo = payload.get("nome")
        if nome_novo:
            cliente.nome = nome_novo

        telefone_novo = payload.get("telefone")
        if telefone_novo:
            cliente.telefone = telefone_novo

        cliente.save()

        # 3. Atualiza os dados do agendamento
        servico_id = payload.get("servico_id")
        if servico_id:
            agendamento.servico = get_object_or_404(Servico, id=servico_id)

        if payload.get("data"):
            agendamento.data = payload.get("data")

        if payload.get("horario"):
            agendamento.horario = payload.get("horario")

        agendamento.save()

        # 4. SINCRONIZAÇÃO: Força o objeto agendamento a enxergar as mudanças do cliente
        agendamento.refresh_from_db()

        # 5. Geração do link (Agora com garantia de dados presentes)
        whatsapp_url = gerar_link_whatsapp_reagendamento(agendamento)

        return JsonResponse({
            "success": "Agendamento reagendado com sucesso",
            "whatsapp_url": whatsapp_url
        })

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)



# ===============================
# CANCELAR (USANDO MESMO TOKEN)
# ===============================

@csrf_exempt
@require_http_methods(["DELETE"])
def cancelar(request, token):
    try:
        agendamento = Agendamento.objects.get(token=token)
    except Agendamento.DoesNotExist:
        return JsonResponse({"error": "Token inválido"}, status=404)

    whatsapp_url = gerar_link_whatsapp_cancelamento(agendamento)

    agendamento.delete()

    return JsonResponse({
        "success": "Agendamento cancelado com sucesso",
        "whatsapp_url": whatsapp_url
    })


# ===============================
# HORÁRIOS DISPONÍVEIS
# ===============================

@require_http_methods(["GET"])
def horarios_disponiveis(request):
    data_str = request.GET.get("data")
    servico_id = request.GET.get("servico_id")

    if not data_str or not servico_id:
        return JsonResponse({"error": "Data ou serviço não informado"}, status=400)

    data_consulta = datetime.strptime(data_str, "%Y-%m-%d").date()
    servico = get_object_or_404(Servico, id=servico_id)

    abertura = time(9, 0)
    fechamento = time(18, 0)

    inicio = datetime.combine(data_consulta, abertura)
    fim = datetime.combine(data_consulta, fechamento)

    horarios_livres = []

    agendamentos = Agendamento.objects.filter(data=data_consulta)

    while inicio + timedelta(minutes=servico.duracao_minutos) <= fim:
        fim_novo = inicio + timedelta(minutes=servico.duracao_minutos)

        conflito = False
        for ag in agendamentos:
            inicio_existente = datetime.combine(ag.data, ag.horario)
            fim_existente = inicio_existente + timedelta(
                minutes=ag.servico.duracao_minutos
            )

            if inicio < fim_existente and fim_novo > inicio_existente:
                conflito = True
                break

        if not conflito:
            horarios_livres.append(inicio.time().strftime("%H:%M"))

        inicio += timedelta(minutes=30)

    return JsonResponse({"horarios_disponiveis": horarios_livres})


# ===============================
# LISTAR AGENDA (BARBEIRO)
# ===============================

@require_http_methods(["GET"])
def listar_agendamentos(request):
    if not verificar_admin(request):
        return JsonResponse({"error": "Não autorizado"}, status=401)

    agendamentos = Agendamento.objects.all()

    dados = [{
        "cliente": ag.cliente.nome,
        "telefone": ag.cliente.telefone,
        "servico": ag.servico.nome,
        "data": ag.data,
        "horario": ag.horario
    } for ag in agendamentos]

    return JsonResponse({"agendamentos": dados})
