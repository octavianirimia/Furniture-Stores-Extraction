import bs4
import concurrent.futures
import re
import requests
import tldextract



def fetch_html_content(url: str, text: bool = False) -> str:
    try:
        response = requests.get(url)
        response.raise_for_status()
        if text:
            return response.text
        return response.content

    except requests.RequestException as e:
        print(f"Error fetching the URL: {e}")
        return ""



def is_visible(element):
    if element.parent.name in ['style', 'script', 'head', 'title', 'meta', '[document]']:
        return False
    
    if isinstance(element, bs4.element.Comment):
        return False

    return True



def extract_visible_text(html):
    soup: bs4.BeautifulSoup = bs4.BeautifulSoup(markup = html, features = 'html.parser')
    texts = soup.findAll(string = True)
    visible_texts = filter(is_visible, texts)

    return " ".join(text.strip() for text in visible_texts if text.strip())



def clean_and_filter_text(text, stop_words, currency_codes) -> str:
    cleaned_text: str = re.sub(r'[^A-Za-z\s]+', '', text).lower()
    words: list[str] = cleaned_text.split()
    filtered_words: list[str] = [word for word in words if word not in stop_words and word not in currency_codes]

    return ' '.join(set(filtered_words))



def extract_text_from_url(arguments: list[tuple[str, set[str], set[str]]]) -> str:

    url, stop_words, currency_codes = arguments

    html_text: str = fetch_html_content(url, True)

    if not html_text:
        return {}

    visible_text = extract_visible_text(html_text)
    clean_text: str = clean_and_filter_text(visible_text, stop_words, currency_codes)

    return {url: clean_text}



def extract_associated_pages(url: str) -> list[str]:

    html_content: str = fetch_html_content(url)

    if not html_content:
        return []

    links: list = []
    soup: bs4.BeautifulSoup = bs4.BeautifulSoup(markup = html_content, features = 'html.parser')

    domain = tldextract.extract(url = url)
    # Find all anchor tags with a valid href attribute
    for link in soup.find_all(name = 'a', href = True):
        if link.get('href').startswith(f'https://www.{domain.domain}.{domain.suffix}'):
            links.append(link.get('href'))

    return links



def extract_website_data(urls: list, stop_words: set[str], currency_codes: set[str], file_path: str = None) -> dict:

    with concurrent.futures.ProcessPoolExecutor() as executor:
        associated_urls = executor.map(extract_associated_pages, urls)

    for item in list(associated_urls):
        if item:
            for url in item:
                urls.append(url)
    
    urls = set(urls)

    # Prepare arguments for the worker function
    arguments: list[tuple[str, set[str], set[str]]] = [(url, stop_words, currency_codes) for url in urls]

    with concurrent.futures.ProcessPoolExecutor() as executor:
        data = executor.map(extract_text_from_url, arguments)

    merged_data: dict = {}
    for item in list(data):
        if item:
            key, value = item.popitem()
            if value:
                merged_data[key] = value    

    if file_path:
        with open(file_path, 'w') as file:
            for key, value in merged_data.items():
                file.write(f"{key}: {value}\n")
    
    return merged_data