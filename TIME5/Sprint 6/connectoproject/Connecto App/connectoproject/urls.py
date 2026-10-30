from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

from connectoapp import views

urlpatterns = [
    path("admin/", admin.site.urls),

    path("i18n/", include("django.conf.urls.i18n")),

    path("", views.login, name="login"),
    path("criar-conta/", views.criar_conta, name="criar_conta"),

    path("home/", views.home, name="home"),
    path("busca/", views.busca, name="busca"),
    path("perfil/", views.perfil, name="perfil"),

    path("match/", views.match, name="match"),
    path("match/<int:vaga_id>/acao/", views.match_acao, name="match_acao"),

    path("candidaturas/", views.candidaturas, name="candidaturas"),
    path("favoritas/", views.favoritas, name="favoritas"),
    path("candidatar/<int:vaga_id>/", views.candidatar, name="candidatar"),

    path("mensagens/", views.mensagens, name="mensagens"),
    path("mensagens/<int:conversa_id>/", views.conversa, name="conversa"),

    path("vaga/", views.visualizacao_vaga, name="visualizacao_vaga"),
    path("vaga/<int:vaga_id>/", views.visualizacao_vaga, name="detalhe_vaga"),
    path(
    "favoritar/<int:vaga_id>/",views.toggle_favorito,name="toggle_favorito"),
    path("notificacoes/", views.notificacoes, name="notificacoes"),
    #path("notificacoes/verificar/", views.verificar_notificacoes, name="notificacoes_verificar"),
    path("configuracoes/", views.configuracoes, name="configuracoes"),
    
    path("esqueceu-senha/", views.esqueceu_senha, name="esqueceu_senha"),

    path(
    "duvidas-frequentes/",
    views.duvidas_frequentes,
    name="duvidas_frequentes"
),
]

if settings.DEBUG:
    urlpatterns += static(
        settings.MEDIA_URL,
        document_root=settings.MEDIA_ROOT
    )
