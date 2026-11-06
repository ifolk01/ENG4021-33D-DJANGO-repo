import logging
import time
import unicodedata
from decimal import Decimal

from django.conf import settings
from google import genai
from google.genai import types


logger = logging.getLogger(__name__)


CONNECTO_SYSTEM_MESSAGE = """
Você é um assistente virtual de recrutamento do app Connecto.

Sua função é ajudar o candidato a compreender a vaga e avaliar a relação entre
a oportunidade e o perfil acadêmico/profissional dele.

Você pode responder SOMENTE com base em:
1. Informações cadastradas da vaga fornecidas pelo sistema.
2. Informações do perfil do candidato fornecidas pelo sistema.
3. Histórico da conversa fornecido pelo sistema, apenas para continuidade.

Você pode comparar o curso/perfil do candidato com o título, a área, a
descrição e os requisitos da vaga quando a pergunta exigir.

Não invente experiências, habilidades ou qualificações do candidato.
Não invente informações ausentes da vaga.

Responda sempre em português do Brasil, de forma natural, curta e clara.
Prefira 1 ou 2 frases e use no máximo 3 quando uma comparação precisar de
explicação.
""".strip()


RESPOSTA_SEM_INFORMACAO = (
    "Desculpe, não possuo essa informação para responder a esta pergunta."
)


class GeminiConfigurationError(RuntimeError):
    """Configuração necessária para acessar a Gemini API está ausente."""


class GeminiResponseError(RuntimeError):
    """A Gemini API não devolveu uma resposta de texto utilizável."""


def _texto_ou_nao_informado(valor):
    if valor is None:
        return "Não informado"

    texto = str(valor).strip()
    return texto if texto else "Não informado"


def _formatar_data(valor):
    if not valor:
        return "Não informado"

    try:
        return valor.strftime("%d/%m/%Y")
    except (AttributeError, ValueError):
        return _texto_ou_nao_informado(valor)


def _formatar_moeda(valor):
    if valor is None or valor == "":
        return "Não informado"

    try:
        numero = Decimal(str(valor))
        formatado = (
            f"{numero:,.2f}"
            .replace(",", "X")
            .replace(".", ",")
            .replace("X", ".")
        )
        return f"R$ {formatado}"
    except Exception:
        return _texto_ou_nao_informado(valor)


def _normalizar_texto(texto):
    texto = str(texto or "").lower().strip()
    texto = unicodedata.normalize("NFD", texto)

    return "".join(
        caractere
        for caractere in texto
        if unicodedata.category(caractere) != "Mn"
    )


def _obter_perfil_usuario(usuario):
    if not usuario:
        return None

    for atributo in ("perfil", "perfilusuario", "profile"):
        try:
            perfil = getattr(usuario, atributo, None)
        except Exception:
            perfil = None

        if perfil is not None:
            return perfil

    return None


def _valor_relacionado(valor):
    if valor is None:
        return "Não informado"

    nome = getattr(valor, "nome", None)
    if nome:
        return _texto_ou_nao_informado(nome)

    return _texto_ou_nao_informado(valor)


def _formatar_contexto_candidato(usuario):
    perfil = _obter_perfil_usuario(usuario)

    nome = ""
    if usuario:
        try:
            nome = usuario.get_full_name().strip()
        except Exception:
            nome = ""

        if not nome:
            nome = (
                getattr(usuario, "first_name", "")
                or getattr(usuario, "username", "")
            )

    curso = getattr(perfil, "curso", None) if perfil else None
    periodo = getattr(perfil, "periodo", None) if perfil else None
    instituicao = getattr(perfil, "instituicao", None) if perfil else None

    campos = [
        ("Nome", nome),
        ("Curso", _valor_relacionado(curso)),
        ("Período", periodo),
        ("Instituição", _valor_relacionado(instituicao)),
    ]

    return "\n".join(
        f"{campo}: {_texto_ou_nao_informado(valor)}"
        for campo, valor in campos
    )


def _formatar_contexto_vaga(vaga):
    empresa = getattr(vaga, "empresa", None)

    campos = [
        ("Título", getattr(vaga, "titulo", None)),
        ("Empresa", getattr(empresa, "nome", None)),
        ("Sobre a empresa", getattr(empresa, "descricao", None)),
        ("Descrição da vaga", getattr(vaga, "descricao", None)),
        ("Instituição", getattr(vaga, "instituicao", None)),
        ("Prazo para candidatura", _formatar_data(getattr(vaga, "prazo", None))),
        ("Cidade", getattr(vaga, "cidade", None)),
        ("Local", getattr(vaga, "local", None)),
        ("Modalidade", getattr(vaga, "modalidade", None)),
        ("Área", getattr(vaga, "area", None)),
        ("Bolsa", _formatar_moeda(getattr(vaga, "bolsa", None))),
        ("Requisitos", getattr(vaga, "requisitos", None)),
        ("Vaga ativa", "Sim" if getattr(vaga, "ativa", False) else "Não"),
        ("Publicada em", _formatar_data(getattr(vaga, "publicada_em", None))),
    ]

    return "\n".join(
        f"{campo}: {_texto_ou_nao_informado(valor)}"
        for campo, valor in campos
    )


def _formatar_historico(historico):
    if not historico:
        return "(sem mensagens anteriores)"

    limite = int(getattr(settings, "GEMINI_HISTORY_LIMIT", 6))
    linhas = []

    for mensagem in historico[-limite:]:
        autor = mensagem.get("autor", "")
        texto = str(mensagem.get("texto", "") or "").strip()

        if not texto:
            continue

        papel = "Candidato" if autor == "candidato" else "Assistente"
        linhas.append(f"{papel}: {texto}")

    return "\n".join(linhas) or "(sem mensagens anteriores)"


def _pergunta_compatibilidade(pergunta):
    pergunta = _normalizar_texto(pergunta)

    termos = (
        "meu curso",
        "meu perfil",
        "compativel",
        "compatibilidade",
        "combina comigo",
        "combina com meu",
        "tem a ver comigo",
        "tem a ver com meu",
        "relacao com meu curso",
        "serve para meu curso",
        "eu atendo",
        "que eu atendo",
        "requisitos que atendo",
        "requisitos eu atendo",
        "atendo os requisitos",
        "sou adequado",
        "sou adequada",
        "faz sentido para mim",
    )

    return any(termo in pergunta for termo in termos)


def _resposta_direta_vaga(vaga, pergunta):
    pergunta = _normalizar_texto(pergunta)

    if any(
        termo in pergunta
        for termo in (
            "bolsa",
            "salario",
            "remuneracao",
            "quanto paga",
            "valor da vaga",
        )
    ):
        bolsa = getattr(vaga, "bolsa", None)
        if bolsa is None:
            return RESPOSTA_SEM_INFORMACAO
        return f"A bolsa dessa vaga é {_formatar_moeda(bolsa)}."

    if any(
        termo in pergunta
        for termo in (
            "modalidade",
            "remoto",
            "remota",
            "presencial",
            "hibrido",
            "home office",
        )
    ):
        modalidade = getattr(vaga, "modalidade", None)
        if not modalidade:
            return RESPOSTA_SEM_INFORMACAO
        return f"A modalidade dessa vaga é {modalidade}."

    if any(
        termo in pergunta
        for termo in (
            "onde fica",
            "localizacao",
            "local da vaga",
            "qual cidade",
            "cidade da vaga",
            "endereco",
        )
    ):
        cidade = getattr(vaga, "cidade", None)
        local = getattr(vaga, "local", None)

        partes = [
            str(valor).strip()
            for valor in (local, cidade)
            if valor and str(valor).strip()
        ]

        if not partes:
            return RESPOSTA_SEM_INFORMACAO

        return f"A vaga fica em {' - '.join(partes)}."

    if any(
        termo in pergunta
        for termo in (
            "requisito",
            "exigencia",
            "o que precisa",
        )
    ):
        requisitos = getattr(vaga, "requisitos", None)
        if not requisitos:
            return RESPOSTA_SEM_INFORMACAO
        return f"Os requisitos informados são: {requisitos}"

    if any(
        termo in pergunta
        for termo in (
            "prazo",
            "ate quando",
            "data limite",
            "ultimo dia",
        )
    ):
        prazo = getattr(vaga, "prazo", None)
        if not prazo:
            return RESPOSTA_SEM_INFORMACAO
        return f"O prazo para candidatura é {_formatar_data(prazo)}."

    if any(
        termo in pergunta
        for termo in (
            "qual empresa",
            "empresa da vaga",
            "empresa dessa vaga",
            "quem oferece",
        )
    ):
        empresa = getattr(vaga, "empresa", None)
        nome_empresa = getattr(empresa, "nome", None)
        if not nome_empresa:
            return RESPOSTA_SEM_INFORMACAO
        return f"A empresa responsável pela vaga é {nome_empresa}."

    if any(
        termo in pergunta
        for termo in (
            "qual area",
            "area da vaga",
            "area dessa vaga",
        )
    ):
        area = getattr(vaga, "area", None)
        if not area:
            return RESPOSTA_SEM_INFORMACAO
        return f"A área cadastrada para essa vaga é {area}."

    if any(
        termo in pergunta
        for termo in (
            "sobre a vaga",
            "descricao da vaga",
            "me explique a vaga",
            "o que vou fazer",
            "o que faz nessa vaga",
        )
    ):
        descricao = getattr(vaga, "descricao", None)
        if not descricao:
            return RESPOSTA_SEM_INFORMACAO
        return str(descricao).strip()

    return None


def _codigo_erro(exc):
    codigo = (
        getattr(exc, "code", None)
        or getattr(exc, "status_code", None)
    )

    if codigo is not None:
        try:
            return int(codigo)
        except (TypeError, ValueError):
            pass

    texto = str(exc).upper()

    if "DEADLINE_EXCEEDED" in texto or "504" in texto:
        return 504
    if "UNAVAILABLE" in texto or "HIGH DEMAND" in texto or "503" in texto:
        return 503
    if "RESOURCE_EXHAUSTED" in texto or "429" in texto:
        return 429
    if "408" in texto:
        return 408
    if "502" in texto:
        return 502
    if "500" in texto:
        return 500

    return None


def _erro_temporario(exc):
    return _codigo_erro(exc) in {408, 429, 500, 502, 503, 504}


def _modelos_para_tentar():
    principal = getattr(
        settings,
        "GEMINI_MODEL",
        "gemini-3.8-flash",
    ).strip()

    fallbacks = getattr(
        settings,
        "GEMINI_FALLBACK_MODELS",
        ["gemini-3.6-flash"],
    )

    modelos = [principal]

    for modelo in fallbacks:
        modelo = str(modelo).strip()
        if modelo and modelo not in modelos:
            modelos.append(modelo)

    return modelos[:2]


def _palavras_relevantes_curso(curso_nome):
    palavras_genericas = {
        "bacharelado",
        "licenciatura",
        "curso",
        "ciencia",
        "ciencias",
        "engenharia",
        "tecnologia",
        "superior",
        "gestao",
        "de",
        "da",
        "do",
        "das",
        "dos",
        "em",
        "e",
    }

    palavras = {
        palavra
        for palavra in _normalizar_texto(curso_nome).split()
        if len(palavra) >= 4 and palavra not in palavras_genericas
    }

    if not palavras:
        palavras = {
            palavra
            for palavra in _normalizar_texto(curso_nome).split()
            if len(palavra) >= 4
            and palavra not in {"de", "da", "do", "das", "dos", "em", "e"}
        }

    return palavras


def _resposta_compatibilidade_local(vaga, usuario, pergunta):
    perfil = _obter_perfil_usuario(usuario)

    if not perfil:
        return (
            "Não consegui avaliar a compatibilidade porque seu perfil "
            "acadêmico ainda não está preenchido."
        )

    curso = getattr(perfil, "curso", None)
    curso_nome = _valor_relacionado(curso)

    if curso_nome == "Não informado":
        return (
            "Cadastre seu curso no perfil para que eu consiga comparar "
            "seu perfil acadêmico com esta vaga."
        )

    pergunta_normalizada = _normalizar_texto(pergunta)

    if any(
        termo in pergunta_normalizada
        for termo in (
            "eu atendo",
            "que eu atendo",
            "requisitos eu atendo",
            "requisitos que atendo",
            "atendo os requisitos",
        )
    ):
        return (
            f"Seu curso de {curso_nome} pode ser comparado com a área da vaga, "
            "mas seu perfil ainda não possui habilidades e experiências "
            "detalhadas suficientes para eu afirmar quais requisitos você atende."
        )

    texto_vaga = _normalizar_texto(
        " ".join(
            str(valor or "")
            for valor in (
                getattr(vaga, "titulo", None),
                getattr(vaga, "area", None),
                getattr(vaga, "descricao", None),
                getattr(vaga, "requisitos", None),
            )
        )
    )

    palavras_curso = _palavras_relevantes_curso(curso_nome)
    encontrados = sorted(
        palavra
        for palavra in palavras_curso
        if palavra in texto_vaga
    )

    titulo = _texto_ou_nao_informado(getattr(vaga, "titulo", None))
    area = _texto_ou_nao_informado(getattr(vaga, "area", None))

    if encontrados:
        return (
            f"Há indícios de compatibilidade entre seu curso de {curso_nome} "
            f'e a vaga "{titulo}", principalmente pelos dados cadastrados '
            f"na área de {area}. A análise é parcial porque a IA externa "
            "está temporariamente indisponível."
        )

    return (
        f'Não encontrei uma relação acadêmica clara entre {curso_nome} e a '
        f'vaga "{titulo}" apenas pela comparação dos dados cadastrados. '
        "A análise é parcial porque a IA externa está temporariamente "
        "indisponível."
    )


def _criar_cliente(api_key, timeout_ms):
    return genai.Client(
        api_key=api_key,
        http_options=types.HttpOptions(
            timeout=int(timeout_ms),
            retry_options=types.HttpRetryOptions(
                attempts=1,
            ),
        ),
    )


def responder_sobre_vaga(vaga, pergunta, historico=None, usuario=None):
    pergunta = (pergunta or "").strip()

    if not vaga or not pergunta:
        return RESPOSTA_SEM_INFORMACAO

    eh_compatibilidade = _pergunta_compatibilidade(pergunta)

    # Perguntas factuais: resposta local imediata.
    if not eh_compatibilidade:
        resposta_direta = _resposta_direta_vaga(
            vaga=vaga,
            pergunta=pergunta,
        )

        if resposta_direta is not None:
            resposta_direta = str(resposta_direta).strip()

            if resposta_direta:
                logger.warning(
                    "Connecto IA: resposta local utilizada. "
                    "Gemini não foi chamado."
                )
                return resposta_direta

    # Compatibilidade ganha uma contingência local caso a API falhe.
    resposta_contingencia = None

    if eh_compatibilidade:
        resposta_contingencia = _resposta_compatibilidade_local(
            vaga=vaga,
            usuario=usuario,
            pergunta=pergunta,
        )

    api_key = getattr(settings, "GEMINI_API_KEY", "").strip()

    if not api_key:
        if resposta_contingencia:
            return resposta_contingencia

        raise GeminiConfigurationError(
            "GEMINI_API_KEY não está configurada no ambiente do servidor."
        )

    timeout_ms = max(
        10000,
        int(getattr(settings, "GEMINI_REQUEST_TIMEOUT_MS", 12000)),
    )

    orcamento_total_ms = max(
        10000,
        int(getattr(settings, "GEMINI_TOTAL_BUDGET_MS", 16000)),
    )

    contexto_vaga = _formatar_contexto_vaga(vaga)
    contexto_candidato = _formatar_contexto_candidato(usuario)

    prompt = f"""
FONTES FACTUAIS AUTORIZADAS — DADOS DO CONNECTO:

<dados_candidato>
{contexto_candidato}
</dados_candidato>

<dados_vaga>
{contexto_vaga}
</dados_vaga>

<historico>
{_formatar_historico(historico)}
</historico>

<pergunta_atual>
{pergunta}
</pergunta_atual>

REGRAS:
- Responda em português do Brasil.
- Use somente os dados fornecidos pelo Connecto.
- Seja direto, natural e curto.
- Prefira 1 ou 2 frases.
- Para compatibilidade, compare principalmente curso, título, área,
  descrição e requisitos.
- Não invente experiências ou habilidades do candidato.
- Não invente informações da vaga.
- O histórico serve somente para continuidade da conversa.
- Campos marcados como "Não informado" não podem ser preenchidos por suposição.
- Se realmente não houver dados suficientes, responda exatamente:
  "{RESPOSTA_SEM_INFORMACAO}"
""".strip()

    modelos = _modelos_para_tentar()
    ultimo_erro = None
    inicio_total = time.perf_counter()

    for indice, modelo in enumerate(modelos, start=1):
        decorrido_ms = int((time.perf_counter() - inicio_total) * 1000)
        restante_ms = orcamento_total_ms - decorrido_ms

        # O Gemini exige deadline mínimo próximo de 10 segundos.
        # Não começamos outra requisição se o orçamento restante for menor.
        if restante_ms < 10000:
            logger.warning(
                "Connecto IA: fallback não iniciado; "
                "orçamento restante insuficiente (%s ms).",
                restante_ms,
            )
            break

        timeout_modelo_ms = min(timeout_ms, restante_ms)
        inicio_modelo = time.perf_counter()

        try:
            client = _criar_cliente(
                api_key=api_key,
                timeout_ms=timeout_modelo_ms,
            )

            response = client.models.generate_content(
                model=modelo,
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=CONNECTO_SYSTEM_MESSAGE,
                    temperature=0.1,
                    max_output_tokens=384,
                ),
            )

            texto = (response.text or "").strip()

            if not texto:
                ultimo_erro = GeminiResponseError(
                    "A Gemini API não retornou texto utilizável."
                )

                logger.warning(
                    "Connecto IA retornou resposta vazia: "
                    "modelo=%s tentativa=%s",
                    modelo,
                    indice,
                )

                continue

            duracao_modelo_ms = int(
                (time.perf_counter() - inicio_modelo) * 1000
            )
            duracao_total_ms = int(
                (time.perf_counter() - inicio_total) * 1000
            )

            logger.warning(
                "Connecto IA respondeu: modelo=%s tentativa=%s "
                "duracao_modelo_ms=%s duracao_total_ms=%s",
                modelo,
                indice,
                duracao_modelo_ms,
                duracao_total_ms,
            )

            return texto

        except Exception as exc:
            ultimo_erro = exc
            codigo = _codigo_erro(exc)

            duracao_modelo_ms = int(
                (time.perf_counter() - inicio_modelo) * 1000
            )

            logger.warning(
                "Connecto IA falhou: modelo=%s tentativa=%s "
                "duracao_ms=%s codigo=%s erro=%s",
                modelo,
                indice,
                duracao_modelo_ms,
                codigo,
                exc,
            )

            if not _erro_temporario(exc):
                raise

            # 504 já consumiu praticamente todo o deadline.
            # Não começamos outra chamada longa.
            if codigo == 504:
                break

            # 408/429/500/502/503 podem seguir para o único fallback,
            # desde que ainda haja orçamento suficiente.
            continue

    if resposta_contingencia:
        logger.warning(
            "Connecto IA: usando resposta local de contingência "
            "para compatibilidade após falha da API."
        )
        return resposta_contingencia

    duracao_total_ms = int(
        (time.perf_counter() - inicio_total) * 1000
    )

    raise GeminiResponseError(
        "Gemini indisponível após tentativa controlada "
        f"({duracao_total_ms} ms): {ultimo_erro}"
    )
