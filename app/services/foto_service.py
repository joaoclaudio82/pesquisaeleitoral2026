"""
Service: FotoService
Busca foto de candidatos na Wikipedia (pt) e salva em static/uploads.
"""
import logging
from pathlib import Path
from urllib.parse import urlparse

import requests

logger = logging.getLogger(__name__)

_WIKI_API = 'https://pt.wikipedia.org/w/api.php'
_USER_AGENT = 'PesquisaEleitoral2026/1.0 (educational; contact: local)'
_TIMEOUT = 12


class FotoService:
    """Obtém e persiste fotos de candidatos a partir da web."""

    @staticmethod
    def _termos_busca(nome: str, partido: str | None = None,
                      categoria: str | None = None) -> list[str]:
        """Gera termos de busca do mais específico ao mais genérico."""
        nome = nome.strip()
        termos = [nome]
        if partido:
            termos.append(f'{nome} {partido}')
        if categoria == 'presidente':
            termos.append(f'{nome} presidente Brasil')
        elif categoria:
            label = categoria.replace('_', ' ')
            termos.append(f'{nome} {label} Brasil')
        return list(dict.fromkeys(t for t in termos if t))

    @staticmethod
    def buscar_url_wikipedia(termo: str) -> str | None:
        """Retorna URL da miniatura na Wikipedia pt, ou None."""
        try:
            r = requests.get(
                _WIKI_API,
                params={
                    'action': 'query',
                    'generator': 'search',
                    'gsrsearch': termo,
                    'gsrlimit': 5,
                    'prop': 'pageimages',
                    'piprop': 'thumbnail',
                    'pithumbsize': 500,
                    'format': 'json',
                },
                headers={'User-Agent': _USER_AGENT},
                timeout=_TIMEOUT,
            )
            r.raise_for_status()
            pages = r.json().get('query', {}).get('pages', {})
            for page in pages.values():
                thumb = page.get('thumbnail', {})
                src = thumb.get('source')
                if src:
                    return src
        except requests.RequestException as exc:
            logger.warning('Wikipedia foto (%s): %s', termo, exc)
        return None

    @staticmethod
    def buscar_foto(
        nome: str,
        partido: str | None = None,
        categoria: str | None = None,
    ) -> str | None:
        """Tenta vários termos até encontrar uma imagem."""
        for termo in FotoService._termos_busca(nome, partido, categoria):
            url = FotoService.buscar_url_wikipedia(termo)
            if url:
                return url
        return None

    @staticmethod
    def _extensao_de_url(url: str) -> str:
        path = urlparse(url).path.lower()
        for ext in ('.jpg', '.jpeg', '.png', '.webp'):
            if ext in path:
                return ext.replace('.', '')
        return 'jpg'

    @staticmethod
    def salvar_foto_local(
        static_root: str | Path,
        slug: str,
        url_imagem: str,
    ) -> str | None:
        """
        Baixa a imagem e salva em static/uploads/candidatos/{slug}.ext
        Retorna caminho relativo ao static (ex: uploads/candidatos/lula.jpg).
        """
        try:
            resp = requests.get(
                url_imagem,
                headers={'User-Agent': _USER_AGENT},
                timeout=_TIMEOUT,
                stream=True,
            )
            resp.raise_for_status()
            content_type = (resp.headers.get('Content-Type') or '').lower()
            if 'image' not in content_type and not url_imagem.lower().endswith(
                ('.jpg', '.jpeg', '.png', '.webp')
            ):
                logger.warning('URL não é imagem: %s', url_imagem)
                return None

            ext = FotoService._extensao_de_url(url_imagem)
            if 'png' in content_type:
                ext = 'png'
            elif 'webp' in content_type:
                ext = 'webp'

            dest_dir = Path(static_root) / 'uploads' / 'candidatos'
            dest_dir.mkdir(parents=True, exist_ok=True)
            dest = dest_dir / f'{slug}.{ext}'

            # Remove versões anteriores com outra extensão
            for antiga in dest_dir.glob(f'{slug}.*'):
                if antiga != dest:
                    antiga.unlink(missing_ok=True)

            with open(dest, 'wb') as f:
                for chunk in resp.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)

            rel = f'uploads/candidatos/{slug}.{ext}'
            return rel
        except (OSError, requests.RequestException) as exc:
            logger.warning('Salvar foto %s: %s', slug, exc)
            return None

    @staticmethod
    def buscar_e_salvar(
        static_root: str | Path,
        slug: str,
        nome: str,
        partido: str | None = None,
        categoria: str | None = None,
    ) -> str | None:
        """Busca na Wikipedia e persiste localmente. Retorna caminho relativo ou None."""
        url = FotoService.buscar_foto(nome, partido, categoria)
        if not url:
            return None
        return FotoService.salvar_foto_local(static_root, slug, url)

    @staticmethod
    def remover_foto_local(static_root: str | Path, slug: str) -> None:
        pasta = Path(static_root) / 'uploads' / 'candidatos'
        if not pasta.exists():
            return
        for arq in pasta.glob(f'{slug}.*'):
            arq.unlink(missing_ok=True)
