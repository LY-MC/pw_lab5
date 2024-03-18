import sys
import urllib.parse
import socket
import re


def make_request(url):
    try:
        parsed_url = urllib.parse.urlparse(url)
        host = parsed_url.netloc
        path = parsed_url.path if parsed_url.path else '/'
        port = 443 if parsed_url.scheme == 'https' else 80

        with socket.create_connection((host, port)) as sock:
            sock.sendall(f"GET {path} HTTP/1.1\r\nHost: {host}\r\nConnection: close\r\n\r\n".encode())
            response = b""
            while True:
                chunk = sock.recv(4096)
                if not chunk:
                    break
                response += chunk

        response_str = response.decode()

        content_index = response_str.find('\r\n\r\n')
        if content_index != -1:
            response_str = response_str[content_index + 4:]
            return response_str
        else:
            raise Exception("No content found in the HTTP response")
    except Exception as e:
        return None


def clean_html(html_content):
    content = re.sub(r'<style[\s\S]*?</style>', '', html_content)
    content = re.sub(r'<[^>]*>', '', content)
    return content


def search_term(terms):
    try:
        search_url = f"https://www.google.com/search?q={urllib.parse.quote(' '.join(terms))}"

        print("Search URL:", search_url)

        search_response = make_request(search_url)

        if search_response:
            print("Top 10 search results:")
            print(search_response.split('\n')[:10])
        else:
            print("Failed to fetch search results.")
    except Exception as e:
        print(f"An error occurred during search: {e}")


def main():
    if len(sys.argv) < 2 or sys.argv[1] == '-h':
        print("Usage: go2web -u <URL> | go2web -s <search-term>")
        sys.exit(1)

    if sys.argv[1] == '-u':
        if len(sys.argv) < 3:
            print("Please provide a URL after -u option")
            sys.exit(1)
        url = sys.argv[2]
        response = make_request(url)
        if response:
            cleaned_content = clean_html(response)
            print(cleaned_content)
        else:
            print("Failed to fetch content from the URL.")
    elif sys.argv[1] == '-s':
        if len(sys.argv) < 3:
            print("Please provide a search term after -s option")
            sys.exit(1)
        search_term(' '.join(sys.argv[2:]))
    else:
        print("Invalid option. Use -u for URL or -s for search term.")
        sys.exit(1)


if __name__ == "__main__":
    main()
