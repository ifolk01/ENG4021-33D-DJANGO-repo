from datetime import date

from django.core.management.base import BaseCommand

from connectoapp.models import Empresa, Oportunidade


class Command(BaseCommand):
    help = "Cria empresas e vagas de exemplo para testar Home, Match e Mensagens."

    def handle(self, *args, **options):
        vagas = [
            {
                "empresa": "Globo",
                "email": "talentos@globo.com",
                "sobre": "Empresa de mídia e tecnologia.",
                "titulo": "Estagiário de Engenharia de Software",
                "descricao": (
                    "Atue no time de backend do Globoplay, trabalhando com "
                    "microsserviços e integração contínua. Procuramos perfis "
                    "focados em código e arquitetura de software."
                ),
                "cidade": "Rio de Janeiro",
                "local": "Rio de Janeiro - RJ",
                "modalidade": "Remoto",
                "area": "Tecnologia",
                "bolsa": 2200,
                "prazo": date(2026, 12, 20),
                "requisitos": "Noções de programação\nGit\nVontade de aprender",
            },
            {
                "empresa": "Itaú Unibanco",
                "email": "estagios@itau.com.br",
                "sobre": "Instituição financeira com atuação nacional.",
                "titulo": "Estagiário em Dados",
                "descricao": "Apoie análises, indicadores e automações para produtos digitais e times de negócio.",
                "cidade": "São Paulo",
                "local": "São Paulo - SP",
                "modalidade": "Híbrido",
                "area": "Dados BI",
                "bolsa": 2300,
                "prazo": date(2026, 12, 15),
                "requisitos": "Python básico\nSQL básico\nRaciocínio analítico",
            },
            {
                "empresa": "TechRio Mobile",
                "email": "jobs@techrio.example",
                "sobre": "Empresa de desenvolvimento de produtos mobile.",
                "titulo": "Estágio em Desenvolvimento iOS",
                "descricao": "Participe do desenvolvimento de aplicativos iOS junto ao time de produto.",
                "cidade": "Rio de Janeiro",
                "local": "Centro - RJ",
                "modalidade": "Híbrido",
                "area": "Tecnologia",
                "bolsa": 1800,
                "prazo": date(2026, 11, 15),
                "requisitos": "Noções de Swift\nOrientação a objetos\nTrabalho em equipe",
            },
            {
                "empresa": "Stone",
                "email": "estagio@stone.com.br",
                "sobre": "Empresa de tecnologia e serviços financeiros.",
                "titulo": "Estágio em DevOps / Infraestrutura",
                "descricao": "Apoie pipelines, automações e infraestrutura em nuvem junto ao time de engenharia.",
                "cidade": "Rio de Janeiro",
                "local": "Rio de Janeiro - RJ",
                "modalidade": "Híbrido",
                "area": "Tecnologia",
                "bolsa": 2100,
                "prazo": date(2026, 12, 10),
                "requisitos": "Linux básico\nGit\nInteresse em cloud",
            },
            {
                "empresa": "99",
                "email": "talentos@99app.com",
                "sobre": "Plataforma de mobilidade e tecnologia.",
                "titulo": "Estagiário de UX/UI Design",
                "descricao": "Apoie pesquisas, protótipos e evolução da experiência dos produtos digitais.",
                "cidade": "São Paulo",
                "local": "São Paulo - SP",
                "modalidade": "Remoto",
                "area": "Design",
                "bolsa": 2000,
                "prazo": date(2026, 12, 5),
                "requisitos": "Figma\nNoções de UX\nPortfólio acadêmico",
            },
        ]

        for item in vagas:
            empresa, _ = Empresa.objects.get_or_create(
                nome=item["empresa"],
                defaults={
                    "email": item["email"],
                    "descricao": item["sobre"],
                },
            )
            Oportunidade.objects.get_or_create(
                titulo=item["titulo"],
                empresa=empresa,
                defaults={
                    "descricao": item["descricao"],
                    "instituicao": "PUC-Rio",
                    "prazo": item["prazo"],
                    "cidade": item["cidade"],
                    "local": item["local"],
                    "modalidade": item["modalidade"],
                    "area": item["area"],
                    "bolsa": item["bolsa"],
                    "requisitos": item["requisitos"],
                    "ativa": True,
                },
            )

        self.stdout.write(self.style.SUCCESS("Vagas de exemplo criadas/confirmadas com sucesso."))
