from custom_react import app  # Import the app with custom React version
import dash
import pandas as pd
from dash import dcc, html, Input, Output, State, ctx
import plotly
import plotly.express as px
import re

app.title = "BESS Fire Incidents"

# Print Dash and Plotly versions
print(f"Dash version: {dash.__version__}")
print(f"Plotly version: {plotly.__version__}")

# Load the Excel file
df = pd.read_excel("Failure_DB_List_2_updated.xlsx", sheet_name="Failure_DB_List_2_updated")
print(f"Initial DataFrame rows: {len(df)}")
print(f"DataFrame columns: {df.columns.tolist()}")

# Clean missing values: separate numerical and non-numerical columns
numerical_cols = df.select_dtypes(include=['float64', 'int64']).columns
string_cols = df.select_dtypes(include=['object']).columns
df[numerical_cols] = df[numerical_cols].fillna(0)
df[string_cols] = df[string_cols].fillna("-")

# Debug lat/lon extraction
print("Sample of Custom location (Lat, Lon) column:")
print(df["Custom location (Lat, Lon)"].head(10))

# Extract lat/lon with improved error handling
def extract_lat_lon(coord, part):
    try:
        if coord == "-" or not isinstance(coord, str) or "," not in coord:
            return None
        parts = coord.split(",")
        value = float(parts[0].strip()) if part == "lat" else float(parts[1].strip())
        # Validate lat/lon ranges
        if part == "lat" and not (-90 <= value <= 90):
            return None
        if part == "lon" and not (-180 <= value <= 180):
            return None
        return value
    except (ValueError, IndexError):
        return None

df["lat"] = df["Custom location (Lat, Lon)"].apply(lambda x: extract_lat_lon(x, "lat"))
df["lon"] = df["Custom location (Lat, Lon)"].apply(lambda x: extract_lat_lon(x, "lon"))
print(f"Rows after lat/lon extraction: {len(df)}")
print(f"Rows with valid lat/lon: {len(df[df['lat'].notnull() & df['lon'].notnull()])}")

# Normalize Location values (ensure consistency for IDs)
df["Location"] = df["Location"].str.strip().str.replace(r'[^a-zA-Z0-9\s]', '', regex=True).str.replace(r'\s+', ' ', regex=True)
print(f"Unique Locations before grouping: {len(df['Location'].unique())}")

# Extract Year of Incident if a date column exists
if "Date of Incident" in df.columns:
    df["Year of Incident"] = pd.to_datetime(df["Date of Incident"], errors="coerce").dt.year
else:
    print("No 'Date of Incident' column found to extract Year of Incident.")

# Group by Location, aggregating other columns
agg_dict = {col: "first" if col in ["lat", "lon", "Country"] else list for col in df.columns if col not in ["Location"]}
grouped_df = df.groupby("Location").agg(agg_dict).reset_index()

# Add a column for the number of incidents
grouped_df["Incident Count"] = df.groupby("Location").size().values

# Add an id column for consistency (normalize to match selected_location)
grouped_df["id"] = grouped_df["Location"].str.strip().str.replace(r'[^a-zA-Z0-9\s]', '', regex=True).str.replace(r'\s+', ' ', regex=True)
print(f"Grouped DataFrame rows: {len(grouped_df)}")
print(f"Grouped DataFrame columns: {grouped_df.columns.tolist()}")
print(f"Grouped Locations in grouped_df: {grouped_df['Location'].tolist()}")
print(f"Grouped IDs in grouped_df: {grouped_df['id'].tolist()}")

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
    return ""

# Dash app layout
app.layout = html.Div([
    # Main container
    html.Div([
        # Filter section at the top
        html.Div([
            html.H1("BESS Fire Incidents Dashboard", style={"textAlign": "center"}),
            html.Label("Filter by Column:"),
            dcc.Dropdown(
                id="filter-column",
                options=[{"label": col, "value": col} for col in df.columns if col not in ["lat", "lon", "id"]],
                value="Country",
                style={"width": "200px", "margin": "10px"}
            ),
            html.Label("Filter Value:"),
            dcc.Input(
                id="filter-value",
                type="text",
                placeholder="Enter filter value",
                style={"width": "200px", "margin": "10px"}
            ),
            html.Button("Apply Filter", id="apply-filter", n_clicks=0, style={"margin": "10px"}),
            html.Button("Reset Filter", id="reset-filter", n_clicks=0, style={"margin": "10px"}),
        ], id="filter-section", style={"padding": "10px", "backgroundColor": "#f0f0f0", "borderBottom": "1px solid #ccc", "textAlign": "center"}),

        # Dashboard content (cards on left, map and chart on right)
        html.Div([
            # Left section (cards)
            html.Div(
                id="left-section",
                className="left-section",
                style={"width": "40%", "overflowY": "auto", "padding": "10px", "borderRight": "1px solid #ccc", "maxHeight": "80vh"}
            ),

            # Right section (map at top, chart below)
            html.Div([
                # Map section
                html.Div(
                    id="map-section",
                    children=[
                        html.H3("Incident Map", style={"textAlign": "center"}),
                        html.Div(id="right-section", style={"height": "600px", "width": "100%"})
                    ]
                ),

                # Chart section
                html.Div([
                    html.Label("Plot Incidents by:"),
                    dcc.Dropdown(
                        id="plot-column",
                        options=[
                            {"label": "Country", "value": "Country"}
                        ] + (
                            [{"label": "Year of Incident", "value": "Year of Incident"}] if "Year of Incident" in df.columns else []
                        ),
                        value="Country",
                        style={"width": "200px", "margin": "10px"}
                    ),
                    dcc.Graph(id="bar-plot", style={"height": "400px", "margin": "20px", "width": "100%"})
                ], id="chart-section")
            ], id="right-column", style={"width": "60%", "display": "flex", "flexDirection": "column", "overflowY": "auto", "maxHeight": "80vh"})
        ], id="dashboard-content", style={"display": "flex", "flex": "1"})
    ], id="app-container", style={"display": "flex", "flexDirection": "column", "minHeight": "100vh"}),

    dcc.Store(id="selected-location", data=None),
    dcc.Store(id="filtered-df", data=df.to_dict("records")),
    dcc.Store(id="filtered-grouped-df", data=grouped_df.to_dict("records")),
    html.Div(id="debug-output"),
    html.Div(id="debug-log", style={"color": "red", "padding": "10px"}),
    # Add a container for injecting JavaScript
    html.Div(id="scroll-script-container", style={"display": "none"})
])

# Callback to filter the DataFrame
@app.callback(
    Output("filtered-df", "data"),
    Output("filtered-grouped-df", "data"),
    Output("debug-log", "children"),
    Input("apply-filter", "n_clicks"),
    Input("reset-filter", "n_clicks"),
    State("filter-column", "value"),
    State("filter-value", "value")
)
def filter_dataframe(apply_clicks, reset_clicks, filter_column, filter_value):
    ctx_triggered = ctx.triggered_id
    debug_msg = f"Filter triggered by: {ctx_triggered}, filter_column: {filter_column}, filter_value: {filter_value}"
    print(debug_msg)

    if ctx_triggered == "reset-filter":
        grouped = grouped_df.to_dict("records")
        return df.to_dict("records"), grouped, "Filter reset."

    if ctx_triggered == "apply-filter" and filter_column and filter_value:
        filtered_df = df.copy()
        if filter_column in numerical_cols:
            try:
                filter_value = float(filter_value)
                filtered_df = filtered_df[filtered_df[filter_column] == filter_value]
            except ValueError:
                return df.to_dict("records"), grouped_df.to_dict("records"), "Invalid numerical filter value."
        else:
            filtered_df = filtered_df[filtered_df[filter_column].str.contains(filter_value, case=False, na=False)]
        
        if not filtered_df.empty:
            filtered_grouped_df = filtered_df.groupby("Location").agg({
                col: "first" if col in ["lat", "lon", "Country"] else list for col in filtered_df.columns if col not in ["Location"]
            }).reset_index()
            filtered_grouped_df["Incident Count"] = filtered_df.groupby("Location").size().values
            filtered_grouped_df["id"] = filtered_grouped_df["Location"].str.strip().str.replace(r'[^a-zA-Z0-9\s]', '', regex=True).str.replace(r'\s+', ' ', regex=True)
        else:
            filtered_grouped_df = filtered_df.groupby("Location").agg({
                col: "first" if col in ["lat", "lon", "Country"] else list for col in filtered_df.columns if col not in ["Location"]
            }).reset_index()
            filtered_grouped_df["Incident Count"] = 0
            filtered_grouped_df["id"] = filtered_grouped_df["Location"].str.strip().str.replace(r'[^a-zA-Z0-9\s]', '', regex=True).str.replace(r'\s+', ' ', regex=True)

        return filtered_df.to_dict("records"), filtered_grouped_df.to_dict("records"), "Filter applied."
    
    grouped = grouped_df.to_dict("records")
    return df.to_dict("records"), grouped, "No filter applied."

# Callback to generate the bar plot
@app.callback(
    Output("bar-plot", "figure"),
    Input("filtered-df", "data"),
    Input("plot-column", "value")
)
def update_bar_plot(filtered_df_data, plot_column):
    print(f"Bar plot callback triggered with plot_column: {plot_column}")
    filtered_df = pd.DataFrame(filtered_df_data)
    print(f"Bar plot filtered_df rows: {len(filtered_df)}")
    if filtered_df.empty:
        return px.bar(title="No data to plot")

    plot_data = filtered_df.groupby(plot_column).size().reset_index(name="Count")
    fig = px.bar(
        plot_data,
        x=plot_column,
        y="Count",
        title=f"Number of Incidents by {plot_column}",
        labels={plot_column: plot_column, "Count": "Number of Incidents"},
        color=plot_column
    )
    fig.update_layout(
        xaxis_title=plot_column,
        yaxis_title="Number of Incidents",
        showlegend=False
    )
    return fig

# Cards generator with scroll script injection
@app.callback(
    Output("left-section", "children"),
    Output("scroll-script-container", "children"),
    Input("selected-location", "data"),
    Input("filtered-grouped-df", "data")
)
def render_cards(selected_id, filtered_grouped_df_data):
    print(f"Render cards triggered with selected_id: '{selected_id}'")
    filtered_grouped_df = pd.DataFrame(filtered_grouped_df_data)
    print(f"Render cards filtered_grouped_df rows: {len(filtered_grouped_df)}")
    print(f"Render cards columns: {filtered_grouped_df.columns.tolist()}")
    print(f"Render cards Locations: {filtered_grouped_df['Location'].tolist()}")
    print(f"Render cards IDs: {filtered_grouped_df['id'].tolist()}")
    if filtered_grouped_df.empty:
        return html.Div("No data matches the filter criteria.", style={"color": "red", "textAlign": "center"}), []

    cards = []
    for _, row in filtered_grouped_df.iterrows():
        is_selected = row["id"] == selected_id
        card_class = "card selected" if is_selected else "card"

        # Special handling for certain columns
        capacities = row["Capacity (MW)"] if isinstance(row["Capacity (MW)"], list) else [row["Capacity (MW)"]]
        power_texts = []
        for mw in capacities:
            color = get_mw_color(mw)
            power_texts.append(html.Div(f"{mw} MW", style={"fontWeight": "bold", "fontSize": "20px", "color": color}))

        flag_url = get_flag_url(row["Country"])
        flag_img = html.Img(src=flag_url, style={"height": "30px"}) if flag_url else None

        images = []
        source_urls = row["Source URL 1"] if isinstance(row["Source URL 1"], list) else [row["Source URL 1"]]
        for url in source_urls:
            if url != "-" and isinstance(url, str) and any(ext in url for ext in [".jpg", ".png", ".jpeg", ".webp"]):
                images.append(html.Img(src=url, style={"width": "100%", "height": "auto", "marginTop": "10px"}))

        # Dynamically display all columns (excluding certain ones)
        details = []
        exclude_columns = ["lat", "lon", "id", "Location", "Capacity (MW)", "Source URL 1", "Incident Count"]
        for col in filtered_grouped_df.columns:
            if col in exclude_columns:
                continue
            value = row[col]
            if isinstance(value, list):
                value = ", ".join(map(str, value)) if value else "-"
            details.append(
                html.Div([
                    html.Span(f"{col}: ", style={"fontWeight": "bold"}),
                    html.Span(str(value))
                ])
            )

        # Add Incident Count separately
        incident_count = row["Incident Count"]
        details.append(
            html.Div([
                html.Span("Number of Incidents: ", style={"fontWeight": "bold"}),
                html.Span(str(incident_count))
            ])
        )

        card = html.Div([
            html.H3(f"{row['Location']} ({incident_count} incidents)"),
            html.Div(power_texts + [flag_img], style={"display": "flex", "gap": "10px", "alignItems": "center"}),
            html.Div(details),
            html.Div(images)
        ],
        id=f"card-{row['id']}",
        className=card_class,
        **{
            "data-location": row["Location"],
            "data-lat": row["lat"],
            "data-lon": row["lon"]
        },
        style={"border": "1px solid #ccc", "borderRadius": "10px", "backgroundColor": "#f9f9f9", "cursor": "pointer", "marginBottom": "10px", "padding": "10px"},
        n_clicks=0)
        cards.append(card)

    # Inject JavaScript to scroll to the selected card
    scroll_script = []
    if selected_id:
        scroll_script = html.Script(f"""
            setTimeout(() => {{
                console.log("Server-side scroll triggered for selected_id: '{selected_id}'");
                const targetCard = document.getElementById('card-{selected_id}');
                const cardStack = document.getElementById('left-section');
                if (targetCard && cardStack) {{
                    console.log("Scrolling to card: 'card-{selected_id}'");
                    cardStack.scrollTop = targetCard.offsetTop - cardStack.offsetTop - 10;
                }} else {{
                    console.log("Target card or card stack not found:", targetCard, cardStack);
                }}
            }}, 100);
        """)

    return cards, scroll_script

# Simplified map rendering callback
@app.callback(
    Output("right-section", "children"),
    Input("selected-location", "data"),
    Input("filtered-grouped-df", "data")
)
def render_map(selected_location, filtered_grouped_df_data):
    print(f"Render map triggered with selected_location: '{selected_location}'")
    filtered_grouped_df = pd.DataFrame(filtered_grouped_df_data)
    print(f"Render map filtered_grouped_df rows: {len(filtered_grouped_df)}")
    print(f"Render map Locations: {filtered_grouped_df['Location'].tolist()}")
    if filtered_grouped_df.empty:
        return html.Div("No data matches the filter criteria.", style={"color": "red", "textAlign": "center"})

    # Filter rows with valid lat/lon for the map
    map_df = filtered_grouped_df[filtered_grouped_df["lat"].notnull() & filtered_grouped_df["lon"].notnull()]
    print(f"Map rows with valid lat/lon: {len(map_df)}")
    if map_df.empty:
        return html.Div("No valid lat/lon data for map.", style={"color": "red", "textAlign": "center"})

    fig = px.scatter_mapbox(
        map_df,
        lat="lat",
        lon="lon",
        hover_name="Location",
        size="Incident Count",
        zoom=2,
        height=600
    )
    fig.update_layout(mapbox_style="open-street-map", margin={"r":0,"t":0,"l":0,"b":0})

    colors = ["red" if loc == selected_location else "blue" for loc in map_df["Location"]]
    print(f"Marker colors: {colors}")
    fig.update_traces(marker=dict(color=colors))

    if selected_location and selected_location in map_df["Location"].values:
        selected_row = map_df[map_df["Location"] == selected_location].iloc[0]
        fig.update_layout(
            mapbox_center={"lat": selected_row["lat"], "lon": selected_row["lon"]},
            mapbox_zoom=10
        )

    return dcc.Graph(id="map-graph", figure=fig, style={"width": "100%", "height": "100%"})

# Click interaction (map ↔ card)
@app.callback(
    Output("selected-location", "data"),
    Output("debug-output", "children"),
    Input("map-graph", "clickData"),
    Input({"type": "card", "index": dash.ALL}, "n_clicks"),
    State({"type": "card", "index": dash.ALL}, "id"),
    prevent_initial_call=True
)
def sync_selection(map_click, card_clicks, card_ids):
    triggered = ctx.triggered_id
    if triggered == "map-graph" and map_click:
        selected = map_click["points"][0]["hovertext"]
        selected = selected.strip()
        selected = re.sub(r'[^a-zA-Z0-9\s]', '', selected)
        selected = re.sub(r'\s+', ' ', selected)
        print(f"Map click: Selected location = '{selected}'")
        return selected, f"Selected location (map): {selected}"
    elif isinstance(triggered, dict) and "index" in triggered:
        clicked_id = card_ids[card_ids.index(triggered)]
        selected = clicked_id.replace("card-", "")
        selected = selected.strip()
        selected = re.sub(r'[^a-zA-Z0-9\s]', '', selected)
        selected = re.sub(r'\s+', ' ', selected)
        print(f"Card click: Selected location = '{selected}'")
        return selected, f"Selected location (card): {selected}"
    return dash.no_update, dash.no_update

if __name__ == "__main__":
    app.run(debug=True)