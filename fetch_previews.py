import pandas as pd
import json
from utils import get_url_preview

# Load the Excel file with the specified sheet
df = pd.read_excel('Failure_DB_List_2_updated.xlsx', sheet_name='Failure_DB_List_2_updated')

# Collect all unique URLs from 'Source URL 1', 'Source URL 2', 'Source URL 3'
urls = set()
for col in ['Source URL 1', 'Source URL 2', 'Source URL 3']:
    if col in df.columns:
        urls.update(df[col].dropna().unique())

# Fetch previews for each URL
previews = {}
for url in urls:
    previews[url] = get_url_preview(url)

# Save the previews to a JSON file
with open('url_previews.json', 'w') as f:
    json.dump(previews, f, indent=4)

print("Previews fetched and saved to url_previews.json")