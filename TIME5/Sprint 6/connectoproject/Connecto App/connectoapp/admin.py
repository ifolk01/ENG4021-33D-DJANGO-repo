# ADICIONE ESTE BLOCO A connectoapp/admin.py
# Se o arquivo ainda não importar admin, mantenha: from django.contrib import admin

from .models import SolicitacaoSuporte
from django.contrib import admin


@admin.register(SolicitacaoSuporte)
class SolicitacaoSuporteAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "assunto",
        "usuario",
        "tipo_conta",
        "status",
        "email_enviado",
        "criada_em",
    )
    list_filter = (
        "status",
        "tipo_conta",
        "email_enviado",
        "criada_em",
    )
    search_fields = (
        "assunto",
        "mensagem",
        "usuario__username",
        "usuario__first_name",
        "usuario__last_name",
        "usuario__email",
        "empresa__nome",
    )
    list_editable = ("status",)
    readonly_fields = (
        "usuario",
        "empresa",
        "tipo_conta",
        "assunto",
        "mensagem",
        "email_enviado",
        "criada_em",
        "atualizada_em",
    )
    date_hierarchy = "criada_em"
    ordering = ("-criada_em",)
    list_per_page = 30
