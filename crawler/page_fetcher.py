from typing import Optional

from bs4 import BeautifulSoup
from threading import Thread
import requests
from urllib.parse import urlparse, urljoin, ParseResult, urlunparse


class PageFetcher(Thread):
    def __init__(self, obj_scheduler):
        super().__init__()
        self.obj_scheduler = obj_scheduler

    def request_url(self, obj_url: ParseResult) -> Optional[bytes] or None:
        """
        :param obj_url: Instância da classe ParseResult com a URL a ser requisitada.
        :return: Conteúdo em binário da URL passada como parâmetro, ou None se o conteúdo não for HTML
        """

        response = requests.get(urlunparse(obj_url), headers=({'user-agent': self.obj_scheduler.usr_agent}))
        
        if ('text/html' in response.headers['Content-type']):
            return response.content
        return None

    def discover_links(self, obj_url: ParseResult, depth: int, bin_str_content: bytes):
        """
        Retorna os links do conteúdo bin_str_content da página já requisitada obj_url
        """
        soup = BeautifulSoup(bin_str_content, features="lxml")
        for link in soup.select('a[href]'):
            if link.get('href') == None:
                pass
            else:
                new_url = link.attrs['href']
                obj_new_url = urlparse(new_url)

            if obj_new_url.netloc == '':
                    new_url = obj_url.scheme + '://' + obj_url.netloc + '/' + obj_new_url.path
                    obj_new_url = urlparse(new_url)

            new_depth = 0
            if obj_new_url.netloc == obj_url.netloc:
                new_depth = depth+1

            yield obj_new_url, new_depth

    def crawl_new_url(self):
        """
        Coleta uma nova URL, obtendo-a do escalonador
        """
        new_url, depth = self.obj_scheduler.get_next_url()
        
        if self.obj_scheduler.can_fetch_page(new_url):
            return None
        else:
            content = self.request_url(new_url)
        
            if content != None:
                return self.discover_links(new_url, depth, content)
            else:
                return None

    def run(self):
        """
        Executa coleta enquanto houver páginas a serem coletadas
        """
        while not self.obj_scheduler.has_finished_crawl():
            links = self.crawl_new_url()
            if links != None:
                for url,depth in links: 
                    if self.obj_scheduler.can_add_page(url, depth): self.obj_scheduler.add_new_page(url, depth)
                self.obj_scheduler.count_fetched_page()
