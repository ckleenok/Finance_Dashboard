import streamlit as st
import pandas as pd

from app.data import load_sheet, coerce_date_column, safe_number, get_series_by_letter
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

	if df.empty:
		st.warning("데이터가 비어 있습니다. 공유 설정 또는 URL을 확인하세요.")
		return

	st.caption(f"행 {len(df)} · 열 {len(df.columns)}")

	# Layout similar to screenshot: 2-column top grid then 3-column sections
	row1_col1, row1_col2 = st.columns([3, 1])
	with row1_col1:
		# Use 'AM' column for net worth
		date_col = next((c for c in df.columns if str(df[c].dtype).startswith("datetime")), df.columns[0])
		# Net worth chart
		try:
			networth_series = safe_number(get_series_by_letter(df, "AM"))
			df_networth = pd.DataFrame({date_col: df[date_col], "순자산합계": networth_series})
			st.plotly_chart(line_chart(df_networth, date_col, ["순자산합계"], "순자산합계"), use_container_width=True)
		except Exception:
			# Fallback: heuristic first numeric column
			numeric_cols = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
			if len(numeric_cols) >= 1:
				st.plotly_chart(line_chart(df, date_col, numeric_cols[:1], "순자산합계"), use_container_width=True)
		
		# Three asset charts side by side
		asset_col1, asset_col2, asset_col3 = st.columns(3)
		
		with asset_col1:
			# Stock total chart
			try:
				stock_series = safe_number(get_series_by_letter(df, "X"))
				df_stock = pd.DataFrame({date_col: df[date_col], "주식합계": stock_series})
				st.plotly_chart(line_chart(df_stock, date_col, ["주식합계"], "주식합계", height=200), use_container_width=True)
			except Exception:
				st.caption("주식합계 데이터를 불러올 수 없습니다.")
		
		with asset_col2:
			# Pension asset total chart
			try:
				pension_series = safe_number(get_series_by_letter(df, "AC"))
				df_pension = pd.DataFrame({date_col: df[date_col], "연금자산합계": pension_series})
				st.plotly_chart(line_chart(df_pension, date_col, ["연금자산합계"], "연금자산합계", height=200), use_container_width=True)
			except Exception:
				st.caption("연금자산합계 데이터를 불러올 수 없습니다.")
		
		with asset_col3:
			# Real estate asset total chart
			try:
				realestate_series = safe_number(get_series_by_letter(df, "AF"))
				df_realestate = pd.DataFrame({date_col: df[date_col], "부동산자산합계": realestate_series})
				st.plotly_chart(line_chart(df_realestate, date_col, ["부동산자산합계"], "부동산자산합계", height=200), use_container_width=True)
			except Exception:
				st.caption("부동산자산합계 데이터를 불러올 수 없습니다.")
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


