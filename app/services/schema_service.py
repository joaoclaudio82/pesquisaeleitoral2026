"""
Service: SchemaService
Documentação das tabelas, colunas e relacionamentos do banco.
"""
from sqlalchemy import inspect as sa_inspect

from ..database import db
from ..models import Candidato, Historico, Noticia, Usuario

_MODELOS = [
    (Candidato, 'Candidatos monitorados pelo sistema (cargo, UF, métricas).'),
    (Noticia, 'Notícias coletadas vinculadas a um candidato.'),
    (Historico, 'Série diária de métricas por candidato.'),
    (Usuario, 'Contas de acesso (admin ou visualizador).'),
]


class SchemaService:
    """Monta visão do schema ORM + estatísticas do banco."""

    @staticmethod
    def obter_documentacao() -> dict:
        tabelas = []
        relacionamentos = []
        mermaid_lines = ['erDiagram']

        for model, descricao in _MODELOS:
            info = SchemaService._documentar_modelo(model, descricao)
            tabelas.append(info)
            for rel in info['relacionamentos_saida']:
                relacionamentos.append(rel)

        for t in tabelas:
            mermaid_lines.append(SchemaService._mermaid_entidade(t))

        pares_vistos: set[tuple[str, str]] = set()
        for rel in relacionamentos:
            if rel['cardinalidade'] != '1:N':
                continue
            par = (rel['origem'], rel['destino'])
            if par in pares_vistos:
                continue
            pares_vistos.add(par)
            mermaid_lines.append(SchemaService._mermaid_relacao(rel))

        return {
            'tabelas': tabelas,
            'relacionamentos': relacionamentos,
            'mermaid': '\n'.join(mermaid_lines),
            'total_tabelas': len(tabelas),
            'total_relacionamentos': len(relacionamentos),
        }

    @staticmethod
    def _documentar_modelo(model, descricao: str) -> dict:
        mapper = sa_inspect(model)
        tabela = model.__tablename__

        colunas = []
        for col in mapper.columns:
            fks = []
            for fk in col.foreign_keys:
                fks.append({
                    'coluna_local': col.name,
                    'tabela_ref': fk.column.table.name,
                    'coluna_ref': fk.column.name,
                })
            colunas.append({
                'nome': col.name,
                'tipo': SchemaService._tipo_amigavel(col.type),
                'nullable': col.nullable,
                'pk': col.primary_key,
                'unique': col.unique or False,
                'index': col.index or False,
                'default': SchemaService._formatar_default(col.default),
                'fks': fks,
            })

        constraints = []
        for c in model.__table__.constraints:
            nome = getattr(c, 'name', None) or c.__class__.__name__
            if hasattr(c, 'columns'):
                cols = [x.name for x in c.columns]
            else:
                cols = []
            constraints.append({
                'nome': nome,
                'tipo': c.__class__.__name__,
                'colunas': cols,
            })

        relacionamentos_saida = []
        for rel in mapper.relationships:
            target = rel.mapper.class_.__tablename__
            target_model = rel.mapper.class_
            cardinalidade = SchemaService._cardinalidade(rel)
            fk_cols = SchemaService._colunas_fk_para(tabela, target_model)

            rel_info = {
                'origem': tabela,
                'destino': target,
                'nome_relacao': rel.key,
                'cardinalidade': cardinalidade,
                'direcao': 'saida',
                'fk_colunas': fk_cols,
                'cascade': SchemaService._cascade_label(rel),
                'descricao': SchemaService._descricao_relacao(
                    tabela, target, cardinalidade, rel.key
                ),
            }
            relacionamentos_saida.append(rel_info)

        try:
            total = db.session.query(model).count()
        except Exception:
            total = None

        return {
            'nome': tabela,
            'modelo': model.__name__,
            'descricao': descricao,
            'total_registros': total,
            'colunas': colunas,
            'relacionamentos_saida': relacionamentos_saida,
            'constraints': constraints,
        }

    @staticmethod
    def _tipo_amigavel(col_type) -> str:
        t = str(col_type)
        mapa = {
            'INTEGER': 'INTEGER',
            'VARCHAR': 'STRING',
            'TEXT': 'TEXT',
            'FLOAT': 'FLOAT',
            'BOOLEAN': 'BOOLEAN',
            'DATETIME': 'DATETIME',
            'DATE': 'DATE',
        }
        for k, v in mapa.items():
            if k in t.upper():
                sufixo = t[t.find('('):] if '(' in t else ''
                return v + sufixo
        return t

    @staticmethod
    def _formatar_default(default) -> str | None:
        if default is None:
            return None
        arg = getattr(default, 'arg', None)
        if arg is None:
            return None
        if callable(arg):
            return f'<{arg.__name__}()>'
        return str(arg)

    @staticmethod
    def _cardinalidade(rel) -> str:
        if rel.uselist:
            return '1:N'
        return 'N:1'

    @staticmethod
    def _colunas_fk_para(tabela_origem: str, model_destino) -> list[str]:
        """Colunas FK na tabela filha que apontam para tabela_origem."""
        cols = []
        child_mapper = sa_inspect(model_destino)
        for col in child_mapper.columns:
            for fk in col.foreign_keys:
                if fk.column.table.name == tabela_origem:
                    cols.append(col.name)
        return cols

    @staticmethod
    def _cascade_label(rel) -> str:
        cascade = rel.cascade
        if not cascade:
            return '—'
        parts = []
        if cascade.delete:
            parts.append('delete')
        if cascade.save_update:
            parts.append('save-update')
        if cascade.merge:
            parts.append('merge')
        if cascade.delete_orphan:
            parts.append('delete-orphan')
        return ', '.join(parts) if parts else '—'

    @staticmethod
    def _descricao_relacao(origem, destino, card, nome) -> str:
        if card == '1:N':
            return (
                f'Um registro em `{origem}` possui vários em `{destino}` '
                f'(atributo `{nome}`).'
            )
        return (
            f'Cada registro em `{origem}` referencia um em `{destino}` '
            f'(atributo `{nome}`).'
        )

    @staticmethod
    def _mermaid_tipo(tipo_sql: str) -> str:
        """Tipo válido para erDiagram do Mermaid (type nome)."""
        t = (tipo_sql or '').upper()
        if 'BOOL' in t:
            return 'boolean'
        if 'DATETIME' in t or 'TIMESTAMP' in t:
            return 'datetime'
        if 'DATE' in t and 'DATETIME' not in t:
            return 'date'
        if 'INT' in t:
            return 'int'
        if any(x in t for x in ('FLOAT', 'DOUBLE', 'NUMERIC', 'REAL')):
            return 'float'
        if 'TEXT' in t or 'CHAR' in t or 'STRING' in t:
            return 'string'
        return 'string'

    @staticmethod
    def _mermaid_attr(nome: str) -> str:
        """Nome de atributo seguro (sem palavras reservadas do Mermaid)."""
        reservados = {'data', 'order', 'end', 'link', 'style', 'class'}
        n = nome.strip().replace(' ', '_')
        if n.lower() in reservados:
            return f'{n}_col'
        return n

    @staticmethod
    def _mermaid_entidade(tabela_info: dict) -> str:
        nome = tabela_info['nome']
        linhas = [f'    {nome} {{']
        for col in tabela_info['colunas']:
            tipo = SchemaService._mermaid_tipo(col['tipo'])
            attr = SchemaService._mermaid_attr(col['nome'])
            linhas.append(f'        {tipo} {attr}')
        linhas.append('    }')
        return '\n'.join(linhas)

    @staticmethod
    def _mermaid_relacao(rel: dict) -> str:
        origem = rel['origem']
        destino = rel['destino']
        label = SchemaService._mermaid_attr(rel['nome_relacao'])
        return f'    {origem} ||--o{{ {destino} : {label}'
