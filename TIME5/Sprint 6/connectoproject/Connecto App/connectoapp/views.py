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
    Curso,
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
    cursos = Curso.objects.all().order_by("nome")

    if request.method == "POST":
        nome = request.POST.get("nome", "").strip()
        matricula = request.POST.get("username", "").strip()
        senha = request.POST.get("password", "")
        confirmar_senha = request.POST.get(
            "confirmar_senha",
            "",
        )

        curso_id = request.POST.get("curso")
        periodo = request.POST.get("periodo")
        instituicao = request.POST.get(
            "instituicao",
            "",
        ).strip()

        if senha != confirmar_senha:
            return render(
                request,
                "criar_conta.html",
                {
                    "erro": "As senhas não coincidem!",
                    "cursos": cursos,
                },
            )

        if User.objects.filter(
            username=matricula
        ).exists():
            return render(
                request,
                "criar_conta.html",
                {
                    "erro": "Esta matrícula já está registada.",
                    "cursos": cursos,
                },
            )

        if not curso_id:
            return render(
                request,
                "criar_conta.html",
                {
                    "erro": "Selecione seu curso.",
                    "cursos": cursos,
                },
            )

        try:
            curso = Curso.objects.get(
                pk=curso_id
            )
        except Curso.DoesNotExist:
            return render(
                request,
                "criar_conta.html",
                {
                    "erro": "Curso inválido.",
                    "cursos": cursos,
                },
            )

        try:
            periodo_numero = (
                int(periodo)
                if periodo
                else None
            )
        except ValueError:
            periodo_numero = None

        partes_nome = nome.split(
            maxsplit=1
        )

        with transaction.atomic():
            user = User.objects.create_user(
                username=matricula,
                password=senha,
                first_name=(
                    partes_nome[0]
                    if partes_nome
                    else ""
                ),
                last_name=(
                    partes_nome[1]
                    if len(partes_nome) > 1
                    else ""
                ),
            )

            PerfilUsuario.objects.create(
                usuario=user,
                curso=curso,
                periodo=periodo_numero,
                instituicao=instituicao,
            )

        return redirect("login")

    return render(
        request,
        "criar_conta.html",
        {
            "cursos": cursos,
        },
    )


# chat
@transaction.atomic
def _criar_candidatura_e_conversa(usuario, oportunidade, origem):
    candidatura, criada = Candidatura.objects.get_or_create(
        usuario=usuario,
        oportunidade=oportunidade,
        defaults={
            "status": "Enviada",
            "origem": origem,
        },
    )

    conversa, conversa_criada = Conversa.objects.get_or_create(
        usuario=usuario,
        oportunidade=oportunidade,
    )

    # Só gera uma nova notificação quando a candidatura
    # realmente foi criada agora.
    if criada:
        notificacao, _ = Notificacao.objects.get_or_create(
            usuario=usuario,
            candidatura=candidatura,
        )

        def enviar_depois_do_commit():
            enviado = enviar_push(
                usuario=usuario,
                titulo="Candidatura enviada",
                mensagem=(
                    f'Sua candidatura para "{oportunidade.titulo}" '
                    "foi registrada com sucesso."
                ),
                url=f"/mensagens/{conversa.id}/",
            )

            if enviado:
                Notificacao.objects.filter(
                    pk=notificacao.pk
                ).update(entregue=True)

        transaction.on_commit(enviar_depois_do_commit)

    return candidatura, criada, conversa


def _ids_candidatados(usuario):
    return Candidatura.objects.filter(usuario=usuario).values_list(
        "oportunidade_id", flat=True
    )



# Home / busca / vaga

@login_required
def home(request):
    usuario = request.user

    # Vagas em que o usuário já se candidatou
    candidaturas_ids = Candidatura.objects.filter(
        usuario=usuario
    ).values_list(
        "oportunidade_id",
        flat=True
    )

    # Todas as vagas disponíveis
    vagas = (
        Oportunidade.objects
        .filter(ativa=True)
        .exclude(id__in=candidaturas_ids)
        .select_related("empresa")
    )

    # Filtro selecionado pela URL
    area_selecionada = request.GET.get("area", "").strip()

    if area_selecionada:
        vagas = vagas.filter(
            area__iexact=area_selecionada
        )

    # Categorias que queremos exibir na interface
    categorias = (
    Oportunidade.objects
    .filter(ativa=True)
    .exclude(area="")
    .values_list("area", flat=True)
    .distinct()
    .order_by("area")
)

    favoritos_ids = set(
        Favorito.objects.filter(
            usuario=usuario
        ).values_list(
            "oportunidade_id",
            flat=True
        )
    )

    contexto = {
        "vagas": vagas,
        "categorias": categorias,
        "area_selecionada": area_selecionada,
        "favoritos_ids": favoritos_ids,
    }

    return render(
        request,
        "home.html",
        contexto
    )

@require_POST
@login_required
def toggle_favorito(request, vaga_id):
    vaga = get_object_or_404(
        Oportunidade,
        pk=vaga_id,
        ativa=True
    )

    favorito, criado = Favorito.objects.get_or_create(
        usuario=request.user,
        oportunidade=vaga
    )

    if not criado:
        favorito.delete()

    destino = request.POST.get("next", "")

    if destino and url_has_allowed_host_and_scheme(
        destino,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return redirect(destino)

    return redirect("home")

@login_required
def busca(request):
    # Mantém a tela já existente. Depois podemos transformar esse q em filtro real.
    return render(request, "Tela_Joao_Felipe.html", {"q": request.GET.get("q", "")})


@login_required
def visualizacao_vaga(request, vaga_id=None):
    if vaga_id is None:
        vaga = Oportunidade.objects.filter(ativa=True).select_related("empresa").first()
        if vaga is None:
            raise Http404("Vaga não encontrada")
    else:
        vaga = get_object_or_404(
            Oportunidade.objects.select_related("empresa"),
            pk=vaga_id,
            ativa=True,
        )

    ja_candidatado = Candidatura.objects.filter(
        usuario=request.user,
        oportunidade=vaga,
    ).exists()

    return render(
        request,
        "visualizacao_vaga.html",
        {"vaga": vaga, "vaga_id": vaga.id, "ja_candidatado": ja_candidatado},
    )


@require_POST
@login_required
def candidatar(request, vaga_id):
    vaga = get_object_or_404(Oportunidade, pk=vaga_id, ativa=True)
    _criar_candidatura_e_conversa(request.user, vaga, origem="home")

    destino = request.POST.get("next")
    if destino == "mensagens":
        return redirect("mensagens")
    if destino == "candidaturas":
        return redirect("candidaturas")
    return redirect("home")



# Match Tinder

@login_required
def match(request):
    candidaturas_ids = _ids_candidatados(request.user)
    descartadas_ids = VagaDescartada.objects.filter(
        usuario=request.user
    ).values_list("oportunidade_id", flat=True)

    disponiveis = (
        Oportunidade.objects.filter(ativa=True)
        .exclude(id__in=candidaturas_ids)
        .exclude(id__in=descartadas_ids)
        .select_related("empresa")
    )

    vaga = disponiveis.first()
    total_vagas = Oportunidade.objects.filter(ativa=True).count()
    processadas = (
        Candidatura.objects.filter(usuario=request.user, origem="match").count()
        + VagaDescartada.objects.filter(usuario=request.user).count()
    )

    contexto = {
        "vaga": vaga,
        "restantes": disponiveis.count(),
        "total_vagas": total_vagas,
        "posicao": min(processadas + 1, total_vagas) if total_vagas else 0,
    }
    return render(request, "match.html", contexto)


@require_POST
@login_required
def match_acao(request, vaga_id):
    vaga = get_object_or_404(Oportunidade, pk=vaga_id, ativa=True)
    acao = request.POST.get("acao")

    if acao == "curtir":
        _criar_candidatura_e_conversa(request.user, vaga, origem="match")
        # Se já havia sido descartada por algum motivo, desfaz o descarte.
        VagaDescartada.objects.filter(
            usuario=request.user,
            oportunidade=vaga,
        ).delete()
    elif acao == "descartar":
        if not Candidatura.objects.filter(
            usuario=request.user,
            oportunidade=vaga,
        ).exists():
            VagaDescartada.objects.get_or_create(
                usuario=request.user,
                oportunidade=vaga,
            )

    return redirect("match")



# Minhas candidaturas / favoritos
@login_required
def candidaturas(request):
    candidaturas_usuario = (
        Candidatura.objects.filter(usuario=request.user)
        .select_related("oportunidade__empresa")
    )
    return render(
        request,
        "candidaturas.html",
        {"candidaturas": candidaturas_usuario},
    )


@login_required
def favoritas(request):
    favoritas_usuario = (
        Favorito.objects.filter(usuario=request.user)
        .select_related("oportunidade__empresa")
    )
    return render(request, "favoritas.html", {"favoritas": favoritas_usuario})



# Mensagens
MENSAGEM_AUTOMATICA_ANTIGA_PREFIXO = (
    "Olá! Vimos seu perfil e ficamos muito interessados na sua candidatura para"
)


@login_required
def mensagens(request):
    conversas = (
        Conversa.objects.filter(usuario=request.user)
        .select_related("oportunidade__empresa")
        .prefetch_related("mensagens")
    )

    itens = []
    for conversa_item in conversas:
        itens.append(
            {
                "conversa": conversa_item,
                "ultima_mensagem": conversa_item.mensagens.exclude(
                    texto__startswith=MENSAGEM_AUTOMATICA_ANTIGA_PREFIXO
                ).last(),
            }
        )

    return render(request, "mensagens.html", {"itens": itens})


@login_required
def conversa(request, conversa_id):
    conversa_atual = get_object_or_404(
        Conversa.objects.select_related("oportunidade__empresa"),
        pk=conversa_id,
        usuario=request.user,
    )

    candidatura = Candidatura.objects.filter(
        usuario=request.user,
        oportunidade=conversa_atual.oportunidade,
    ).first()

    # Conversas antigas podem conter a resposta fixa criada pela versão
    # anterior do app. Ela fica escondida para não parecer uma resposta da IA.
    mensagens_visiveis = conversa_atual.mensagens.exclude(
        texto__startswith=MENSAGEM_AUTOMATICA_ANTIGA_PREFIXO
    )

    return render(
        request,
        "conversa.html",
        {
            "conversa": conversa_atual,
            "mensagens_conversa": mensagens_visiveis,
            "foi_match": bool(candidatura and candidatura.origem == "match"),
        },
    )


@require_POST
@login_required
def assistente_vaga(request, conversa_id):
    conversa = get_object_or_404(
        Conversa.objects.select_related(
            "oportunidade",
            "oportunidade__empresa",
        ),
        id=conversa_id,
        usuario=request.user,
    )

    try:
        dados = json.loads(request.body or b"{}")
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse(
            {
                "ok": False,
                "erro": "Requisição inválida.",
            },
            status=400,
        )

    # Compatível com versões do frontend que usam "pergunta" ou "mensagem".
    pergunta = str(
        dados.get("pergunta")
        or dados.get("mensagem")
        or ""
    ).strip()

    if not pergunta:
        return JsonResponse(
            {
                "ok": False,
                "erro": "Digite uma pergunta para o assistente.",
            },
            status=400,
        )

    if len(pergunta) > 2000:
        return JsonResponse(
            {
                "ok": False,
                "erro": "A mensagem deve ter no máximo 2000 caracteres.",
            },
            status=400,
        )

    # Últimas 8 mensagens, em ordem cronológica.
    historico = list(
        conversa.mensagens
        .exclude(texto__startswith=MENSAGEM_AUTOMATICA_ANTIGA_PREFIXO)
        .order_by("-criada_em", "-id")
        .values("autor", "texto")[:8]
    )
    historico.reverse()

    try:
        resposta = responder_sobre_vaga(
            vaga=conversa.oportunidade,
            usuario=request.user,
            pergunta=pergunta,
            historico=historico,
        )

    except GeminiConfigurationError:
        logger.exception("Gemini não está configurado para o Connecto.")
        return JsonResponse(
            {
                "ok": True,
                "resposta": (
                    "O assistente está temporariamente indisponível. "
                    "Tente novamente em alguns instantes."
                ),
                "degradada": True,
            }
        )

    except GeminiResponseError:
        logger.exception("A Gemini API não retornou uma resposta utilizável.")
        return JsonResponse(
            {
                "ok": True,
                "resposta": (
                    "Não consegui concluir essa resposta agora. "
                    "Tente novamente em alguns instantes."
                ),
                "degradada": True,
            }
        )

    except Exception:
        logger.exception("Falha inesperada ao consultar a Gemini API.")
        return JsonResponse(
            {
                "ok": True,
                "resposta": (
                    "O assistente está temporariamente indisponível. "
                    "Tente novamente em alguns instantes."
                ),
                "degradada": True,
            }
        )

    # Nunca permite None ou string vazia no banco.
    resposta = str(resposta or "").strip()

    if not resposta:
        logger.error(
            "Connecto IA retornou resposta vazia. "
            "A gravação da mensagem foi bloqueada."
        )
        return JsonResponse(
            {
                "ok": True,
                "resposta": (
                    "Não consegui concluir essa resposta agora. "
                    "Tente novamente em alguns instantes."
                ),
                "degradada": True,
            }
        )

    with transaction.atomic():
        Mensagem.objects.create(
            conversa=conversa,
            autor="candidato",
            texto=pergunta,
        )

        mensagem_assistente = Mensagem.objects.create(
            conversa=conversa,
            autor="empresa",
            texto=resposta,
        )

        conversa.save(update_fields=["atualizada_em"])

    return JsonResponse(
        {
            "ok": True,
            "resposta": resposta,
            "degradada": False,
            "mensagem_id": mensagem_assistente.id,
        }
    )



# Perfil

@login_required
def editar_perfil(request):
    usuario = request.user

    perfil_usuario, _ = PerfilUsuario.objects.get_or_create(
        usuario=usuario
    )

    cursos = Curso.objects.all().order_by("nome")

    if request.method == "POST":
        nome = request.POST.get("nome", "").strip()
        email = request.POST.get("email", "").strip()

        curso_id = request.POST.get("curso")
        periodo = request.POST.get("periodo")
        instituicao = request.POST.get(
            "instituicao",
            "",
        ).strip()

        if not nome or not email:
            messages.error(
                request,
                "Preencha nome e e-mail.",
            )

        else:
            partes_nome = nome.split(maxsplit=1)

            usuario.first_name = partes_nome[0]
            usuario.last_name = (
                partes_nome[1]
                if len(partes_nome) > 1
                else ""
            )

            usuario.email = email

            usuario.save(
                update_fields=[
                    "first_name",
                    "last_name",
                    "email",
                ]
            )

            # Curso
            if curso_id:
                perfil_usuario.curso = get_object_or_404(
                    Curso,
                    pk=curso_id,
                )
            else:
                perfil_usuario.curso = None

            # Período
            if periodo:
                try:
                    perfil_usuario.periodo = int(periodo)
                except ValueError:
                    perfil_usuario.periodo = None
            else:
                perfil_usuario.periodo = None

            # Instituição
            perfil_usuario.instituicao = instituicao

            perfil_usuario.save()

            messages.success(
                request,
                "Perfil atualizado com sucesso!",
            )

            return redirect("perfil")

    nome = (
        usuario.get_full_name().strip()
        or usuario.username
    )

    return render(
        request,
        "editar_perfil.html",
        {
            "nome": nome,
            "email": usuario.email,
            "matricula": usuario.username,

            "perfil_usuario": perfil_usuario,
            "cursos": cursos,
        },
    )
    

@login_required
def perfil(request):
    usuario = request.user

    perfil_usuario, criado = PerfilUsuario.objects.get_or_create(
        usuario=usuario
    )

    
    if request.method == "POST":
        form = FotoPerfilForm(
            request.POST,
            request.FILES,
            instance=perfil_usuario
        )

        if not request.FILES.get("foto"):
            messages.error(request, "Selecione uma foto antes de salvar.")
            return redirect("perfil")

        if form.is_valid():
            form.save()
            messages.success(request, "Foto atualizada com sucesso!")
            return redirect("perfil")
        else:
            messages.error(request, "Não foi possível salvar a foto.")

    else:
        form = FotoPerfilForm(instance=perfil_usuario)




    nome = usuario.get_full_name().strip() or usuario.username
    matricula = usuario.username
    email = usuario.email or "Não informado"

    iniciais = "".join(
        parte[0] for parte in nome.split()[:2]
    ).upper()

    # O User padrão do Django não possui campo curso.
    # Por enquanto mantemos esses dados no contexto.
    curso = (
        perfil_usuario.curso.nome
        if perfil_usuario.curso
        else "Não informado"
)

    periodo = (
        perfil_usuario.periodo
        if perfil_usuario.periodo
        else "Não informado"
)

    instituicao = (
        perfil_usuario.instituicao
        or "Não informado"
)

    contexto = {
        "nome": nome,
        "iniciais": iniciais,
        "matricula": matricula,
        "email": email,
        "curso": curso,
        "periodo": periodo,
        "instituicao": instituicao,
        "foto": perfil_usuario.foto,
        "foto_form": form,
        
        "total_candidaturas":
            Candidatura.objects.filter(usuario=usuario).count(),

        "total_salvas":
            Favorito.objects.filter(usuario=usuario).count(),

        "total_conversas":
            Conversa.objects.filter(usuario=usuario).count(),
    }

    return render(
        request,
        "perfil.html",
        contexto
    )

def esqueceu_senha(request):
    return render(
        request,
        "Login.html",
        {"erro": "Recuperação de senha ainda não disponível."}
    )


@login_required
def duvidas_frequentes(request):
    return render(request, "duvidas_frequentes.html")


@login_required
def notificacoes(request):
    notificacoes_usuario = list(
        Notificacao.objects
        .filter(usuario=request.user)
        .select_related(
            "candidatura__oportunidade__empresa"
        )
        .order_by("-criada_em")
    )

    oportunidades_ids = [
        notificacao.candidatura.oportunidade_id
        for notificacao in notificacoes_usuario
    ]

    conversas = {
        conversa.oportunidade_id: conversa.id
        for conversa in Conversa.objects.filter(
            usuario=request.user,
            oportunidade_id__in=oportunidades_ids,
        )
    }

    for notificacao in notificacoes_usuario:
        notificacao.conversa_id = conversas.get(
            notificacao.candidatura.oportunidade_id
        )

    # Mantemos os objetos carregados com lida=False para o
    # template poder destacar as novas.
    Notificacao.objects.filter(
        usuario=request.user,
        lida=False,
    ).update(lida=True)

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

