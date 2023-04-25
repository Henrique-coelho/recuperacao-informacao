from crawler import page_fetcher, scheduler
from urllib.parse import urlparse
from datetime import datetime

def fetch_pages(page_limit: int, depth_limit: int, thread_counter: int):
    seeds = ["https://g1.globo.com/", "https://www.cnnbrasil.com.br/", "https://www.estadao.com.br/"]
    seeds = [urlparse(url) for url in seeds]

    s = scheduler.Scheduler("Henrique C. e Rodrigo L.", page_limit, depth_limit, seeds)

    startTime = datetime.now()

    open('url_coletadas.txt', 'w').close()
    print('Executando...')

    threads = []

    for num in range(thread_counter):
        thread = page_fetcher.PageFetcher(s)
        thread.start()
        thread.run()
        threads.append(thread)

    for thread in threads:
        thread.join()

    total_time = (datetime.now() - startTime).total_seconds()
    return total_time