from django.contrib.auth import authenticate, login as auth_login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db import transaction
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from django.utils.http import url_has_allowed_host_and_scheme
from .forms import FotoPerfilForm
from .models import (
    Candidatura,
    Conversa,
    Favorito,
    Mensagem,
    Oportunidade,
    VagaDescartada,
    PerfilUsuario,
)
from django.contrib import messages
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
        matricula = request.POST.get("username", "").strip()
        senha = request.POST.get("password", "")

        user = authenticate(request, username=matricula, password=senha)
        if user is not None:
            auth_login(request, user)
            return redirect("home")

        return render(
            request,
            "Login.html",
            {"erro": "Matrícula ou senha incorretos. Tente novamente."},
        )

    return render(request, "Login.html")


def criar_conta(request):
    if request.method == "POST":
        nome = request.POST.get("nome", "").strip()
        matricula = request.POST.get("username", "").strip()
        senha = request.POST.get("password", "")
        confirmar_senha = request.POST.get("confirmar_senha", "")

        # Senhas precisam ser iguais
        if senha != confirmar_senha:
            return render(
                request,
                "criar_conta.html",
                {"erro": "As senhas não coincidem!"}
            )

        # Matrícula não pode estar cadastrada
        if User.objects.filter(username=matricula).exists():
            return render(
                request,
                "criar_conta.html",
                {"erro": "Esta matrícula já está registada."}
            )

        # Cria o usuário
        User.objects.create_user(
            username=matricula,
            password=senha,
            first_name=nome
        )

        return redirect("login")

    
    return render(request, "criar_conta.html")


# chat
@transaction.atomic
def _criar_candidatura_e_conversa(usuario, oportunidade, origem):
    candidatura, criada = Candidatura.objects.get_or_create(
        usuario=usuario,
        oportunidade=oportunidade,
        defaults={"status": "Enviada", "origem": origem},
    )

    conversa, conversa_criada = Conversa.objects.get_or_create(
        usuario=usuario,
        oportunidade=oportunidade,
    )

    # Não criamos mais respostas prontas. A conversa começa vazia e as
    # respostas são geradas pelo assistente Gemini somente quando o candidato
    # envia uma pergunta.
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
    conversa_atual = get_object_or_404(
        Conversa.objects.select_related("oportunidade__empresa"),
        pk=conversa_id,
        usuario=request.user,
    )

    try:
        if request.content_type == "application/json":
            payload = json.loads(request.body or b"{}")
            texto = str(payload.get("mensagem", "")).strip()
        else:
            texto = request.POST.get("mensagem", "").strip()
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse(
            {"ok": False, "erro": "Requisição inválida."},
            status=400,
        )

    if not texto:
        return JsonResponse(
            {"ok": False, "erro": "Digite uma pergunta antes de enviar."},
            status=400,
        )

    if len(texto) > 2000:
        return JsonResponse(
            {"ok": False, "erro": "A mensagem deve ter no máximo 2000 caracteres."},
            status=400,
        )

    historico = list(
        conversa_atual.mensagens
        .exclude(texto__startswith=MENSAGEM_AUTOMATICA_ANTIGA_PREFIXO)
        .order_by("criada_em", "id")
        .values("autor", "texto")
    )[-8:]

    try:
        resposta = responder_sobre_vaga(
            vaga=conversa_atual.oportunidade,
            pergunta=texto,
            historico=historico,
        )
    except GeminiConfigurationError:
        logger.exception("Gemini não está configurado para o Connecto.")
        return JsonResponse(
            {
                "ok": False,
                "erro": "O assistente ainda não está configurado no servidor.",
            },
            status=503,
        )
    except GeminiResponseError:
        logger.exception("A Gemini API não retornou uma resposta utilizável.")
        return JsonResponse(
            {
                "ok": False,
                "erro": "Não foi possível obter uma resposta agora. Tente novamente.",
            },
            status=503,
        )
    except Exception:
        logger.exception("Falha ao consultar a Gemini API.")
        return JsonResponse(
            {
                "ok": False,
                "erro": "Não foi possível obter uma resposta agora. Tente novamente.",
            },
            status=503,
        )

    with transaction.atomic():
        mensagem_candidato = Mensagem.objects.create(
            conversa=conversa_atual,
            autor="candidato",
            texto=texto,
        )
        mensagem_assistente = Mensagem.objects.create(
            conversa=conversa_atual,
            autor="empresa",
            texto=resposta,
        )
        conversa_atual.save(update_fields=["atualizada_em"])

    return JsonResponse(
        {
            "ok": True,
            "resposta": resposta,
            "mensagem_candidato_id": mensagem_candidato.id,
            "mensagem_assistente_id": mensagem_assistente.id,
        }
    )



# Perfil

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




    nome = usuario.first_name or usuario.username
    matricula = usuario.username
    email = usuario.email or "Não informado"

    iniciais = "".join(
        parte[0] for parte in nome.split()[:2]
    ).upper()

    # O User padrão do Django não possui campo curso.
    # Por enquanto mantemos esses dados no contexto.
    curso = "Ciência da Computação"
    instituicao = "PUC-Rio"

    contexto = {
        "nome": nome,
        "iniciais": iniciais,
        "matricula": matricula,
        "email": email,
        "curso": curso,
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
    return redirect("home")
