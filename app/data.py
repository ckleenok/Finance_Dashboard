import re
from typing import Optional

import pandas as pd
import requests
import streamlit as st


def _to_csv_export_url(google_sheets_url: str) -> str:
	"""Convert a Google Sheets edit URL to a CSV export URL.

	Supports URLs like:
	- https://docs.google.com/spreadsheets/d/<sheet_id>/edit?gid=<gid>

	Returns a CSV export URL targeting the same gid.
	"""
	match = re.search(r"/spreadsheets/d/([a-zA-Z0-9-_]+)", google_sheets_url)
	if not match:
		raise ValueError("Invalid Google Sheets URL: sheet id not found")
	sheet_id = match.group(1)

	# Try to capture gid; default to first sheet (gid=0) if absent
	gid_match = re.search(r"[?&]gid=(\d+)", google_sheets_url)
	gid = gid_match.group(1) if gid_match else "0"

	return (
		f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}"
	)


@st.cache_data(show_spinner=False)
def load_sheet(google_sheets_url: str, timeout_seconds: int = 20) -> pd.DataFrame:
	"""Load a Google Sheet as a DataFrame via published CSV export.

	The result is cached by Streamlit. If the sheet is not published or
	access is restricted, the request will fail.
	"""
	csv_url = _to_csv_export_url(google_sheets_url)
	response = requests.get(csv_url, timeout=timeout_seconds)
	response.raise_for_status()
	# Let pandas infer types; keep_default_na=False allows string 'NA' to stay
	# while still recognizing real blanks as NaN.
	df = pd.read_csv(pd.compat.StringIO(response.text)) if hasattr(pd, "compat") else pd.read_csv(pd.io.common.StringIO(response.text))
	return df


def coerce_date_column(df: pd.DataFrame, column_name: str) -> pd.DataFrame:
	"""Ensure a column is parsed as datetime and return a copy."""
	copy = df.copy()
	if column_name in copy.columns:
		copy[column_name] = pd.to_datetime(copy[column_name], errors="coerce")
	return copy


def safe_number(series: pd.Series) -> pd.Series:
	"""Convert strings with commas or currency symbols to numeric."""
	return (
		pd.to_numeric(
			series.astype(str)
			.str.replace(",", "", regex=False)
			.str.replace("₩", "", regex=False)
			.str.replace("$", "", regex=False)
			.str.strip(),
			errors="coerce",
		)
	)


