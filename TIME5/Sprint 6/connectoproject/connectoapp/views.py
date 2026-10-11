from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login as auth_login
from django.contrib.auth.models import User



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