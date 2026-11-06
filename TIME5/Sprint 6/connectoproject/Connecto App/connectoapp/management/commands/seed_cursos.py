from django.core.management.base import BaseCommand

from connectoapp.models import Curso


CURSOS = [
    "Administração",
    "Arquitetura e Urbanismo",
    "Biomedicina",
    "Análise e Desenvolvimento de Sistemas",
    "Comércio Exterior",
    "Ciência da Computação",
    "Ciências Contábeis",
    "Ciências Econômicas",
    "Design",
    "Direito",
    "Engenharia Ambiental",
    "Engenharia Civil",
    "Engenharia da Computação",
    "Engenharia de Produção",
    "Engenharia Elétrica",
    "Engenharia Mecânica",
    "Engenharia Química",
    "Educação Física",
    "Economia",
    "Estatística",
    "Enfermagem",
    "Fisioterapia",
    "Farmácia",
    "Jornalismo",
    "Matemática",
    "Medicina Veterinária",
    "Medicina",
    "Nutrição",
    "Odontologia",
    "Psicologia",
    "Publicidade",
    "Relações Internacionais",
    "Sistemas de Informação",
]


class Command(BaseCommand):
    help = "Cria os cursos disponíveis no Connecto"

    def handle(self, *args, **options):
        criados = 0

        for nome in CURSOS:
            _, criado = Curso.objects.get_or_create(
                nome=nome
            )

            if criado:
                criados += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"{criados} cursos criados. "
                f"Total: {Curso.objects.count()}."
            )
        )