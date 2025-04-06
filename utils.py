import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse

def get_url_preview(url):
    if not url or not isinstance(url, str) or not url.strip() or not url.startswith(('http://', 'https://')):
        return {'title': 'Invalid URL', 'description': '', 'image': '', 'url': url or 'N/A'}

    if 'box.com' in url.lower():
        return {'title': 'Box.com Link (Preview Skipped)', 'description': '', 'image': '', 'url': url}

    try:
        response = requests.get(url, timeout=10, headers={'User-Agent': 'Mozilla/5.0'}, allow_redirects=True)
        response.raise_for_status()
        if response.headers.get('Content-Type', '').startswith('application/pdf'):
            return {'title': urlparse(url).netloc or 'PDF Document', 'description': '', 'image': '', 'url': url}
        else:
            soup = BeautifulSoup(response.text, 'html.parser')
            preview = {
                'title': soup.find('meta', property='og:title') or soup.find('title'),
                'description': soup.find('meta', property='og:description'),
                'image': soup.find('meta', property='og:image'),
                'url': url
            }
            preview['title'] = preview['title'].get('content', preview['title'].text)[:100] if preview['title'] else urlparse(url).netloc
            preview['description'] = preview['description'].get('content', '')[:200] if preview['description'] else ''
            preview['image'] = preview['image'].get('content', '') if preview['image'] else ''
            return preview
    except Exception as e:
        return {'title': 'Preview Unavailable', 'description': '', 'image': '', 'url': url}