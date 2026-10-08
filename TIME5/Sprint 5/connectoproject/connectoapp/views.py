from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login as auth_login
from django.contrib.auth.models import User


def login(request):
    if request.method == "POST":
        # Recolhe os dados enviados pelo HTML
        matricula = request.POST.get('username')
        senha = request.POST.get('password')

        # O Django verifica se existe um utilizador com esta matrícula e palavra-passe
        user = authenticate(request, username=matricula, password=senha)

        if user is not None:
            # Se os dados estiverem corretos, faz o login e envia para a Home
            auth_login(request, user)
            return redirect('home')
        else:
            # Se falhar, devolve o ecrã de login com uma mensagem de erro
            return render(request, "Login.html", {"erro": "Matrícula ou senha incorretos."})

    # Se for apenas aceder à página (GET), mostra o formulário vazio
    return render(request, "Login.html")


def criar_conta(request):
    if request.method == "POST":
        matricula = request.POST.get('username')
        senha = request.POST.get('password')

        # Verifica se a matrícula já existe na base de dados
        if User.objects.filter(username=matricula).exists():
            return render(request, "criar_conta.html", {"erro": "Esta matrícula já está registada."})
        else:
            # Cria o utilizador de forma segura na base de dados do Django
            user = User.objects.create_user(username=matricula, password=senha)
            user.save()
            # Redireciona para o login para que o utilizador possa entrar
            return redirect('login')

    return render(request, "criar_conta.html")

# Tela Inicial 
def login(request):
    return render(request, "Login.html")

# Home 
def home(request):
    return render(request, "home.html")

# Tela de Busca 
def busca(request):
    return render(request, "Tela_Joao_Felipe.html")

# Tela de Perfil
def perfil(request):
    return render(request, "perfil.html")

# Tela de Candidaturas / Favoritas
def candidaturas(request):
    return render(request, "candidaturas.html")

def favoritas(request):
    return render(request, "favoritas.html")

# Tela de Visualização de Vaga Única
def visualizacao_vaga(request):
    return render(request, "visualizacao_vaga.html")