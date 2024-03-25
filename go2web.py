import sys
from bs4 import BeautifulSoup
import socket
import ssl
import re
import hashlib
import json
import os

HTTPS_PORT = 443
HTTP_PORT = 80


def load_cache_from_json():
    if os.path.exists('http_cache.json'):
        with open('http_cache.json', 'r') as file:
            return json.load(file)
    else:
        return {}


def save_cache_to_json():
    with open('http_cache.json', 'w') as file:
        json.dump(http_cache, file)


http_cache = load_cache_from_json()


def parse_url(url):
    scheme_end = url.find("://")
    if scheme_end != -1:
        scheme = url[:scheme_end]
        url = url[scheme_end + 3:]
    else:
        scheme = "http"

    path_start = url.find("/")
    if path_start != -1:
        host_and_port = url[:path_start]
        path = url[path_start:]
    else:
        host_and_port = url
        path = "/"
    host, port = parse_host_and_port(host_and_port)
    return scheme, host, port, path


def parse_host_and_port(host_and_port):
    port_start = host_and_port.find(":")
    if port_start != -1:
        host = host_and_port[:port_start]
        port = int(host_and_port[port_start + 1:])
    else:
        host = host_and_port
        port = HTTPS_PORT
    return host, port


def get_cache_key(url):
    return hashlib.md5(url.encode('utf-8')).hexdigest()


def cache_response(url, response):
    cache_key = get_cache_key(url)
    http_cache[cache_key] = response
    save_cache_to_json()


def get_cached_response(url):
    cache_key = get_cache_key(url)
    return http_cache.get(cache_key)


def send_http_get_request(host, port, path, max_redirects=10):
    url = f"{host}:{port}{path}"
    cached_response = get_cached_response(url)
    if cached_response:
        print("Retrieved response from cache")
        return cached_response
    redirect_count = 0
    while redirect_count < max_redirects:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((host, port))

        if port == HTTPS_PORT:
            context = ssl.create_default_context()
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE
            sock = context.wrap_socket(sock, server_hostname=host)

        request = f"GET {path} HTTP/1.1\r\nHost: {host}\r\nUser-Agent: YourAppName/1.0 (+http://yourwebsite.com)\r\nConnection: close\r\n\r\n"
        sock.sendall(request.encode())

        response = b""
        while True:
            data = sock.recv(2048)
            if not data:
                break
            response += data

        sock.close()

        headers, body = response.split(b"\r\n\r\n", 1)
        headers_str = headers.decode('utf-8')
        body_str = body.decode('utf-8', 'replace')

        status_code = int(headers_str.split(' ')[1])
        if 300 <= status_code < 400:
            print("Status code:", status_code)
            location_match = re.search(r"Location: (.+)", headers_str)
            if location_match:
                new_location = location_match.group(1).strip()
                print(f"Redirecting to: {new_location}")
                scheme, host, port, path = parse_url(new_location)
                port = HTTPS_PORT if scheme == 'https' else HTTP_PORT
                redirect_count += 1
                continue
            else:
                break
        else:
            break

    if redirect_count == max_redirects:
        raise Exception(f"Stopped after {max_redirects} redirects. Last attempted URL: {path}")

    cache_response(url, (headers_str, body_str))
    return headers_str, body_str


def parse_html_body(html_body):
    soup = BeautifulSoup(html_body, 'html.parser')
    body_text = soup.body.get_text(separator='\n\n', strip=True)

    return body_text.strip()


def parse_search_response(html_body):
    soup = BeautifulSoup(html_body, 'html.parser')

    final_results = []
    index = 1
    results = soup.find_all('div', class_='egMi0 kCrYT')

    while index <= len(results):
        link = results[index - 1].findChild('a')
        if link:
            url = link.get('href')
            if url.startswith('/url?q='):
                url = url.split('/url?q=')[1].split('&sa=')[0]
            desc = link.get_text()

            final_results.append((index, desc, url))
            index += 1
        else:
            break

    return final_results


def google_search(terms):
    query = '+'.join(term.replace(" ", "+") for term in terms)
    url = f"https://www.google.com/search?q={query}"
    scheme, host, port, path = parse_url(url)

    _, body = send_http_get_request(host, port, path)
    return parse_search_response(body)


def main():
    if len(sys.argv) < 2 or sys.argv[1] == '-h':
        print("Usage: go2web -u <URL>  # Fetch content from URL\n"
              "       go2web -s <search-term>  # Search Google\n"
              "       go2web -h  # Show usage information")
        sys.exit(1)

    elif sys.argv[1] == '-u':
        if len(sys.argv) < 3:
            print("Please provide a URL.")
            sys.exit(1)
        url = sys.argv[2]
        scheme, host, port, path = parse_url(url)

        headers, body = send_http_get_request(host, port, path)
        if 'application/json' in headers:
            print(body)
        else:
            print(parse_html_body(body))

    elif sys.argv[1] == '-s':
        if len(sys.argv) < 3:
            print("Please provide search terms.")
            sys.exit(1)
        terms = sys.argv[2:]
        results = google_search(terms)
        for index, desc, link in results:
            print(f"{index}. {desc};\nAccess link: {link}\n\n")
    else:
        print("Invalid option.")
        sys.exit(1)


if __name__ == "__main__":
    main()

