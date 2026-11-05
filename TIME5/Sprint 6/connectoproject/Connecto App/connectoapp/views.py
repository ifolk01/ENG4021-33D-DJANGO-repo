from django.shortcuts import render
from django.contrib.auth import authenticate, login as auth_login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db import transaction
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from django.utils.http import url_has_allowed_host_and_scheme
from .webpush_service import enviar_push
from .forms import FotoPerfilForm
from .models import (
    Candidatura,
    Empresa,
    Conversa,
    Favorito,
    Mensagem,
    Notificacao,
    Oportunidade,
    PushSubscription,
    VagaDescartada,
    PerfilUsuario,
)
from django.contrib import messages
from django.conf import settings
from django.core.mail import send_mail
from smtplib import SMTPException
import json
import logging

from .gemini_service import (
    GeminiConfigurationError,
    GeminiResponseError,
    responder_sobre_vaga,
)

logger = logging.getLogger(__name__)

def login(request):
    if request.method == "POST":
        identificador = request.POST.get("username", "").strip()
        senha = request.POST.get("password", "")
        tipo_usuario = request.POST.get("tipo_usuario", "aluno")

        if tipo_usuario == "empregador":
            empresa = Empresa.objects.filter(
                email__iexact=identificador,
                usuario__isnull=False,
            ).select_related("usuario").first()

            if empresa is not None:
                user = authenticate(
                    request,
                    username=empresa.usuario.username,
                    password=senha,
                )

                if user is not None:
                    auth_login(request, user)
                    return redirect("perfil_empresa")

            erro = "Email ou senha incorretos. Tente novamente."

        else:
            user = authenticate(
                request,
                username=identificador,
                password=senha,
            )

            if user is not None and not Empresa.objects.filter(
                usuario=user
            ).exists():
                auth_login(request, user)
                return redirect("home")

            erro = "Matrícula ou senha incorretos. Tente novamente."

        return render(
            request,
            "Login.html",
            {
                "erro": erro,
                "tipo_usuario": tipo_usuario,
            },
        )

    return render(request, "Login.html")

def criar_conta(request):
    if request.method == "POST":
        nome = request.POST.get("nome", "").strip()
        matricula = request.POST.get("username", "").strip()
        senha = request.POST.get("password", "")
        confirmar_senha = request.POST.get("confirmar_senha", "")
