"""
pip install feedparser trafilatura newspaper3k langchain-community
"""
import feedparser
import requests
import time
import json
import datetime
import logging
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor
from trafilatura import fetch_url, extract
from typing import List, Dict, Any
from newspaper import Article
from langchain_community.document_loaders.recursive_url_loader import RecursiveUrlLoader
import requests
import re as regex
from bs4 import BeautifulSoup

logging.basicConfig(level=logging.INFO)


def download_html_trafilatura(url: str):
    try:
        return fetch_url(url)
    except Exception as e:
        return None


def download_html_recursive_url_loader(url: str):
    try:
        loader = RecursiveUrlLoader(url=url, max_depth=2)
        docs = loader.load()
        doc = docs[0]
        return doc.page_content
    except Exception as e:
        return None


def extract_text_trafilatura(html: str):
    try:
        text = extract(html)
        return {'text': text, 'url': None, 'title': None}
    except Exception as e:
        return None


def extract_text_newspaper(doc):
    try:
        html = doc['html']
        url = doc['url']
        article = Article('', language='en', keep_article_html=True)
        article.download(input_html=html)
        article.parse()
        text = article.text
        title = article.title


        if len(text) < 100:
            return None
        return {'title': title, 'text': text, 'url': url}
    except Exception as e:
        return None


def multithread_download_html(urls: list, download_html_callable):
    with ThreadPoolExecutor(max_workers=10) as executor:
        htmls = list(executor.map(download_html_callable, urls))
    return [{'html': html, 'url': url} for html, url in zip(htmls, urls) if html is not None]


def multi_thread_extract_text(htmls: list, extract_text_callable):
    with ThreadPoolExecutor(max_workers=10) as executor:
        texts = list(executor.map(extract_text_callable, htmls))
    return [text for text in texts if text is not None]


def get_links_from_rss_feed(rss_feed: str, articles_per_feed: int, max_crawled_articles: int = 2500, timedelta_days=1):
    feed = feedparser.parse(rss_feed)
    urls = []
    cnt = 0
    currend_date = datetime.datetime.now()
    for entry in feed.entries:
        published = entry.published_parsed
        if currend_date - datetime.datetime(*published[:6]) > datetime.timedelta(days=timedelta_days):
            break
        if cnt >= articles_per_feed:
            break
        if len(urls) >= max_crawled_articles:
            break
        urls.append(entry.link)
        cnt += 1
    return urls


def get_articles_metadata_from_rss(rss_name, rss_url, timedelta_days=1):
    feed = feedparser.parse(rss_url)
    currend_date = datetime.datetime.now()
    entries = {}
    for entry in feed.entries:
        published = entry.published_parsed
        if currend_date - datetime.datetime(*published[:6]) > datetime.timedelta(days=timedelta_days):
            break
        entries[entry.link] = {
            'rss_name': rss_name,
            'title': entry.title,
            'summary': entry.summary,
            'url': entry.link,
            'published': datetime.datetime(*published[:6]).isoformat()
        }
    return entries


def get_links_from_all_gnews_feeds(keywords: list, articles_per_feed: int, max_crawled_articles: int = 2500, timedelta_days: int = 1):
    """return a list of urls to download"""
    urls = []
    for keyword_search_term in keywords:
        keyword_search_term = keyword_search_term.replace(" ", "%20")
        rss_feed = f'https://news.google.com/rss/search?q={keyword_search_term}%20when:1d&hl=en-US&gl=US&ceid=US:en'
        urls.extend(get_links_from_rss_feed(rss_feed, articles_per_feed, max_crawled_articles, timedelta_days))
        if len(urls) >= max_crawled_articles:
            break
    return urls


def get_redirected_urls(urls: list):
    """return a list of redirected urls"""
    def redirect_url(url):
        try:
            return requests.head(url, allow_redirects=True, timeout=2).url
        except Exception as e:
            print(f"**** Failed to get redirect url: {e} -> {url}")
            return None

    with ThreadPoolExecutor(max_workers=10) as executor:
        redirect_urls = list(executor.map(redirect_url, urls))
    return [url for url in redirect_urls if url is not None]


def extract_articles_trafilatura(urls: list):
    htmls = multithread_download_html(urls, download_html_trafilatura)
    print(f"Downloaded {len(htmls)} htmls with trafilatura")

    articles = multi_thread_extract_text(htmls, extract_text_trafilatura)
    print(f"Extracted {len(articles)} articles with trafilatura")
    return articles


def extract_articles(urls: list):
    htmls = multithread_download_html(urls, download_html_recursive_url_loader)
    print(f"Downloaded {len(htmls)} htmls")

    articles = multi_thread_extract_text(htmls, extract_text_newspaper)
    print(f"Extracted {len(articles)} articles")

    return articles


def crawl_gnews_articles(keywords: list, articles_per_feed: int = 50, max_crawled_articles: int = 2500, timedelta_days: int = 1):
    urls = get_google_news_article(keywords[0], articles_per_feed*3)

    print(f"Total Article URLs: {len(urls)}")
    # need to redirect to get the actual article url
    redirect_urls = get_redirected_urls(urls)
    redirect_urls = list(set(redirect_urls))
    print(f"Unique Redirected URLs: {len(redirect_urls)}")
    articles = extract_articles(redirect_urls)
    success_rate = len(articles) / len(redirect_urls)
    print(f"Crawler success rate: {success_rate:.2f}")
    return articles


def crawl_businesswire_articles(timedelta_days: int = 1):
    page_with_all_rss_feeds = 'https://www.businesswire.com/portal/site/home/news/industries/?_gl=1*1v5vxx*_ga*MTU1NDkzMTE1Mi4xNzA1Njg0MzU4*_ga_ZQWF70T3FK*MTcxMzM3NDc1MS4yNi4xLjE3MTMzNzYzOTEuMjMuMC4w'
    html = requests.get(page_with_all_rss_feeds).text
    soup = BeautifulSoup(html, 'html.parser')

    rss_link_map = {}
    for link in soup.find_all('a'):
        if 'feed.businesswire.com/rss' in link.get('href'):
            full_link = link.get('href')
            if full_link.startswith('//'):
                full_link = 'https:' + full_link
            # get name of the rss feed from the parent
            rss_feed_name = link.parent.get('title')
            rss_link_map[rss_feed_name] = full_link
    all_articles_metadata = {}
    for rss_name, rss_url in rss_link_map.items():
        articles_metadata = get_articles_metadata_from_rss(rss_name, rss_url, timedelta_days)
        all_articles_metadata.update(articles_metadata)
    urls = list(all_articles_metadata.keys())
    articles = extract_articles(urls)
    return articles, all_articles_metadata


def get_top_events():
    top_results_page = "https://news.google.com/topstories?hl=en-US&gl=US&ceid=US%3Aen"
    business_page = "https://news.google.com/topics/CAAqJggKIiBDQkFTRWdvSUwyMHZNRGx6TVdZU0FtVnVHZ0pWVXlnQVAB?hl=en-US&gl=US&ceid=US%3Aen"
    science_page = "https://news.google.com/topics/CAAqJggKIiBDQkFTRWdvSUwyMHZNRFp0Y1RjU0FtVnVHZ0pWVXlnQVAB?hl=en-US&gl=US&ceid=US%3Aen"
    # world_page = "https://news.google.com/topics/CAAqJggKIiBDQkFTRWdvSUwyMHZNRGx1YlY4U0FtVnVHZ0pWVXlnQVAB?hl=en-US&gl=US&ceid=US%3Aen"
    health_page  = "https://news.google.com/topics/CAAqIQgKIhtDQkFTRGdvSUwyMHZNR3QwTlRFU0FtVnVLQUFQAQ?hl=en-US&gl=US&ceid=US%3Aen"
    tech_page = "https://news.google.com/topics/CAAqJggKIiBDQkFTRWdvSUwyMHZNRGRqTVhZU0FtVnVHZ0pWVXlnQVAB?hl=en-US&gl=US&ceid=US%3Aen"
    pages = [top_results_page, business_page, science_page, tech_page, health_page]
    names = ["top_results", "business", "science", "tech", "health"]
    event_dataset = []
    for page, name in zip(pages, names):
        results = requests.get(page)
        soup = BeautifulSoup(results.text, "html.parser")
        # Filter to ones with href and "/stories/" in href
        links = [link for link in soup.find_all("a") if link.has_attr("href") and "/stories/" in link["href"]]
        print("Found %d %s stories" % (len(links), name))
        for link in links:
            gnews_eid = link["href"].split("/")[-1].split("?")[0]
            event_dataset.append({"gnews_eid": gnews_eid, "category": name})
    return event_dataset


def get_article_from_event(event):
    gnews_eid = event["gnews_eid"]
    url = "https://news.google.com/stories/"+gnews_eid+"?hl=en-US&gl=US&ceid=US%3Aen"
    results = requests.get(url)
    soup = BeautifulSoup(results.text, "html.parser")
    # Find all links with "/articles/" in href
    article_links = [link for link in soup.find_all("a") if link.has_attr("href") and "/articles/" in link["href"]]
    # id_to_title
    gnews_aids = set([])
    for a in article_links:
        gnews_aid = a["href"].split("/")[-1].split("?")[0]
        gnews_aids.add(gnews_aid)
    gnews_aids = list(gnews_aids)
    for gnews_aid in gnews_aids:
        gnews_url = "https://news.google.com/articles/"+gnews_aid
        try:
            redirect_url = requests.head(gnews_url, allow_redirects=True, timeout=2).url
            html = download_html_recursive_url_loader(redirect_url)
            article = extract_text_newspaper({'html': html, 'url': redirect_url})
            article['url'] = redirect_url
            # only need one parsed article per google story
            if article and article['text']:
                return article
        except Exception as e:
            pass
    return None


def get_all_articles_from_substack(substack_sitemap: str):
    results = requests.get(substack_sitemap)
    soup = BeautifulSoup(results.text, "html.parser")
    # Find all links with "/p/" in href
    article_links = [link for link in soup.find_all("loc") if "/p/" in link.text]
    urls = [link.text for link in article_links]
    articles = extract_articles(urls)
    return articles


def crawl_top_gnews_articles():
    event_dataset = get_top_events()
    with ThreadPoolExecutor(max_workers=10) as executor:
        articles = list(executor.map(get_article_from_event, event_dataset))
    return [a for a in articles if a is not None]


class DailyNewsCrawler:
    def crawl(self):
        top_articles = crawl_top_gnews_articles()
        top_bw_articles, _ = crawl_businesswire_articles(timedelta_days=1)
        articles = top_articles + top_bw_articles
        return articles

    def crawl_and_save(self, data_dir = "./news/"):
        articles = self.crawl()
        current_data_str = datetime.datetime.now().strftime("%Y-%m-%d")
        with open(f"{data_dir}{current_data_str}.json", "w") as f:
            json.dump(articles, f, indent=2)


def test_gnews_crawl():
    start = time.time()
    keywords = ["Disney"]
    articles_per_feed = 5
    articles = crawl_gnews_articles(keywords, articles_per_feed=articles_per_feed)
    for article in articles:
        print(article['title'])
        print(article['url'])
        print('****')
    print(f"Total Articles: {len(articles)}")
    # print(f"Total Visited URLs: {len(visited_urls)}")
    print(f"Time taken: {time.time() - start:.2f} seconds")

def get_google_news_article(search_string, test_size):
    articles = []
    count = 0
    for size in range(0, test_size//10+10):
        url = f'https://www.google.com/search?q={search_string}&safe=active&tbs=qdr:w,sdb:1&tbm=nws&source=lnt&dpr=1&start={size}'
        response = requests.get(url)
        raw_html = BeautifulSoup(response.text, "lxml")
        main_tag = raw_html.find('div', {'id': 'main'})
        for div_tag in main_tag.find_all('div', {'class': regex.compile('xpd')}):
            for a_tag in div_tag.find_all('a', href=True):
                if not a_tag.get('href').startswith('/search?'):
                    none_articles = bool(
                        regex.search('amazon.com|facebook.com|twitter.com|youtube.com|wikipedia.org', a_tag['href']))
                    if none_articles is False:
                        if a_tag.get('href').startswith('/url?q='):
                            find_article = regex.search('(.*)(&sa=)', a_tag.get('href'))
                            article = find_article.group(1).replace('/url?q=', '')
                            if article.startswith('https://'):
                                articles.append(article)
                                count += 1
                if count >= test_size:
                    break
            if count >= test_size:
                break
    return articles

if __name__ == '__main__':
    test_gnews_crawl()