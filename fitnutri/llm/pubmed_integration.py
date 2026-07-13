"""
FitNutri - Integração com PubMed (API NCBI Gratuita)
Busca artigos científicos recentes para complementar recomendações dos agentes.

NOTA: Usar API E-utilities do NCBI (gratuita, sem autenticação necessária)
"""

import logging
import requests
import json
from typing import Optional, List, Dict
from datetime import datetime, timedelta
import time

logger = logging.getLogger(__name__)

PUBMED_BASE_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
PUBMED_FETCH_URL = "https://www.ncbi.nlm.nih.gov/pubmed"


class PubMedArticle:
    """Representa um artigo do PubMed."""
    def __init__(self, pmid: str, title: str, authors: List[str], pub_date: str, abstract: str):
        self.pmid = pmid
        self.title = title
        self.authors = authors
        self.pub_date = pub_date
        self.abstract = abstract

    def to_dict(self) -> Dict:
        return {
            "pmid": self.pmid,
            "title": self.title,
            "authors": self.authors,
            "pub_date": self.pub_date,
            "abstract": self.abstract,
            "url": f"https://pubmed.ncbi.nlm.nih.gov/{self.pmid}/"
        }

    def format_for_prompt(self) -> str:
        """Formata artigo para uso em prompts de agentes."""
        authors_str = ", ".join(self.authors[:3])
        if len(self.authors) > 3:
            authors_str += f" et al."
        
        return f"""
**{self.title}**
Autores: {authors_str}
Data: {self.pub_date}
PMID: {self.pmid}
URL: https://pubmed.ncbi.nlm.nih.gov/{self.pmid}/
Resumo: {self.abstract[:300]}...
"""


class PubMedClient:
    """Cliente para buscar artigos no PubMed usando API NCBI (gratuita)."""

    def __init__(self, cache_hours: int = 24):
        self.base_url = PUBMED_BASE_URL
        self.cache_hours = cache_hours
        self._cache: Dict[str, tuple] = {}  # (timestamp, results)
        self.rate_limit_delay = 0.1  # 100ms entre requisições (respeitar rate limit)

    def buscar_por_topico(
        self,
        query: str,
        min_date: Optional[str] = None,
        max_date: str = None,
        max_results: int = 3
    ) -> List[PubMedArticle]:
        """
        Busca artigos no PubMed por tópico.
        
        Args:
            query: Termo de busca (ex: "creatine supplementation athletes")
            min_date: Data mínima em formato YYYY/MM/DD (padrão: últimos 5 anos)
            max_date: Data máxima em formato YYYY/MM/DD (padrão: hoje)
            max_results: Máximo de artigos a retornar
        
        Returns:
            Lista de PubMedArticle com os resultados
        """
        
        # Verificar cache
        cache_key = f"{query}_{min_date}_{max_date}_{max_results}"
        if cache_key in self._cache:
            cached_time, cached_results = self._cache[cache_key]
            if (datetime.now() - cached_time).total_seconds() < (self.cache_hours * 3600):
                logger.info(f"✓ Retornando resultados do cache para: {query}")
                return cached_results

        # Definir datas padrão
        if not max_date:
            max_date = datetime.now().strftime("%Y/%m/%d")
        if not min_date:
            min_date = (datetime.now() - timedelta(days=5*365)).strftime("%Y/%m/%d")

        try:
            # Etapa 1: Buscar IDs (esearch)
            logger.info(f"🔍 Buscando no PubMed: {query}")
            
            search_params = {
                "db": "pubmed",
                "term": query,
                "mindate": min_date.replace("/", ""),  # YYYYMMDD format
                "maxdate": max_date.replace("/", ""),
                "retmax": max_results * 2,  # Buscar mais para filtrar
                "rettype": "json",
                "tool": "fitnutri",
                "email": "contact@fitnutri.com"  # Recomendado pelo NCBI
            }

            time.sleep(self.rate_limit_delay)
            response = requests.get(
                f"{self.base_url}/esearch.fcgi",
                params=search_params,
                timeout=10
            )
            response.raise_for_status()

            search_data = response.json()
            pmids = search_data.get("esearchresult", {}).get("idlist", [])

            if not pmids:
                logger.warning(f"Nenhum resultado encontrado para: {query}")
                return []

            # Etapa 2: Buscar detalhes dos artigos (efetch)
            logger.info(f"📚 Recuperando {len(pmids[:max_results])} artigos")
            
            fetch_params = {
                "db": "pubmed",
                "id": ",".join(pmids[:max_results]),
                "rettype": "json",
                "tool": "fitnutri",
                "email": "contact@fitnutri.com"
            }

            time.sleep(self.rate_limit_delay)
            response = requests.get(
                f"{self.base_url}/efetch.fcgi",
                params=fetch_params,
                timeout=10
            )
            response.raise_for_status()

            articles_data = response.json()
            articles = self._parsear_articles(articles_data)

            # Cachear resultados
            self._cache[cache_key] = (datetime.now(), articles)

            logger.info(f"✓ {len(articles)} artigos encontrados e cacheados")
            return articles

        except requests.RequestException as e:
            logger.error(f"Erro ao buscar PubMed: {e}")
            return []
        except Exception as e:
            logger.error(f"Erro ao parsear resposta do PubMed: {e}")
            return []

    def _parsear_articles(self, data: dict) -> List[PubMedArticle]:
        """Parseia resposta JSON do efetch em lista de PubMedArticle."""
        articles = []
        
        try:
            articles_list = data.get("result", {}).get("uids", [])
            
            for uid in articles_list:
                if uid == "uids":  # Skip header
                    continue
                
                article_data = data.get("result", {}).get(uid, {})
                if not article_data:
                    continue

                # Extrair campos
                pmid = uid
                title = article_data.get("title", "N/A")
                
                # Autores
                authors = []
                if "authors" in article_data:
                    authors = [a.get("name", "") for a in article_data["authors"] if a.get("name")]
                
                # Data de publicação
                pub_date = "N/A"
                if "pubdate" in article_data:
                    pub_date = article_data["pubdate"]
                elif "articleids" in article_data:
                    for aid in article_data["articleids"]:
                        if aid.get("idtype") == "pii":
                            continue
                    pub_date = "2024-2025"  # Fallback para artigos recentes
                
                # Abstract
                abstract = ""
                if "abstract" in article_data:
                    abstract = article_data["abstract"]
                
                articles.append(
                    PubMedArticle(
                        pmid=pmid,
                        title=title,
                        authors=authors[:5],  # Máximo 5 autores
                        pub_date=pub_date,
                        abstract=abstract
                    )
                )
        
        except Exception as e:
            logger.error(f"Erro ao parsear artigos: {e}")

        return articles

    def buscar_por_topico_nutricionista(self, tema: str) -> str:
        """
        Busca artigos relevantes para nutricionista e formata para prompt.
        
        Exemplos de temas:
        - "creatine supplementation muscle"
        - "vitamin d deficiency athletes"
        - "gut health microbiome nutrition"
        - "protein synthesis resistance training"
        """
        articles = self.buscar_por_topico(
            query=tema,
            max_results=3
        )

        if not articles:
            return f"(Nenhum artigo recente encontrado para '{tema}')"

        formatted = f"\n## Evidência Científica Recente - {tema}\n"
        for art in articles:
            formatted += art.format_for_prompt()

        return formatted


# Instância global (singleton)
_pubmed_client = None


def get_pubmed_client() -> PubMedClient:
    """Retorna instância única do cliente PubMed."""
    global _pubmed_client
    if _pubmed_client is None:
        _pubmed_client = PubMedClient(cache_hours=24)
    return _pubmed_client
