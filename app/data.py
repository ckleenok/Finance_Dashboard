import io
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
	"""Load a Google Sheet as a DataFrame via CSV export with friendly errors."""
	csv_url = _to_csv_export_url(google_sheets_url)
	try:
		response = requests.get(
			csv_url,
			timeout=timeout_seconds,
			headers={"User-Agent": "Mozilla/5.0 (Streamlit Financial Dashboard)"},
		)
		response.raise_for_status()
	except requests.HTTPError:
		st.error(
			"Google Sheet에 접근할 수 없습니다. 시트를 '링크가 있는 모든 사용자 보기'로 공유하거나 '웹에 게시' 후 다시 시도하세요."
		)
		st.caption(f"요청 URL: {csv_url}")
		return pd.DataFrame()
	except requests.RequestException:
		st.error("네트워크 오류로 데이터를 불러오지 못했습니다. 잠시 후 다시 시도하세요.")
		return pd.DataFrame()

	# Parse CSV text safely
	df = pd.read_csv(io.StringIO(response.text))
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



def column_index_from_letter(letter: str) -> int:
	"""Convert Excel-style column letter to 0-based index.

	Examples: 'A' -> 0, 'Z' -> 25, 'AA' -> 26, 'AM' -> 38.
	"""
	letter = letter.strip().upper()
	value = 0
	for ch in letter:
		if not ("A" <= ch <= "Z"):
			raise ValueError("Invalid column letter")
		value = value * 26 + (ord(ch) - ord("A") + 1)
	return value - 1


def get_series_by_letter(df: pd.DataFrame, letter: str) -> pd.Series:
	idx = column_index_from_letter(letter)
	if idx < 0 or idx >= df.shape[1]:
		raise IndexError(f"Column letter {letter} out of range for dataframe with {df.shape[1]} columns")
	return df.iloc[:, idx]

