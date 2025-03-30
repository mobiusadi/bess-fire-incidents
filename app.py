from flask import Flask, render_template
import folium
import pandas as pd
import plotly.express as px
import json

app = Flask(__name__)

# Load CSV data
df = pd.read_csv('Failure_DB_List_1.csv')  # Note the '_1' suffix

@app.route('/')
def index():
    incidents = df.to_dict('records')

    # Graph 1: Incidents by Enclosure Type
    enclosure_counts = df['Enclosure Type'].value_counts().reset_index()
    enclosure_counts.columns = ['Enclosure Type', 'Count']
    fig1 = px.bar(enclosure_counts, x='Enclosure Type', y='Count', title='Incidents by Enclosure Type',
                  hover_data=['Count'], labels={'Count': 'Number of Incidents'})
    graph1_json = json.dumps(fig1, cls=plotly.utils.PlotlyJSONEncoder)

    # Graph 2: Capacity (MWh) by Location
    capacity_by_location = df.groupby('Location')['Capacity (MWh)'].sum().reset_index()
    fig2 = px.bar(capacity_by_location, x='Location', y='Capacity