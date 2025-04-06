from flask import Flask, render_template, request
import pandas as pd
import folium
import plotly.express as px
import plotly
import json
from utils import get_url_preview  # Import from utils.py
import logging
import sys

app = Flask(__name__)

# Setup logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

print("Loading Excel...", file=sys.stderr)
df = pd.read_excel('Failure_DB_List_2_updated.xlsx', sheet_name='Failure_DB_List_1_updated')
print("Excel loaded!", file=sys.stderr)

# Cache for URL previews
preview_cache = {}

# Load pre-fetched previews
try:
    with open('url_previews.json', 'r') as f:
        preview_cache = json.load(f)
    print("Loaded pre-fetched previews.", file=sys.stderr)
except FileNotFoundError:
    print("url_previews.json not found. Starting with empty cache.", file=sys.stderr)

@app.route('/favicon.ico')
def favicon():
    return '', 204

@app.route('/')
def index():
    print(f"Index route hit! Request path: {request.path}", file=sys.stderr)

    # Process incidents from Excel
    incidents = df.to_dict('records')
    for incident in incidents:
        # Dynamically find URL columns
        urls = [incident.get(col) for col in df.columns if col.startswith('Source URL')]
        # Filter out empty URLs
        urls = [url for url in urls if url and isinstance(url, str)]
        # Get previews from cache, fallback to 'Preview Not Available'
        incident['previews'] = [preview_cache.get(url, {'title': 'Preview Not Available', 'description': '', 'image': '', 'url': url}) for url in urls]

    # Graph 1: Incidents by Enclosure Type
    enclosure_counts = df['Enclosure Type'].value_counts().reset_index()
    enclosure_counts.columns = ['Enclosure Type', 'Count']
    fig1 = px.bar(enclosure_counts, x='Enclosure Type', y='Count', title='Incidents by Enclosure Type')
    graph1_json = json.dumps(fig1, cls=plotly.utils.PlotlyJSONEncoder)

    # Graph 2: Capacity by Location
    df['Capacity (MWh)'] = df['Capacity (MWh)'].fillna(0)
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