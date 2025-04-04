from flask import Flask, render_template, request
import pandas as pd
import folium
import plotly.express as px
import plotly
import json
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse
import logging
import sys

app = Flask(__name__)

# Setup logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

print("Loading CSV...", file=sys.stderr)
df = pd.read_csv('Failure_DB_List_1.csv')
print("CSV loaded!", file=sys.stderr)

# Hardcoded clean URLs
hardcoded_urls = [
    "https://www.technologyreview.com/2025/02/13/1111843/battery-fire-moss-landing-power-plant/",
    "https://www.energystoragejournal.com/belgiums-li-ion-ess-fire-cause-still-unknown-two-months-later/",
    "https://cfpa-e.eu/fire-in-a-battery-energy-storage-system/",
    "https://insideclimatenews.org/news/01022025/moss-landing-battery-fire-contamination-health-fears/"
]

# Cache for URL previews
preview_cache = {}

def get_url_preview(url):
    # Check cache first
    if url in preview_cache:
        logger.debug(f"Using cached preview for: {url}")
        return preview_cache[url]
    
    if not url or not isinstance(url, str) or not url.strip() or not url.startswith(('http://', 'https://')):
        logger.debug(f"Skipping invalid URL: {url}")
        return {'title': 'Invalid URL', 'description': '', 'image': '', 'url': url or 'N/A'}
    
    if 'box.com' in url.lower():
        logger.debug(f"Skipping Box.com URL: {url}")
        return {'title': 'Box.com Link (Preview Skipped)', 'description': '', 'image': '', 'url': url}
    
    try:
        logger.debug(f"Fetching preview for: {url}")
        response = requests.get(url, timeout=10, headers={'User-Agent': 'Mozilla/5.0'}, allow_redirects=True)
        response.raise_for_status()
        if response.headers.get('Content-Type', '').startswith('application/pdf'):
            preview = {'title': urlparse(url).netloc or 'PDF Document', 'description': '', 'image': '', 'url': url}
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
        
        # Cache the result
        preview_cache[url] = preview
        return preview
    except Exception as e:
        logger.debug(f"Error for {url}: {e}")
        return {'title': 'Preview Unavailable', 'description': '', 'image': '', 'url': url}

# Pre-fetch previews at startup
print("Pre-fetching URL previews...", file=sys.stderr)
for url in hardcoded_urls:
    get_url_preview(url)
print("Pre-fetching complete!", file=sys.stderr)

@app.route('/favicon.ico')
def favicon():
    return '', 204

@app.route('/')
def index():
    print(f"Index route hit! Request path: {request.path}", file=sys.stderr)
    # Process incidents from CSV, ignore Source URL
    incidents = df.to_dict('records')
    for incident in incidents:
        # Use cached previews
        incident['previews'] = [preview_cache[url] for url in hardcoded_urls]

    # Graph 1: Enclosure Type
    enclosure_counts = df['Enclosure Type'].value_counts().reset_index()
    enclosure_counts.columns = ['Enclosure Type', 'Count']
    fig1 = px.bar(enclosure_counts, x='Enclosure Type', y='Count', title='Incidents by Enclosure Type')
    graph1_json = json.dumps(fig1, cls=plotly.utils.PlotlyJSONEncoder)

    # Graph 2: Capacity by Location
    capacity_by_location = df.groupby('Location')['Capacity (MWh)'].sum().reset_index()
    fig2 = px.bar(capacity_by_location, x='Location', y='Capacity (MWh)', title='Capacity by Location')
    graph2_json = json.dumps(fig2, cls=plotly.utils.PlotlyJSONEncoder)

    # Map (all incidents)
    m = folium.Map(location=[20, 0], zoom_start=2)
    for _, row in df.iterrows():
        if pd.notna(row['Custom location (Lat, Lon)']) and isinstance(row['Custom location (Lat, Lon)'], str):
            try:
                lat, lon = map(float, row['Custom location (Lat, Lon)'].split(','))
                folium.Marker([lat, lon], popup=row['Location']).add_to(m)
            except ValueError:
                continue
    map_html = m._repr_html_()

    print("Rendering template...", file=sys.stderr)
    return render_template('index.html', incidents=incidents, graph1_json=graph1_json, 
                           graph2_json=graph2_json, map_html=map_html)

if __name__ == '__main__':
    print("Starting Flask server...", file=sys.stderr)
    app.run(host='0.0.0.0', port=5000, debug=True)