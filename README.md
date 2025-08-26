## Financial Dashboard (Streamlit)

Run this dashboard locally:

```bash
pip install -r requirements.txt
streamlit run streamlit_app.py
```

It loads data from a Google Sheets URL. Paste your sheet URL (the normal edit URL is fine, e.g. `https://docs.google.com/spreadsheets/d/<id>/edit?gid=<gid>`) and the app will fetch the CSV export for that `gid`.

If you get a permissions error, publish the sheet to the web or set sharing to anyone with the link (read-only).


