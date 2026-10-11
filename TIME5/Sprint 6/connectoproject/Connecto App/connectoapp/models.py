from django.db import models

# Create your models here.
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
    descricao = models.TextField()

    def __str__(self):
        return self.nome


class Oportunidade(models.Model):
    titulo = models.CharField(max_length=100)
    descricao = models.TextField()
    instituicao = models.CharField(max_length=100)
    prazo = models.DateField()
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE)

    def __str__(self):
        return self.titulo


class Candidatura(models.Model):
    data_candidatura = models.DateField()
    status = models.CharField(max_length=50)
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE)
    oportunidade = models.ForeignKey(Oportunidade, on_delete=models.CASCADE)


class Favorito(models.Model):
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE)
    oportunidade = models.ForeignKey(Oportunidade, on_delete=models.CASCADE)
