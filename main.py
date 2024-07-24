import csv
import time
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup


# noinspection HttpUrlsUsage
def clean_url(current_url, new_url):
    if new_url.startswith("#") or new_url.startswith("javascript") or new_url.startswith(
            "mailto") or new_url.startswith("?"):
        return current_url

    if new_url.startswith('http://') or new_url.startswith('https://'):
        return new_url

    return urljoin(current_url, new_url)


class Crawler:
    tag_mapping = {
        'a': {'text': "Anchor", 'source': "href"},
        'img': {'text': "Image", 'source': "src"},
        'link': {'text': "Link", 'source': "href"},
        'script': {'text': "Script", 'source': "src"}
    }

    def __init__(self, base_url, subdomain_only=False, crawl_external=False, max_links=100):
        self.base_url = base_url
        self.subdomain_only = subdomain_only
        self.crawl_external = crawl_external
        self.visited = set()
        self.output = set()
        self.max_links = max_links
        self.base_hostname = urlparse(self.base_url).hostname
        self.base_domain = '.'.join(self.base_hostname.split('.')[-2:])

    def find_links_recursive(self, url, source=(None, None)):
        if not url or url in self.visited:
            return

        if 0 < self.max_links <= len(self.visited):
            return

        print(f"[{len(self.visited) + 1}] Crawling: {url}")
        self.visited.add(url)
        hostname = urlparse(url).hostname
        domain = '.'.join(hostname.split('.')[-2:])

        try:
            response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
        except requests.exceptions.RequestException as e:
            print(e)
            # self.output.add((source[0], source[1], url))
            return
        if response.status_code != 200:
            source_type, source_url = source
            self.output.add((source_type, source_url, url))
            return

        invalid_subdomain = self.subdomain_only and hostname != self.base_hostname
        invalid_domain = not self.subdomain_only and domain != self.base_domain
        if not self.crawl_external and (invalid_subdomain or invalid_domain):
            return

        soup = BeautifulSoup(response.text, 'html.parser')

        for tag, attr in self.tag_mapping.items():
            for element in soup.find_all(tag, href=True):
                source = element.get(attr['source'])
                if not source:
                    continue
                self.find_links_recursive(clean_url(url, source), (attr['text'], url))


def main():
    base_url = input("Enter the base URL: ").strip().lower()
    if not base_url.startswith('http'):
        base_url = 'https://' + base_url
    if not base_url.endswith('/'):
        base_url += '/'
    subdomain_only = input("Crawl subdomain only? (y/N): ").strip().lower() in ['y', 'yes']
    crawl_external = input("Crawl external links? (y/N): ").strip().lower() in ['y', 'yes']
    try:
        max_links = int(input("Enter the maximum number of links to crawl (default 100): ").strip())
    except ValueError:
        max_links = 100
    crawler = Crawler(base_url, subdomain_only, crawl_external, max_links)
    start_time = time.time()
    crawler.find_links_recursive(base_url)
    end_time = time.time()
    print(f"Time taken: {end_time - start_time} seconds")
    print(f"Found {len(crawler.output)} invalid links out of {len(crawler.visited)} links.")

    with open(f'all-links-{end_time}.txt', 'w') as f:
        for link in crawler.visited:
            f.write(f'{link}\n')

    with open(f'output-{end_time}.csv', 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['Source', 'Type', 'Destination'])
        for text, source, destination in crawler.output:
            writer.writerow([source, text, destination])


if __name__ == '__main__':
    main()
