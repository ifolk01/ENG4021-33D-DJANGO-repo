from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login as auth_login
from django.contrib.auth.models import User
from django.http import Http404



def login(request):
    if request.method == "POST":
       
        matricula = request.POST.get('username', '').strip()
        senha = request.POST.get('password', '')

       
        user = authenticate(request, username=matricula, password=senha)

        if user is not None:
            auth_login(request, user)
            return redirect('home')
        else:
            # Se falhar, devolve um erro visual para a página de login
            return render(request, "Login.html", {"erro": "Matrícula ou senha incorretos. Tente novamente."})

    return render(request, "Login.html")


def criar_conta(request):
    if request.method == "POST":
        nome = request.POST.get('nome', '') # Recolhe o nome completo
        matricula = request.POST.get('username', '').strip()
        senha = request.POST.get('password', '')
        confirmar_senha = request.POST.get('confirmar_senha', '')

        # Trava 1: Verifica se as duas senhas são iguais
        if senha != confirmar_senha:
            return render(request, "criar_conta.html", {"erro": "As senhas não coincidem!"})

        # Trava 2: Verifica se a matrícula já existe
        if User.objects.filter(username=matricula).exists():
            return render(request, "criar_conta.html", {"erro": "Esta matrícula já está registada."})
        
        
        user = User.objects.create_user(username=matricula, password=senha, first_name=nome)
        user.save()
        
        return redirect('login')

    return render(request, "criar_conta.html")



# Home 
def home(request):
    return render(request, "home.html")

# Tela de Busca 
def busca(request):
    return render(request, "Tela_Joao_Felipe.html")

# Tela de Perfil
# View + URL (Sprint 6 - João Henrique): a view monta os dados do perfil e
# envia para o template pelo contexto. Se houver usuário logado, usa o nome,
# a matrícula (username) e o e-mail dele; senão, mostra um perfil de exemplo.
def perfil(request):
    usuario = request.user

    if usuario.is_authenticated:
        nome = usuario.first_name or usuario.username
        matricula = usuario.username
        email = usuario.email or "Não informado"
    else:
        nome = "Lucas Silva"
        matricula = "2510335"
        email = "lucas.silva@email.com"

    # Iniciais para o avatar (ex.: "Lucas Silva" -> "LS")
    iniciais = "".join(parte[0] for parte in nome.split()[:2]).upper()

    contexto = {
        "nome": nome,
        "iniciais": iniciais,
        "matricula": matricula,
        "email": email,
        "curso": "Ciência da Computação",
        "instituicao": "PUC-Rio",
        # Contadores ainda fixos; depois virão das tabelas Candidatura/Favorito
        "total_candidaturas": 2,
        "total_salvas": 2,
        "total_conversas": 0,
    }
    return render(request, "perfil_melhorada.html", contexto)

# Tela de Candidaturas / Favoritas
def candidaturas(request):
    return render(request, "candidaturas.html")

def favoritas(request):
    return render(request, "favoritas.html")

# Tela de Visualização de Vaga Única
# View + URL (Sprint 6 - João Henrique): a vaga agora é escolhida pelo id na
# URL (/vaga/1/, /vaga/2/...). Enquanto o models.py/migrações não estão no
# ar, os dados vêm desta lista de exemplo; depois basta trocar por
# get_object_or_404(Oportunidade, pk=vaga_id).
VAGAS_EXEMPLO = {
    1: {
        "titulo": "Estágio em Desenvolvimento de Software",
        "empresa": "Empresa ABC",
        "cidade": "Rio de Janeiro",
        "local": "Botafogo - RJ",
        "modalidade": "Presencial",
        "area": "Tecnologia",
        "bolsa": "R$ 2.000",
        "prazo": "30/10/2026",
        "publicada": "Publicada recentemente",
        "descricao": "Buscamos um estagiário para auxiliar no desenvolvimento de software e participar dos projetos da equipe.",
        "requisitos": [
            "Estar cursando graduação em Computação, Engenharia ou áreas afins",
            "Interesse em tecnologia e desenvolvimento de software",
            "Conhecimentos básicos de Python ou JavaScript",
        ],
        "sobre_empresa": "A Empresa ABC atua na área de tecnologia e desenvolvimento de soluções digitais.",
    },
    2: {
        "titulo": "Estágio em Desenvolvimento iOS",
        "empresa": "TechRio Mobile",
        "cidade": "Rio de Janeiro",
        "local": "Centro - RJ",
        "modalidade": "Híbrido",
        "area": "Tecnologia",
        "bolsa": "R$ 1.800",
        "prazo": "15/11/2026",
        "publicada": "Publicada recentemente",
        "descricao": "Participe do desenvolvimento de aplicativos iOS junto ao time de produto, do protótipo à publicação na App Store.",
        "requisitos": [
            "Cursando a partir do 3º período",
            "Noções de Swift ou de outra linguagem orientada a objetos",
            "Vontade de aprender e trabalhar em equipe",
        ],
        "sobre_empresa": "A TechRio Mobile desenvolve aplicativos para startups e grandes empresas do Rio.",
    },
}


def visualizacao_vaga(request, vaga_id=1):
    vaga = VAGAS_EXEMPLO.get(vaga_id)
    if vaga is None:
        raise Http404("Vaga não encontrada")
    return render(request, "visualizacao_vaga_melhorada.html", {"vaga": vaga, "vaga_id": vaga_id})