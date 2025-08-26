import streamlit as st
import pandas as pd

from app.data import load_sheet, coerce_date_column, safe_number
from app.charts import line_chart, area_chart
from app.layout import make_sidebar


st.set_page_config(page_title="Financial Dashboard", layout="wide")

GOOGLE_SHEET_URL_DEFAULT = (
	"https://docs.google.com/spreadsheets/d/1HM_Jxv6zQzr-O5Spt06uq2HTyX1yFTVju2jzVjneL5M/edit?gid=462380555"
)


def _prepare(df: pd.DataFrame) -> pd.DataFrame:
	# Attempt common column conversions
	for col in df.columns:
		if "date" in col.lower() or col.endswith(("월", "날짜")):
			df = coerce_date_column(df, col)
		elif df[col].dtype == object:
			# Best-effort numeric conversion for money-like fields
			maybe_numeric = safe_number(df[col])
			# Only replace if we actually got numbers in many rows
			if pd.notna(maybe_numeric).sum() >= max(3, int(0.5 * len(maybe_numeric))):
				df[col] = maybe_numeric
	return df


def main():
	make_sidebar()
	st.title("재무 대시보드")

	# Manual refresh button: clears cached data and reruns
	col_a, col_b = st.columns([1, 3])
	with col_b:
		if st.button("데이터 수동고침", type="primary"):
			st.cache_data.clear()
			st.rerun()

	url = st.text_input("Google Sheets URL", value=GOOGLE_SHEET_URL_DEFAULT)
	with st.spinner("데이터 불러오는 중..."):
		df = load_sheet(url)
		df = _prepare(df)

	st.caption(f"행 {len(df)} · 열 {len(df.columns)}")

	# Layout similar to screenshot: 2-column top grid then 3-column sections
	row1_col1, row1_col2 = st.columns([2, 1])
	with row1_col1:
		# Try to pick columns heuristically
		date_col = next((c for c in df.columns if str(df[c].dtype).startswith("datetime")), df.columns[0])
		numeric_cols = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
		if len(numeric_cols) >= 1:
			st.plotly_chart(line_chart(df, date_col, numeric_cols[:1], "순자산합계"), use_container_width=True)
	with row1_col2:
		if len(numeric_cols) >= 2:
			st.plotly_chart(area_chart(df, date_col, numeric_cols[1], "Overall"), use_container_width=True)

	row2_col1, row2_col2 = st.columns(2)
	with row2_col1:
		if len(numeric_cols) >= 2:
			st.plotly_chart(line_chart(df, date_col, [numeric_cols[0]], "자산추세"), use_container_width=True)
	with row2_col2:
		if len(numeric_cols) >= 3:
			st.plotly_chart(line_chart(df, date_col, [numeric_cols[2]], "부채추세"), use_container_width=True)

	st.divider()
	row3_col1 = st.container()
	with row3_col1:
		if len(numeric_cols) >= 4:
			st.plotly_chart(line_chart(df, date_col, numeric_cols[:4], "ISA / 기타"), use_container_width=True)

	row4_col1, row4_col2 = st.columns(2)
	with row4_col1:
		if len(numeric_cols) >= 5:
			st.plotly_chart(line_chart(df, date_col, [numeric_cols[4]], "나이키주식"), use_container_width=True)
	with row4_col2:
		if len(numeric_cols) >= 6:
			st.plotly_chart(line_chart(df, date_col, [numeric_cols[5]], "미래퇴직연금"), use_container_width=True)


if __name__ == "__main__":
	main()


