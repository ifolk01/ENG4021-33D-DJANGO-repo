from django.db import migrations, models
#mudança aqui 
#criação pelo migration
def marcar_mensagens_antigas_como_lidas(
    apps,
    schema_editor,
):
    Mensagem = apps.get_model(
        "connectoapp",
        "Mensagem",
    )

    Mensagem.objects.all().update(
        lida_pelo_candidato=True
    )


class Migration(migrations.Migration):

    dependencies = [
        ("connectoapp", "0007_merge_20261106_0953"),
    ]

    operations = [
        migrations.AddField(
            model_name="mensagem",
            name="lida_pelo_candidato",
            field=models.BooleanField(default=False),
        ),

        migrations.RunPython(
            marcar_mensagens_antigas_como_lidas,
            migrations.RunPython.noop,
        ),
    ]