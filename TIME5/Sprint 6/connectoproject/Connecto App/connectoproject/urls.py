from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import TemplateView

from connectoapp import views

urlpatterns = [
    path("admin/", admin.site.urls),

    path("i18n/", include("django.conf.urls.i18n")),

    path("", views.login, name="login"),
    path("criar-conta/", views.criar_conta, name="criar_conta"),

    path("home/", views.home, name="home"),
    path("busca/", views.busca, name="busca"),
    path("perfil/", views.perfil, name="perfil"),
    path("editar-perfil/", views.editar_perfil, name="editar_perfil"),
    path("perfil-empresa/", views.perfil_empresa, name="perfil_empresa"),

    path("match/", views.match, name="match"),
    path("match/<int:vaga_id>/acao/", views.match_acao, name="match_acao"),

    path("candidaturas/", views.candidaturas, name="candidaturas"),
    path("empresa/candidaturas/",views.candidaturas_empresa,name="candidaturas_empresa",),
    path("empresa/candidaturas/<int:candidatura_id>/status/",views.atualizar_status_candidatura, name="atualizar_status_candidatura",),
    
    path("favoritas/", views.favoritas, name="favoritas"),
    path("candidatar/<int:vaga_id>/", views.candidatar, name="candidatar"),

    path("mensagens/", views.mensagens, name="mensagens"),
    path("mensagens/<int:conversa_id>/", views.conversa, name="conversa"),
    path("mensagens/<int:conversa_id>/assistente/",views.assistente_vaga,name="assistente_vaga"),

    path("vaga/", views.visualizacao_vaga, name="visualizacao_vaga"),
    path("vaga/<int:vaga_id>/", views.visualizacao_vaga, name="detalhe_vaga"),
    path("candidaturas/<int:candidatura_id>/",views.detalhe_candidatura,name="detalhe_candidatura"),
    path(
    "favoritar/<int:vaga_id>/",views.toggle_favorito,name="toggle_favorito"),
    path("notificacoes/", views.notificacoes, name="notificacoes"),
    path("notificacoes/verificar/", views.verificar_notificacoes, name="notificacoes_verificar"),
    path("configuracoes/", views.configuracoes, name="configuracoes"),
    
    path("esqueceu-senha/", views.esqueceu_senha, name="esqueceu_senha"),

    path("duvidas-frequentes/",views.duvidas_frequentes,name="duvidas_frequentes"),
    path("notificacoes/push/subscribe/",views.push_subscribe,name="push_subscribe"),
    path("service-worker.js",TemplateView.as_view(template_name="service-worker.js",content_type="application/javascript"),name="service_worker"),
]

if settings.DEBUG:
    urlpatterns += static(
        settings.MEDIA_URL,
        document_root=settings.MEDIA_ROOT
    )
