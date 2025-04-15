import dash

# Define the Dash app with custom React version
app = dash.Dash(__name__, suppress_callback_exceptions=True)

# Use React 17 instead of React 18 to avoid lifecycle warnings
app.config.external_scripts = [
    "https://unpkg.com/react@17.0.2/umd/react.production.min.js",
    "https://unpkg.com/react-dom@17.0.2/umd/react-dom.production.min.js"
]