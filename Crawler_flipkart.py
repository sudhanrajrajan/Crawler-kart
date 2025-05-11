# -*- coding: utf-8 -*- 
# All packages
from requests.packages.urllib3.exceptions import InsecureRequestWarning
from itertools import cycle
import requests, json, re, random
from bs4 import BeautifulSoup, NavigableString, Tag
import gzip, xml.etree.ElementTree as ET
from io import BytesIO
import sys,os, time
from PIL import Image
from concurrent.futures import ThreadPoolExecutor, as_completed

requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
import threading
data_lock = threading.Lock()
stop_event = threading.Event()

reverse = []
datalist = []
hit_counter = 0
proxy_pool = None
proxies_list = None

USER_AGENT = ["Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/56.0.2924.76 Safari/537.36","Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/104.0.5112.79 Safari/537.36","Mozilla/5.0 (Linux; Android 10) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/113.0.5672.76 Mobile Safari/537.36","Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/104.0.5112.79 Safari/537.36"]

def get_proxy():
    global hit_counter, proxy_pool
    if(hit_counter%100 == 0):
        hit_counter = 0
        file = open("http_proxies.txt", "r")
        proxies_list = file.read().split("\n")
        file.close()
        proxy_pool = cycle(proxies_list)
    hit_counter = hit_counter + 1
    return next(proxy_pool)

def crawler(content):
    try:
        soup = BeautifulSoup(content, 'html.parser')
        title = soup.select_one('h1')
        sku = soup.select_one('link[rel=canonical]')['href'] if soup.select_one('link[rel=canonical][href]') else ""
        sku = trim_string(sku.split('/')[-1])
        desc = next((d.text.replace("Description", "").strip() for d in soup.select('.cPHDOP') if "Description" in d.text), "")
        #if len(desc) < 1:
        #    desc = soup.select_one('meta[name=Description][content]')['content'] if soup.select_one('meta[name=Description][content]') else ""
        img = soup.select_one('img[fetchpriority="high"]')
        data = {
            "Title": trim_string(title.text) if title else "","SKU": sku,
            "Description": trim_string(desc),"Image URL": trim_string(img['src']) if img else ""}

        return (data,img) if all(len(data[k]) > 1 for k in data) else None
    except Exception as e:
        pass

def trim_string(string=""):
    if string == None:
        string = ""
        
    string = str(string)
    string = string.replace("\\n", " ").replace("\\t", " ").replace("\\r", " ")
    string = re.sub(r"<.*?>", " ", string)
    string = re.sub(r"\s+", " ", string)
    string = string.strip()
    return string

def getRequest(url):
    if stop_event.is_set():
        return
    try:
        proxy = get_proxy()
        PROXYDICT = {"http":proxy, "https": proxy}
        HEADER_DETAILS = {'Upgrade-Insecure-Requests': '1','User-Agent': USER_AGENT[random.randint(0,3)]}
        if not url.strip(): return None
        response = requests.get(url, headers = HEADER_DETAILS, timeout = 10, proxies = PROXYDICT)
        response.encoding = 'utf-8'
        if response.status_code == 200:
            print(url, response)
            reverse.append(url)
            dat,img = crawler(response.text)
            if dat:
                print(dat)
                with data_lock:
                    if not stop_event.is_set():
                        image_bool = save_and_resize_image(dat['Image URL'], dat['SKU'])
                        if image_bool:
                            datalist.append(dat)
                        if len(datalist) == 50:
                            with open("Products.json", "w", encoding="utf-8") as f:
                                json.dump(datalist, f, ensure_ascii=False, indent=2)
                            stop_event.set()
        else:
            return None
    except Exception as e:
        pass

def save_and_resize_image(img_url, sku):
    try:
        output_dir="images"
        os.makedirs(output_dir, exist_ok=True)
        response = requests.get(img_url, timeout=10)
        if response.status_code != 200:
            print(f"Failed to download image for {sku}")
            return False

        image = Image.open(BytesIO(response.content)).convert("RGB")
        image = image.resize((500, 500))

        file_path = os.path.join(output_dir, f"{sku}.jpg")
        image.save(file_path, "JPEG")
        print(f"Saved image for {sku}")
        return True
    except Exception as e:
        print(f"Error saving image for {sku}: {e}")
        return False

def fetch_flipkart_sitemap_links(url):
    r = requests.get(url)
    with gzip.GzipFile(fileobj=BytesIO(r.content)) as f:
        root = ET.fromstring(f.read())
    links = {loc.text for loc in root.iter("{http://www.sitemaps.org/schemas/sitemap/0.9}loc") if '/p/' in loc.text and '/hi/' not in loc.text}
    print(f"Sample product links: {len(links)}")
    return list(links)

def fetch_flipkart_product_links(url):
    try:
        HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0 Safari/537.36"}
        r = requests.get(url, headers=HEADERS)
        soup = BeautifulSoup(r.text, "html.parser")
        product_anchors = soup.select('[data-id] a')
        links = set()
        for a in product_anchors:
            href = a.get("href")
            full_url = "https://www.flipkart.com" + href.split("?")[0]  
            links.add(full_url)

        print(f"Fetched {len(links)} links from {url}")
        return links
    except:
        pass


keywords = [
    "mobiles", "shoes", "headphones", "smartwatches", "laptops",
    "tshirts", "jackets", "jeans", "sunglasses", "backpacks",
    "trimmers", "power banks", "wireless earphones", "bluetooth speakers",
    "bedsheets", "cookware"
]
sitemap_urls = [f"https://www.flipkart.com/search?q={keyword.replace(' ', '+')}" for keyword in keywords]

all_product_links = set()
for sitemap_url in sitemap_urls:
    try:
        links = fetch_flipkart_product_links(sitemap_url)
        all_product_links.update(links)
        time.sleep(5)
    except:
        time.sleep(5)
        pass
product_links = list(all_product_links)


# READ LINKS FROM SITEMAP
#sitemap_url = "https://www.flipkart.com/sitemap_p_product_1.xml.gz"
#product_links = fetch_flipkart_sitemap_links(sitemap_url)


def compare_files(urls1, urls2):
    new_urls = sorted(set(urls1) - set(urls2))
    return new_urls


flag = True
# Loop run untill compelted 50 and products data all present 
while flag:
    domain = compare_files(product_links,reverse)
    print("-----------------------process starting----------------")
    print(len(domain))
    if len(domain) == 0:
        flag = False
    with ThreadPoolExecutor(max_workers=50) as executor:
        futures = [executor.submit(getRequest, url) for url in domain]
        for future in as_completed(futures):
            if stop_event.is_set():
                flag = False
                break

