# 🗳️ Pesquisa Eleitoral 2026 — Python MVC

Plataforma de análise de tendências eleitorais construída com **Python + Flask** seguindo rigorosamente a **arquitetura MVC** (Model-View-Controller).

---

## 🏗️ Arquitetura MVC

```
python-mvc/
├── run.py                          ← Ponto de entrada
├── config.py                       ← Configurações (dev/test/prod)
├── requirements.txt
├── .env.example
│
└── app/
    ├── __init__.py                 ← Application Factory + registro de blueprints
    ├── database.py                 ← Instância do SQLAlchemy
    ├── seed.py                     ← Dados iniciais
    │
    ├── models/          ── M (Model)
    │   ├── __init__.py
    │   ├── candidato.py            ← Candidato (tabela, propriedades, to_dict)
    │   ├── noticia.py              ← Noticia (análise de sentimento)
    │   └── historico.py            ← Historico (série temporal diária)
    │
    ├── services/        ── Lógica de negócio (entre Controller e Model)
    │   ├── __init__.py
    │   ├── candidato_service.py    ← CRUD + simulação de métricas
    │   ├── noticia_service.py      ← Filtros, paginação, estatísticas
    │   ├── historico_service.py    ← Série temporal, tendência, gráficos
    │   └── dashboard_service.py    ← Agregação para o dashboard
    │
    ├── controllers/     ── C (Controller) = Blueprints Flask
    │   ├── __init__.py
    │   ├── main_controller.py      ← GET /
    │   ├── candidato_controller.py ← GET/POST /candidatos/
    │   ├── noticia_controller.py   ← GET /noticias/
    │   ├── tendencia_controller.py ← GET /tendencias/
    │   └── api_controller.py       ← /api/v1/* (REST JSON)
    │
    ├── views/           ── V (View) = Templates Jinja2
    │   └── templates/
    │       ├── base.html           ← Layout base (sidebar, topbar, flash)
    │       ├── dashboard.html      ← Dashboard com Chart.js
    │       ├── candidatos/
    │       │   ├── lista.html
    │       │   ├── detalhe.html
    │       │   └── form.html
    │       ├── noticias/
    │       │   └── lista.html
    │       └── tendencias/
    │           └── index.html
    │
    └── static/
        ├── css/style.css           ← Design system dark mode
        └── js/app.js               ← JS cliente (sidebar, toast, refresh)
```

---

## 🚀 Como Executar

### 1. Criar ambiente virtual

```bash
cd python-mvc
python -m venv .venv

# Linux/Mac
source .venv/bin/activate

# Windows
.venv\Scripts\activate
```

### 2. Instalar dependências

```bash
pip install -r requirements.txt
```

### 3. Configurar variáveis de ambiente

```bash
cp .env.example .env
# Edite o .env se necessário
```

### 4. Executar

```bash
python run.py
```

Acesse: **http://localhost:5000**

O banco SQLite é criado automaticamente na pasta `instance/` e populado com dados iniciais na primeira execução.

---

## 🌐 Rotas da Aplicação

### Páginas (HTML)

| Método | Rota | Descrição |
|--------|------|-----------|
| GET | `/` | Dashboard principal |
| GET | `/candidatos/` | Lista de candidatos |
| GET | `/candidatos/<slug>` | Detalhe de um candidato |
| GET | `/candidatos/novo` | Formulário para adicionar |
| POST | `/candidatos/novo` | Criar novo candidato |
| POST | `/candidatos/<id>/desativar` | Remover do monitoramento |
| GET | `/noticias/` | Feed com filtros e paginação |
| GET | `/tendencias/` | Análise comparativa e histórico |

### API REST — `/api/v1/`

| Método | Rota | Descrição |
|--------|------|-----------|
| GET | `/api/v1/candidatos` | Lista candidatos (JSON) |
| GET | `/api/v1/candidatos/<slug>` | Detalhe de candidato |
| POST | `/api/v1/candidatos` | Criar candidato via JSON |
| DELETE | `/api/v1/candidatos/<id>` | Desativar candidato |
| GET | `/api/v1/noticias` | Notícias com filtros |
| GET | `/api/v1/noticias/sentimento` | Estatísticas de sentimento |
| GET | `/api/v1/noticias/temas` | Contagem por tema |
| GET | `/api/v1/historico?dias=30` | Histórico de todos |
| GET | `/api/v1/historico/<id>` | Histórico de um candidato |
| GET | `/api/v1/dashboard?periodo=30` | Dados completos do dashboard |
| GET | `/api/v1/inteligencia/sinais?dias=30` | Sinais acionáveis por candidato |
| GET | `/api/v1/alertas?dias=30&limite=8` | Alertas automáticos priorizados |
| POST | `/api/v1/atualizar` | Simula ciclo de coleta |

### Query params disponíveis

**`/noticias/` e `/api/v1/noticias`:**
- `sentimento=positivo|negativo|neutro`
- `tema=economia|saude|educacao|violencia|justica|politica`
- `candidato_id=<int>`
- `q=<texto>`
- `pagina=<int>` (padrão: 1)
- `por_pagina=<int>` (padrão: 20)

---

## 🗄️ Modelos de Dados

### Candidato
| Campo | Tipo | Descrição |
|---|---|---|
| id | Integer | PK |
| slug | String | Identificador único URL-friendly |
| nome | String | Nome completo |
| nome_abrev | String | Nome curto (ex: "Tarcísio") |
| partido | String | Sigla do partido |
| cor | String | Cor hex de identificação |
| aprovacao | Float | % aprovação atual |
| rejeicao | Float | % rejeição atual |
| neutro | Float | % neutros atual |
| mencoes | Integer | Total de menções |
| tendencia | String | `up`, `down` ou `stable` |
| temas_csv | String | Temas separados por vírgula |
| ativo | Boolean | Flag de monitoramento ativo |

### Noticia
| Campo | Tipo | Descrição |
|---|---|---|
| candidato_id | FK | Candidato mencionado |
| titulo | String | Título da notícia |
| resumo | Text | Corpo/resumo |
| fonte | String | Veículo de mídia |
| sentimento | String | `positivo`, `negativo`, `neutro` |
| tema | String | Categoria temática |
| relevancia | Integer | Score 0–100 |
| publicada_em | DateTime | Data de publicação |

### Historico
| Campo | Tipo | Descrição |
|---|---|---|
| candidato_id | FK | Dono da série |
| data | Date | Data do snapshot (único por candidato/dia) |
| aprovacao | Float | % aprovação no dia |
| rejeicao | Float | % rejeição no dia |
| neutro | Float | % neutros no dia |
| mencoes | Integer | Menções no dia |

---

## 🔧 Tecnologias

| Camada | Tecnologia |
|---|---|
| Web Framework | Flask 3.0 |
| ORM | SQLAlchemy + Flask-SQLAlchemy |
| Banco (dev) | SQLite 3 |
| Banco (prod) | PostgreSQL (via `DATABASE_URL`) |
| Templates | Jinja2 (integrado ao Flask) |
| Slugs | python-slugify |
| Env vars | python-dotenv |
| Frontend | HTML5 + CSS3 + JavaScript ES6 |
| Gráficos | Chart.js 4 (CDN) |
| Ícones | Font Awesome 6 (CDN) |
| Fontes | Google Fonts / Inter |

---

## 🔮 Próximas Evoluções

1. **Coleta real de notícias** — integrar RSS feeds ou API de busca
2. **IA de sentimento real** — modelo BERT/RoBERTa para português (HuggingFace)
3. **Autenticação** — Flask-Login para painel administrativo
4. **Agendamento** — APScheduler para coleta automática a cada 2h
5. **Migrações** — Flask-Migrate para evolução do schema
6. **Testes** — pytest + Flask test client
7. **Deploy** — gunicorn + Nginx + Docker + PostgreSQL
8. **Cache** — Flask-Caching para queries pesadas do dashboard
9. **Export** — endpoint `/api/v1/export/csv` para download
10. **WebSocket** — atualização ao vivo sem recarregar a página

---

## 🧠 Camada de Inteligência (atual)

O produto agora inclui sinais acionáveis para consultoria eleitoral:

- **Ruptura negativa**: crescimento abrupto de negatividade no período.
- **Aceleração positiva**: ganho rápido de sentimento positivo.
- **Pico de visibilidade**: aumento súbito de volume de cobertura.
- **Score de prioridade**: combinação de volume, risco e momentum.

### Indicadores de decisão

- `delta_positivo_pp`: variação do percentual positivo vs janela anterior.
- `delta_negativo_pp`: variação do percentual negativo vs janela anterior.
- `delta_volume`: variação de volume de notícias entre janelas.
- `confianca`: proxy de robustez analítica (baseado em volume).

### Alertas automáticos

Alertas são derivados dos sinais e exibidos no dashboard e módulos:

- `critico`: severidade alta (rupturas relevantes).
- `atencao`: mudanças importantes para monitoramento tático.

---

## 🧩 Módulos Profissionais

Rotas dedicadas por perfil:

- `/modulos/consultoria` — leitura executiva com recomendações.
- `/modulos/campanha` — foco em risco reputacional diário.
- `/modulos/partido` — visão multi-candidatos por tema/UF.

As visões usam os mesmos dados-base, com contexto de decisão específico por público.

---

## 📐 Princípios MVC aplicados

| Componente | Responsabilidade |
|---|---|
| **Model** (`models/`) | Definição do schema, relacionamentos, serialização, propriedades calculadas |
| **Service** (`services/`) | Lógica de negócio pura, reutilizável por Controllers e API |
| **Controller** (`controllers/`) | Recebe requisição HTTP → chama Service → passa dados para View |
| **View** (`views/templates/`) | Renderização HTML via Jinja2, sem lógica de negócio |
| **Static** (`static/`) | CSS e JS do lado cliente |

---

*Pesquisa Eleitoral 2026 — Desenvolvido com Python + Flask seguindo arquitetura MVC.*
