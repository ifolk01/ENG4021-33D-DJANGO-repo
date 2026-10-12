from django.conf import settings
from django.db import models


class Curso(models.Model):
    nome = models.CharField(max_length=100)

    def __str__(self):
        return self.nome



class Usuario(models.Model):
    nome = models.CharField(max_length=100)
    email = models.EmailField()
    senha = models.CharField(max_length=100)
    periodo = models.IntegerField()
    curso = models.ForeignKey(Curso, on_delete=models.CASCADE)

    def __str__(self):
        return self.nome


class Empresa(models.Model):
    nome = models.CharField(max_length=100)
    email = models.EmailField()
    descricao = models.TextField(blank=True)

    def __str__(self):
        return self.nome

    @property
    def iniciais(self):
        partes = [parte for parte in self.nome.split() if parte]
        return "".join(parte[0] for parte in partes[:2]).upper() or "EM"


class Oportunidade(models.Model):
    MODALIDADES = [
        ("Presencial", "Presencial"),
        ("Híbrido", "Híbrido"),
        ("Remoto", "Remoto"),
    ]

    titulo = models.CharField(max_length=120)
    descricao = models.TextField()
    instituicao = models.CharField(max_length=100, blank=True)
    prazo = models.DateField(null=True, blank=True)
    empresa = models.ForeignKey(
        Empresa,
        on_delete=models.CASCADE,
        related_name="oportunidades",
    )

    cidade = models.CharField(max_length=100, blank=True)
    local = models.CharField(max_length=150, blank=True)
    modalidade = models.CharField(
        max_length=20,
        choices=MODALIDADES,
        default="Presencial",
    )
    area = models.CharField(max_length=100, blank=True)
    bolsa = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    requisitos = models.TextField(blank=True, help_text="Um requisito por linha")
    ativa = models.BooleanField(default=True)
    publicada_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-publicada_em", "-id"]

    def __str__(self):
        return self.titulo

    @property
    def publicada(self):
        return "Publicada recentemente"

    @property
    def sobre_empresa(self):
        return self.empresa.descricao

    @property
    def lista_requisitos(self):
        return [linha.strip() for linha in self.requisitos.splitlines() if linha.strip()]


class Candidatura(models.Model):
    ORIGENS = [
        ("home", "Home"),
        ("match", "Match"),
        ("detalhe", "Detalhe da vaga"),
    ]

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="candidaturas_connecto",
    )
    oportunidade = models.ForeignKey(
        Oportunidade,
        on_delete=models.CASCADE,
        related_name="candidaturas",
    )
    data_candidatura = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=50, default="Enviada")
    origem = models.CharField(max_length=20, choices=ORIGENS, default="home")

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["usuario", "oportunidade"],
                name="candidatura_usuario_oportunidade_unica",
            )
        ]
        ordering = ["-data_candidatura"]

    def __str__(self):
        return f"{self.usuario} -> {self.oportunidade}"


class Favorito(models.Model):
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="favoritos_connecto",
    )
    oportunidade = models.ForeignKey(
        Oportunidade,
        on_delete=models.CASCADE,
        related_name="favoritos",
    )
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["usuario", "oportunidade"],
                name="favorito_usuario_oportunidade_unico",
            )
        ]


class VagaDescartada(models.Model):
   

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="vagas_descartadas_connecto",
    )
    oportunidade = models.ForeignKey(
        Oportunidade,
        on_delete=models.CASCADE,
        related_name="descartes_match",
    )
    criada_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["usuario", "oportunidade"],
                name="descarte_usuario_oportunidade_unico",
            )
        ]


class Conversa(models.Model):
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="conversas_connecto",
    )
    oportunidade = models.ForeignKey(
        Oportunidade,
        on_delete=models.CASCADE,
        related_name="conversas",
    )
    criada_em = models.DateTimeField(auto_now_add=True)
    atualizada_em = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["usuario", "oportunidade"],
                name="conversa_usuario_oportunidade_unica",
            )
        ]
        ordering = ["-atualizada_em"]

    def __str__(self):
        return f"{self.usuario} x {self.oportunidade.empresa}"


class Mensagem(models.Model):
    AUTORES = [
        ("empresa", "Empresa"),
        ("candidato", "Candidato"),
    ]

    conversa = models.ForeignKey(
        Conversa,
        on_delete=models.CASCADE,
        related_name="mensagens",
    )
    autor = models.CharField(max_length=20, choices=AUTORES)
    texto = models.TextField()
    criada_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["criada_em", "id"]

    def __str__(self):
        return f"{self.get_autor_display()}: {self.texto[:40]}"
