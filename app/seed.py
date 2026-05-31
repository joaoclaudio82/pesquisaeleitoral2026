"""
Seed — popula o banco com dados iniciais de candidatos e notícias.
Chamado uma única vez na inicialização da aplicação se o banco estiver vazio.
"""
import random
from datetime import datetime, timedelta

from .database import db
from .models   import Candidato, Noticia, Historico
from .services import HistoricoService


# ── Dados iniciais dos candidatos ─────────────────────────────────────────
CANDIDATOS_SEED = [
    {
        'slug':       'lula',
        'nome':       'Luiz Inácio Lula da Silva',
        'nome_abrev': 'Lula',
        'partido':    'PT',
        'cor':        '#e63946',
        'aprovacao':  38.0,
        'rejeicao':   48.0,
        'neutro':     14.0,
        'mencoes':    1847,
        'tendencia':  'down',
        'temas_csv':  'economia,saude,politica',
        'categoria':  'presidente',
        'uf':         None,
    },
    {
        'slug':       'bolsonaro',
        'nome':       'Jair Messias Bolsonaro',
        'nome_abrev': 'Bolsonaro',
        'partido':    'PL',
        'cor':        '#ffd60a',
        'aprovacao':  35.0,
        'rejeicao':   52.0,
        'neutro':     13.0,
        'mencoes':    1623,
        'tendencia':  'stable',
        'temas_csv':  'politica,violencia,justica',
        'categoria':  'presidente',
        'uf':         None,
    },
    {
        'slug':       'tarcisio-de-freitas',
        'nome':       'Tarcísio de Freitas',
        'nome_abrev': 'Tarcísio',
        'partido':    'Republicanos',
        'cor':        '#2196f3',
        'aprovacao':  42.0,
        'rejeicao':   31.0,
        'neutro':     27.0,
        'mencoes':    986,
        'tendencia':  'up',
        'temas_csv':  'economia,politica,educacao',
        'categoria':  'governador',
        'uf':         'SP',
    },
    {
        'slug':       'ciro-gomes',
        'nome':       'Ciro Gomes',
        'nome_abrev': 'Ciro',
        'partido':    'PDT',
        'cor':        '#ff6b35',
        'aprovacao':  28.0,
        'rejeicao':   38.0,
        'neutro':     34.0,
        'mencoes':    412,
        'tendencia':  'stable',
        'temas_csv':  'economia,educacao',
        'categoria':  'presidente',
        'uf':         None,
    },
    {
        'slug':       'marina-silva',
        'nome':       'Marina Silva',
        'nome_abrev': 'Marina',
        'partido':    'REDE',
        'cor':        '#2d6a4f',
        'aprovacao':  31.0,
        'rejeicao':   29.0,
        'neutro':     40.0,
        'mencoes':    387,
        'tendencia':  'up',
        'temas_csv':  'saude,educacao,politica',
        'categoria':  'senador',
        'uf':         'AC',
    },
    {
        'slug':       'flavio-dino',
        'nome':       'Flávio Dino',
        'nome_abrev': 'F. Dino',
        'partido':    'PSB',
        'cor':        '#7b2d8b',
        'aprovacao':  24.0,
        'rejeicao':   41.0,
        'neutro':     35.0,
        'mencoes':    298,
        'tendencia':  'down',
        'temas_csv':  'justica,politica',
        'categoria':  'senador',
        'uf':         'MA',
    },
]

# ── Notícias seed ─────────────────────────────────────────────────────────
NOTICIAS_SEED = [
    ('lula',              'Governo anuncia novo pacote de medidas para controle da inflação',
     'O presidente Lula anunciou um conjunto de medidas econômicas visando reduzir a inflação nos próximos meses, incluindo subsídios para combustíveis e alimentos básicos.',
     'neutro', 'economia', 'G1 / Globo', 92, 2),
    ('bolsonaro',         'Bolsonaro faz discurso inflamado em convenção do PL em São Paulo',
     'O ex-presidente reuniu milhares de apoiadores na capital paulista durante encontro nacional do Partido Liberal, reafirmando candidatura para 2026.',
     'positivo', 'politica', 'UOL Notícias', 88, 4),
    ('tarcisio-de-freitas','Tarcísio apresenta plano de segurança pública para estados do Nordeste',
     'O governador de São Paulo apresentou proposta abrangente de segurança pública com investimento em tecnologia e policiamento integrado.',
     'positivo', 'violencia', 'Folha de S.Paulo', 85, 6),
    ('lula',              'Pesquisa aponta queda na aprovação do governo federal',
     'Novo levantamento do Datafolha indica que a aprovação do governo Lula caiu 4 pontos percentuais nas últimas semanas, impactada pela alta do dólar.',
     'negativo', 'politica', 'Estadão', 95, 8),
    ('ciro-gomes',        'Ciro Gomes critica política econômica do PT e propõe alternativa',
     'O pré-candidato do PDT fez duras críticas ao modelo econômico do governo Lula durante entrevista, apresentando proposta de desenvolvimento industrial.',
     'negativo', 'economia', 'CNN Brasil', 72, 10),
    ('marina-silva',      'Marina Silva defende urgência na aprovação de legislação ambiental',
     'A senadora intensificou pressão sobre parlamentares para aprovação do novo marco regulatório ambiental, tema central de sua pré-candidatura.',
     'positivo', 'politica', 'Agência Brasil', 68, 12),
    ('bolsonaro',         'STF volta a discutir elegibilidade de candidatos com condenações',
     'O Supremo Tribunal Federal retomou julgamento que pode afetar a elegibilidade de candidatos com condenações em segunda instância.',
     'negativo', 'justica', 'O Globo', 91, 14),
    ('lula',              'Índice de desemprego cai para menor nível em 10 anos',
     'Dados do IBGE mostram queda no desemprego, com taxa atingindo 6,2%. Governo comemora resultado como fruto de políticas econômicas.',
     'positivo', 'economia', 'Poder360', 87, 16),
    ('tarcisio-de-freitas','Tarcísio lidera intenções de voto em pesquisa para presidente em 2026',
     'Levantamento nacional coloca o governador de São Paulo na frente pela primeira vez em simulação de segundo turno contra Lula.',
     'positivo', 'politica', 'Veja', 97, 18),
    ('flavio-dino',       'Flávio Dino anuncia ampliação de programa de habitação popular',
     'O ministro das Cidades apresentou expansão do Minha Casa Minha Vida, com meta de construção de 500 mil novas unidades.',
     'positivo', 'politica', 'R7', 65, 20),
    ('bolsonaro',         'Disputa pelo eleitorado evangélico esquenta corrida presidencial',
     'Candidatos intensificam aproximação com lideranças evangélicas em todo o país, segmento que representa cerca de 30% do eleitorado.',
     'neutro', 'politica', 'Metrópoles', 78, 24),
    ('ciro-gomes',        'Debate sobre reforma tributária divide candidatos à presidência',
     'As diferentes visões sobre a implementação da reforma tributária aprovada no Congresso estão dividindo os pré-candidatos presidenciais.',
     'neutro', 'economia', 'Nexo Jornal', 74, 28),
    ('marina-silva',      'Marina Silva lança campanha nacional de educação ambiental',
     'A senadora apresentou programa educacional com inclusão de conteúdo ambiental obrigatório em todas as escolas públicas.',
     'positivo', 'educacao', 'Brasil de Fato', 62, 30),
    ('lula',              'Governo federal lança programa de crédito para pequenas empresas',
     'O BNDES lançou linha de crédito especial para pequenas e médias empresas, totalizando R$ 20 bilhões em recursos.',
     'positivo', 'economia', 'Band News', 81, 36),
    ('tarcisio-de-freitas','Tarcísio inaugura sistema de monitoramento por câmeras em SP',
     'São Paulo ampliou sua rede com a inauguração de mais 2.000 câmeras integradas ao Centro de Operações de Segurança estadual.',
     'positivo', 'violencia', 'SBT News', 76, 40),
    ('ciro-gomes',        'Críticos apontam contradições no plano econômico de Ciro',
     'Economistas questionam viabilidade de algumas propostas do pré-candidato do PDT, especialmente a criação de nova moeda digital.',
     'negativo', 'economia', 'The Intercept BR', 69, 44),
    ('marina-silva',      'Saúde pública volta ao centro do debate eleitoral após crise em hospitais',
     'Superlotação em hospitais de seis capitais brasileiras reacende debate sobre o SUS e projeta o tema como central na campanha de 2026.',
     'negativo', 'saude', 'Record News', 83, 48),
    ('bolsonaro',         'Bolsonaro reforça discurso de combate ao crime organizado',
     'Em evento com parlamentares do PL, o ex-presidente reafirmou compromisso com endurecimento das leis penais.',
     'positivo', 'violencia', 'Correio Braziliense', 77, 52),
    ('flavio-dino',       'Flávio Dino participa de conferência internacional sobre cidades sustentáveis',
     'O ministro representou o Brasil em evento em Berlim, assinando acordos de cooperação técnica para cidades brasileiras.',
     'positivo', 'politica', 'Reuters Brasil', 60, 56),
    ('tarcisio-de-freitas','Pesquisa espontânea mostra crescimento de Tarcísio no interior do Brasil',
     'Levantamento do Quaest indica avanço expressivo do governador paulista em cidades do interior das regiões Sul e Sudeste.',
     'positivo', 'politica', 'O Estado do MA', 89, 60),
]


def seed_database() -> None:
    """Popula o banco se ainda não houver candidatos cadastrados."""
    if Candidato.query.first():
        return  # Já populado — não re-seed

    print('🌱 Populando banco de dados com dados iniciais...')

    # ── Candidatos ────────────────────────────────────────────────────────
    candidatos_criados = {}
    for dados in CANDIDATOS_SEED:
        c = Candidato(**dados)
        db.session.add(c)
        db.session.flush()
        candidatos_criados[dados['slug']] = c
        HistoricoService.gerar_historico(c, dias=60)

    db.session.flush()

    # ── Notícias ──────────────────────────────────────────────────────────
    for (slug, titulo, resumo, sentimento, tema, fonte, relevancia, horas) in NOTICIAS_SEED:
        cand = candidatos_criados.get(slug)
        if not cand:
            continue
        n = Noticia(
            candidato_id = cand.id,
            titulo       = titulo,
            resumo       = resumo,
            sentimento   = sentimento,
            tema         = tema,
            fonte        = fonte,
            relevancia   = relevancia,
            publicada_em = datetime.utcnow() - timedelta(hours=horas),
        )
        db.session.add(n)

    db.session.commit()
    print(f'✅ Seed concluído: {len(CANDIDATOS_SEED)} candidatos, '
          f'{len(NOTICIAS_SEED)} notícias inseridas.')
