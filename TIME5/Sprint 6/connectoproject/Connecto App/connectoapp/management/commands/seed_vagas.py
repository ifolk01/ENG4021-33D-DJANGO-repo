
from datetime import date

from django.core.management.base import BaseCommand

from connectoapp.models import Empresa, Oportunidade


class Command(BaseCommand):
    help = "Cria uma base de vagas de demonstração para Home e Match."

    def add_arguments(self, parser):
        parser.add_argument(
            "--quantidade",
            type=int,
            default=60,
            help="Quantidade máxima de vagas demo a criar (padrão: 60).",
        )

    def handle(self, *args, **options):
        quantidade = max(1, min(options["quantidade"], 60))

        empresas = [
            ("TechRio Mobile", "jobs@techrio.example", "Produtos digitais e desenvolvimento mobile."),
            ("Globo", "talentos@globo.example", "Mídia, entretenimento e tecnologia."),
            ("Itaú Unibanco", "estagios@itau.example", "Serviços financeiros e produtos digitais."),
            ("Nubank", "talentos@nubank.example", "Tecnologia aplicada a serviços financeiros."),
            ("Stone", "estagio@stone.example", "Tecnologia e serviços financeiros."),
            ("99", "talentos@99.example", "Mobilidade urbana e produtos digitais."),
            ("CB Bank", "talentos@cbbank.example", "Banco digital e soluções de dados."),
            ("Construtora Tenda", "estagio@tenda.example", "Construção civil e desenvolvimento urbano."),
            ("Vale", "talentos@vale.example", "Mineração, logística e engenharia."),
            ("WEG", "estagios@weg.example", "Tecnologia industrial e energia."),
            ("CSN", "talentos@csn.example", "Indústria, mineração e infraestrutura."),
            ("Sabesp", "estagios@sabesp.example", "Saneamento, engenharia e meio ambiente."),
        ]

        vagas_base = [
            ("Estágio em Desenvolvimento iOS", "Tecnologia", "Desenvolvimento de funcionalidades mobile com foco em qualidade, testes e experiência do usuário.", "Noções de Swift\nGit\nOrientação a objetos"),
            ("Estagiário de Engenharia de Software", "Tecnologia", "Atuação com desenvolvimento de software, APIs, integração contínua e boas práticas de engenharia.", "Lógica de programação\nGit\nInteresse em backend"),
            ("Estagiário Full Stack", "Tecnologia", "Apoio no desenvolvimento de aplicações web, integrações e evolução de produtos digitais.", "HTML e CSS\nJavaScript\nNoções de APIs"),
            ("Estágio em DevOps / Infraestrutura", "Tecnologia", "Apoio em pipelines, automações, observabilidade e infraestrutura em nuvem.", "Linux básico\nGit\nInteresse em cloud"),
            ("Estagiário de UX/UI Design", "Design", "Apoio em pesquisa, prototipação e evolução da experiência de produtos digitais.", "Figma\nNoções de UX\nPortfólio acadêmico"),
            ("Estagiário em Ciência de Dados", "Dados BI", "Análise de dados, construção de indicadores e apoio a modelos analíticos.", "Python básico\nSQL\nRaciocínio analítico"),
            ("Estágio em Analytics", "Dados BI", "Criação de dashboards, acompanhamento de métricas e apoio a decisões de negócio.", "Excel\nSQL básico\nPower BI"),
            ("Estágio em Engenharia Civil", "Engenharia", "Acompanhamento de obras, planejamento e apoio aos controles de engenharia.", "Excel\nLeitura de projetos\nOrganização"),
            ("Estágio em Engenharia de Minas", "Engenharia", "Apoio técnico a operações, indicadores de produção e segurança operacional.", "Excel\nNoções de mineração\nTrabalho em equipe"),
            ("Estágio em Engenharia de Petróleo", "Engenharia", "Apoio a estudos técnicos, análise de dados operacionais e documentação de projetos.", "Excel\nInglês intermediário\nRaciocínio analítico"),
            ("Estágio em Engenharia Elétrica", "Engenharia", "Suporte a projetos elétricos, manutenção, documentação e análise de indicadores.", "Circuitos básicos\nExcel\nOrganização"),
            ("Estágio em Engenharia de Produção", "Engenharia", "Melhoria de processos, indicadores e apoio ao planejamento operacional.", "Excel\nProcessos\nComunicação"),
            ("Estágio em Engenharia Ambiental", "Meio Ambiente", "Apoio a projetos ambientais, indicadores e conformidade de operações.", "Excel\nGestão ambiental\nRelatórios"),
            ("Estágio em Psicologia Organizacional", "Recursos Humanos", "Apoio a recrutamento, desenvolvimento e iniciativas de experiência das pessoas.", "Comunicação\nOrganização\nPacote Office"),
            ("Estágio em Marketing Digital", "Marketing", "Apoio a campanhas, conteúdo, métricas e comunicação digital.", "Redes sociais\nExcel\nBoa escrita"),
            ("Estágio em Finanças", "Finanças", "Apoio em controles, orçamento, análises financeiras e relatórios gerenciais.", "Excel\nMatemática financeira\nOrganização"),
            ("Estágio em Logística", "Logística", "Acompanhamento de fluxo operacional, indicadores e melhoria de processos logísticos.", "Excel\nOrganização\nRaciocínio analítico"),
            ("Estágio Pedagógico", "Educação", "Apoio a projetos educacionais, organização de conteúdos e acompanhamento de atividades.", "Comunicação\nOrganização\nInteresse em educação"),
            ("Estágio em Relações Internacionais", "Relações Internacionais", "Apoio a pesquisas, relatórios e relacionamento com parceiros institucionais.", "Inglês intermediário\nBoa escrita\nPesquisa"),
            ("Estágio em Negócios", "Negócios", "Apoio a análises de mercado, estratégia comercial e acompanhamento de indicadores.", "Excel\nApresentações\nRaciocínio analítico"),
        ]

        cidades = [
            ("Rio de Janeiro", "Rio de Janeiro - RJ"),
            ("São Paulo", "São Paulo - SP"),
            ("Belo Horizonte", "Belo Horizonte - MG"),
            ("Fortaleza", "Fortaleza - CE"),
            ("Volta Redonda", "Volta Redonda - RJ"),
        ]
        modalidades = ["Híbrido", "Remoto", "Presencial"]

        criadas = 0
        existentes = 0

        # 20 cargos x 12 empresas geram 60 pares diferentes antes de repetir.
        for i in range(quantidade):
            titulo, area, descricao, requisitos = vagas_base[i % len(vagas_base)]
            nome_empresa, email, sobre = empresas[(i * 7) % len(empresas)]
            cidade, local = cidades[(i * 3) % len(cidades)]
            modalidade = modalidades[i % len(modalidades)]
            bolsa = 1800 + ((i * 100) % 1100)

            empresa, _ = Empresa.objects.get_or_create(
                nome=nome_empresa,
                defaults={"email": email, "descricao": sobre},
            )

            _, criada = Oportunidade.objects.get_or_create(
                titulo=titulo,
                empresa=empresa,
                defaults={
                    "descricao": descricao,
                    "instituicao": "PUC-Rio",
                    "prazo": date(2026, 12, 20),
                    "cidade": cidade,
                    "local": local,
                    "modalidade": modalidade,
                    "area": area,
                    "bolsa": bolsa,
                    "requisitos": requisitos,
                    "ativa": True,
                },
            )

            if criada:
                criadas += 1
            else:
                existentes += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Seed concluído: {criadas} vagas criadas e {existentes} já existentes."
            )
        )
