import pandas as pd
import dash
from dash import dcc, html, Input, Output, State, ctx
import plotly.express as px

# Load the Excel file
df = pd.read_excel("Failure_DB_List_2_updated.xlsx", sheet_name="Failure_DB_List_2_updated")

# Clean missing values
df.fillna("-", inplace=True)

# Extract lat/lon
df["lat"] = df["Custom location (Lat, Lon)"].apply(lambda x: float(str(x).split(",")[0].strip()) if x != "-" else None)
df["lon"] = df["Custom location (Lat, Lon)"].apply(lambda x: float(str(x).split(",")[1].strip()) if x != "-" else None)

# Filter rows with valid lat/lon
df = df[df["lat"].notnull() & df["lon"].notnull()]

# Add ID column
df["id"] = df["Location"]

# Power color helper
def get_mw_color(mw):
    try:
        mw = float(mw)
        if mw < 10: return "green"
        elif mw < 50: return "orange"
        else: return "red"
    except:
        return "gray"

# Flag helper (based on 'Country' column)
def get_flag_url(country):
    country = country.lower()
    if "usa" in country or "united states" in country:
        return "https://flagcdn.com/us.svg"
    elif "australia" in country:
        return "https://flagcdn.com/au.svg"
    elif "germany" in country:
        return "https://flagcdn.com/de.svg"
    elif "uk" in country or "united kingdom" in country:
        return "https://flagcdn.com/gb.svg"
    elif "china" in country:
        return "https://flagcdn.com/cn.svg"
    elif "japan" in country:
        return "https://flagcdn.com/jp.svg"
    # Add more countries as needed
    return ""

# Base map
map_fig = px.scatter_mapbox(
    df,
    lat="lat",
    lon="lon",
    hover_name="Location",
    zoom=2,
    height=800
)
map_fig.update_layout(mapbox_style="open-street-map", margin={"r":0,"t":0,"l":0,"b":0})

# Dash app
app = dash.Dash(__name__)
app.title = "BESS Fire Incidents"

app.layout = html.Div([  
    html.H1("BESS Fire Incidents Dashboard", style={"textAlign": "center"}),

    html.Div([
        html.Div(id="card-stack", style={"width": "40%", "overflowY": "scroll", "height": "800px"}),

        html.Div([
            dcc.Graph(id="map-graph", figure=map_fig)
        ], style={"width": "60%"})
    ], style={"display": "flex"}),

    dcc.Store(id="selected-location", data=None)
])

# Cards generator
@app.callback(
    Output("card-stack", "children"),
    Input("selected-location", "data")
)
def render_cards(selected_id):
    cards = []
    for _, row in df.iterrows():
        is_selected = row["id"] == selected_id
        border = "4px solid red" if is_selected else "1px solid #ccc"

        color = get_mw_color(row["Capacity (MW)"])
        power_text = html.Div(f"{row['Capacity (MW)']} MW", style={"fontWeight": "bold", "fontSize": "20px", "color": color})

        flag_url = get_flag_url(row["Country"])  # Use 'Country' column instead of 'Location'
        flag_img = html.Img(src=flag_url, style={"height": "30px"}) if flag_url else None

        image = None
        if row["Source URL 1"] != "-" and any(ext in row["Source URL 1"] for ext in [".jpg", ".png", ".jpeg", ".webp"]):
            image = html.Img(src=row["Source URL 1"], style={"width": "100%", "height": "auto", "marginTop": "10px"})

        # Generate all field display
        details = []
        for col in df.columns:
            if col in ["lat", "lon", "id"]: continue  # skip helper cols
            val = row[col]
            if isinstance(val, float): val = f"{val:.2f}" if not pd.isna(val) else "-"
            details.append(html.Div([
                html.Span(f"{col}: ", style={"fontWeight": "bold"}),
                html.Span(val)
            ]))

        card = html.Div([
            html.H3(row["Location"]),
            html.Div([power_text, flag_img], style={"display": "flex", "gap": "10px", "alignItems": "center"}),
            html.Div(details),
            image
        ],
        id={"type": "card", "index": row["id"]},
        n_clicks=0,
        style={
            "border": border,
            "padding": "10px",
            "margin": "10px",
            "borderRadius": "10px",
            "backgroundColor": "#f9f9f9",
            "cursor": "pointer"
        })
        cards.append(card)
    return cards

# Click interaction (map ↔ card)
@app.callback(
    Output("selected-location", "data"),
    [
        Input("map-graph", "clickData"),
        Input({"type": "card", "index": dash.ALL}, "n_clicks")
    ],
    [State({"type": "card", "index": dash.ALL}, "id")],
    prevent_initial_call=True
)
def sync_selection(map_click, card_clicks, card_ids):
    triggered = ctx.triggered_id
    if triggered == "map-graph" and map_click:
        return map_click["points"][0]["hovertext"]
    if isinstance(triggered, dict) and "index" in triggered:
        return triggered["index"]
    return dash.no_update

# Update map with selection color
@app.callback(
    Output("map-graph", "figure"),
    Input("selected-location", "data")
)
def update_map_highlight(selected_id):
    colors = df["id"].apply(lambda x: "red" if x == selected_id else "blue")
    fig = px.scatter_mapbox(
        df,
        lat="lat",
        lon="lon",
        hover_name="Location",
        zoom=2,
        height=800
    )
    fig.update_traces(marker=dict(color=colors, size=12))
    fig.update_layout(mapbox_style="open-street-map", margin={"r":0,"t":0,"l":0,"b":0})
    return fig

if __name__ == "__main__":
    app.run(debug=True)
