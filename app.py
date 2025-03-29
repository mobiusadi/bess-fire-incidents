from flask import Flask, render_template
import pandas as pd
import folium

app = Flask(__name__)

@app.route('/')
def index():
    # Load CSV data
    df = pd.read_csv('Failure_DB_List_1.csv')
    incidents = df.to_dict(orient='records')
    return render_template('index.html', incidents=incidents)

@app.route('/map/<int:index>')
def show_map(index):
    # Load CSV and get specific incident
    df = pd.read_csv('Failure_DB_List_1.csv')
    incident = df.iloc[index]
    # Parse Custom location (Lat, Lon) assuming format "lat, lon"
    lat_lon = incident['Custom location (Lat, Lon)'].split(',')
    lat, lon = float(lat_lon[0].strip()), float(lat_lon[1].strip())
    # Create Folium map
    m = folium.Map(location=[lat, lon], zoom_start=10)
    folium.Marker([lat, lon], popup=incident['Location']).add_to(m)
    return m._repr_html_()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)