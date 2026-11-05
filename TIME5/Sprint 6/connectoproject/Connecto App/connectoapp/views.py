
    return render(
        request,
        "notificacoes.html",
        {
            "notificacoes": notificacoes_usuario,
            "vapid_public_key": settings.VAPID_PUBLIC_KEY,
        },
    )

@login_required
def perfil_empresa(request):
    empresa = get_object_or_404(Empresa, usuario=request.user)

    return render(
        request,
        "perfil_empresa.html",
        {"empresa": empresa},
    )
@login_required
def configuracoes(request):
    return render(request, "configuracoes.html")

import json

from django.http import JsonResponse
from django.views.decorators.http import require_POST


@require_POST
@login_required
def push_subscribe(request):

    dados = json.loads(request.body)

    endpoint = dados.get("endpoint")
    keys = dados.get("keys", {})

    if not endpoint:
        return JsonResponse(
            {"erro": "Subscription inválida"},
            status=400
        )

    PushSubscription.objects.update_or_create(
        endpoint=endpoint,
        defaults={
            "usuario": request.user,
            "p256dh": keys.get("p256dh", ""),
            "auth": keys.get("auth", ""),
            "ativa": True,
        }
    )

    return JsonResponse({
        "ok": True
    })


@require_POST
@login_required
def verificar_notificacoes(request):
    nao_lidas = Notificacao.objects.filter(
        usuario=request.user,
        lida=False,
    ).count()

    return JsonResponse({
        "novas": [],
        "nao_lidas": nao_lidas,
    })

@login_required
def abrir_solicitacao(request):
    if request.method == "POST":
        mensagem = request.POST.get("mensagem", "").strip()

        if not mensagem:
            messages.error(request, "Digite uma mensagem antes de enviar.")

        elif len(mensagem) > 3000:
            messages.error(request, "A mensagem deve ter no máximo 3000 caracteres.")

        elif not settings.EMAIL_HOST_USER or not settings.EMAIL_HOST_PASSWORD or not settings.SUPPORT_EMAIL:
            messages.error(request, "O e-mail de suporte ainda não está configurado.")

        else:
            usuario = request.user
            nome = usuario.get_full_name().strip() or usuario.username

            conteudo = (
                "Nova solicitação de suporte - Connecto\n\n"
                f"Nome: {nome}\n"
                f"Matrícula: {usuario.username}\n"
                f"E-mail: {usuario.email or 'Não informado'}\n\n"
                "Mensagem:\n"
                f"{mensagem}"
            )

            try:
                enviados = send_mail(
                    subject="Nova solicitação de suporte - Connecto",
                    message=conteudo,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[settings.SUPPORT_EMAIL],
                    fail_silently=False,
                )

                if enviados != 1:
                    raise SMTPException("O servidor não confirmou o envio.")

            except (SMTPException, OSError):
                logger.exception("Erro ao enviar solicitação de suporte.")
                messages.error(
                    request,
                    "Não foi possível enviar sua solicitação. Tente novamente."
                )
            else:
                messages.success(request, "Sua solicitação foi enviada com sucesso!")
                return redirect("abrir_solicitacao")

        return render(
            request,
            "abrir_solicitacao.html",
            {"mensagem": mensagem}
        )

    return render(request, "abrir_solicitacao.html")
