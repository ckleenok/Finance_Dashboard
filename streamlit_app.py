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
		if "date" in col.lower() or col.endswith(("월", "날짜", "일", "시간")):
			df = coerce_date_column(df, col)
		elif df[col].dtype == object:
			# Best-effort numeric conversion for money-like fields
			maybe_numeric = safe_number(df[col])
			# Only replace if we actually got numbers in many rows
			if pd.notna(maybe_numeric).sum() >= max(3, int(0.5 * len(maybe_numeric))):
				df[col] = maybe_numeric
	
	# Additional date detection for columns that might contain dates
	for col in df.columns:
		if df[col].dtype == object and col not in [c for c in df.columns if str(df[c].dtype).startswith("datetime")]:
			try:
				# Try to detect if this column contains dates
				sample_values = df[col].dropna().head(20)
				if len(sample_values) > 0:
					# Check if values look like dates
					date_patterns = [
						r'\d{4}-\d{1,2}-\d{1,2}',  # YYYY-MM-DD
						r'\d{1,2}/\d{1,2}/\d{4}',  # MM/DD/YYYY
						r'\d{4}년\s*\d{1,2}월\s*\d{1,2}일',  # YYYY년 MM월 DD일
						r'\d{1,2}월\s*\d{1,2}일',  # MM월 DD일
					]
					
					import re
					date_like_count = 0
					for val in sample_values:
						val_str = str(val)
						if any(re.search(pattern, val_str) for pattern in date_patterns):
							date_like_count += 1
					
					# If more than 70% look like dates, convert the column
					if date_like_count >= len(sample_values) * 0.7:
						df[col] = pd.to_datetime(df[col], errors="coerce")
			except:
				continue
	
	return df


def _apply_time_filter(df: pd.DataFrame, time_filter: str) -> pd.DataFrame:
	"""
	Applies a time filter to the DataFrame based on the selected time period.
	"""
	# Find the date column - try multiple strategies
	date_col = None
	
	# Strategy 1: Look for existing datetime columns
	date_col = next((c for c in df.columns if str(df[c].dtype).startswith("datetime")), None)
	
	# Strategy 2: Look for columns with date-related names
	if not date_col:
		date_keywords = ["date", "날짜", "월", "일", "time", "시간"]
		for col in df.columns:
			if any(keyword in col.lower() for keyword in date_keywords):
				# Try to convert this column to datetime
				try:
					df_copy = df.copy()
					df_copy[col] = pd.to_datetime(df_copy[col], errors="coerce")
					# Check if conversion was successful (not all NaT)
					if df_copy[col].notna().sum() > len(df_copy) * 0.5:  # At least 50% valid dates
						date_col = col
						df[col] = df_copy[col]  # Update the original dataframe
						break
				except:
					continue
	
	# Strategy 3: Look for the first column that might be dates
	if not date_col:
		for col in df.columns:
			try:
				# Try to convert to datetime
				test_conversion = pd.to_datetime(df[col].head(10), errors="coerce")
				if test_conversion.notna().sum() >= 5:  # At least 5 out of 10 valid dates
					df[col] = pd.to_datetime(df[col], errors="coerce")
					date_col = col
					break
			except:
				continue
	
	if not date_col:
		st.warning("날짜 컬럼을 찾을 수 없습니다. 모든 데이터를 표시합니다.")
		return df  # No date column found, return all data
	
	# Get the latest date
	latest_date = df[date_col].max()
	
	if time_filter == "모든 데이터":
		return df
	elif time_filter == "최근 3개월":
		cutoff_date = latest_date - pd.Timedelta(days=90)
	elif time_filter == "최근 6개월":
		cutoff_date = latest_date - pd.Timedelta(days=180)
	elif time_filter == "최근 9개월":
		cutoff_date = latest_date - pd.Timedelta(days=270)
	elif time_filter == "최근 12개월":
		cutoff_date = latest_date - pd.Timedelta(days=365)
	elif time_filter == "최근 18개월":
		cutoff_date = latest_date - pd.Timedelta(days=540)
	elif time_filter == "최근 24개월":
		cutoff_date = latest_date - pd.Timedelta(days=730)
	else:
		return df  # Default to all data if filter is not recognized
	
	# Filter data based on the cutoff date
	filtered_df = df[df[date_col] >= cutoff_date]
	
	return filtered_df


def main():
	time_filter = make_sidebar()
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

	# Apply time filter
	df_filtered = _apply_time_filter(df, time_filter)
	
	st.caption(f"행 {len(df_filtered)} · 열 {len(df_filtered.columns)} · 필터: {time_filter}")

	# Layout similar to screenshot: 2-column top grid then 3-column sections
	row1_col1 = st.container()
	with row1_col1:
		# Use 'AM' column for net worth
		date_col = next((c for c in df_filtered.columns if str(df_filtered[c].dtype).startswith("datetime")), df_filtered.columns[0])
		
		# Split first row into two columns: 50% for assets, 50% for net worth
		top_col1, top_col2 = st.columns(2)
		
		with top_col1:
			# Assets total chart (AG column)
			try:
				assets_series = safe_number(get_series_by_letter(df_filtered, "AG"))
				df_assets = pd.DataFrame({date_col: df_filtered[date_col], "자산합계": assets_series})
				st.plotly_chart(line_chart(df_assets, date_col, ["자산합계"], "자산합계"), use_container_width=True)
			except Exception:
				st.caption("자산합계 데이터를 불러올 수 없습니다.")
		
		with top_col2:
			# Net worth chart (AM column)
			try:
				networth_series = safe_number(get_series_by_letter(df_filtered, "AM"))
				df_networth = pd.DataFrame({date_col: df_filtered[date_col], "순자산합계": networth_series})
				st.plotly_chart(line_chart(df_networth, date_col, ["순자산합계"], "순자산합계"), use_container_width=True)
			except Exception:
				# Fallback: heuristic first numeric column
				numeric_cols = [c for c in df_filtered.columns if pd.api.types.is_numeric_dtype(df_filtered[c])]
				if len(numeric_cols) >= 1:
					st.plotly_chart(line_chart(df_filtered, date_col, numeric_cols[:1], "순자산합계"), use_container_width=True)
		
		# Three asset charts side by side
		asset_col1, asset_col2, asset_col3 = st.columns(3)
		
		with asset_col1:
			# Stock total chart
			try:
				stock_series = safe_number(get_series_by_letter(df_filtered, "X"))
				df_stock = pd.DataFrame({date_col: df_filtered[date_col], "주식합계": stock_series})
				st.plotly_chart(line_chart(df_stock, date_col, ["주식합계"], "주식합계", height=200), use_container_width=True)
			except Exception:
				st.caption("주식합계 데이터를 불러올 수 없습니다.")
		
		with asset_col2:
			# Pension asset total chart
			try:
				pension_series = safe_number(get_series_by_letter(df_filtered, "AC"))
				df_pension = pd.DataFrame({date_col: df_filtered[date_col], "연금자산합계": pension_series})
				st.plotly_chart(line_chart(df_pension, date_col, ["연금자산합계"], "연금자산합계", height=200), use_container_width=True)
			except Exception:
				st.caption("연금자산합계 데이터를 불러올 수 없습니다.")
		
		with asset_col3:
			# Real estate asset total chart
			try:
				realestate_series = safe_number(get_series_by_letter(df_filtered, "AF"))
				df_realestate = pd.DataFrame({date_col: df_filtered[date_col], "부동산자산합계": realestate_series})
				st.plotly_chart(line_chart(df_realestate, date_col, ["부동산자산합계"], "부동산자산합계", height=200), use_container_width=True)
			except Exception:
				st.caption("부동산자산합계 데이터를 불러올 수 없습니다.")
		
		# Add debt total chart below the three asset charts
		debt_col1, debt_col2, debt_col3 = st.columns(3)
		
		with debt_col1:
			# Debt total chart
			try:
				debt_series = safe_number(get_series_by_letter(df_filtered, "AL"))
				df_debt = pd.DataFrame({date_col: df_filtered[date_col], "부채합계": debt_series})
				st.plotly_chart(line_chart(df_debt, date_col, ["부채합계"], "부채합계", height=200), use_container_width=True)
			except Exception:
				st.caption("부채합계 데이터를 불러올 수 없습니다.")
		
		with debt_col2:
			# Empty column for spacing
			pass
		
		with debt_col3:
			# Empty column for spacing
			pass

	row2_col1, row2_col2 = st.columns(2)
	with row2_col1:
		if len(numeric_cols) >= 2:
			st.plotly_chart(line_chart(df_filtered, date_col, [numeric_cols[0]], "자산추세"), use_container_width=True)
	with row2_col2:
		if len(numeric_cols) >= 3:
			st.plotly_chart(line_chart(df_filtered, date_col, [numeric_cols[2]], "부채추세"), use_container_width=True)

	st.divider()
	row3_col1 = st.container()
	with row3_col1:
		if len(numeric_cols) >= 4:
			st.plotly_chart(line_chart(df_filtered, date_col, numeric_cols[:4], "ISA / 기타"), use_container_width=True)

	row4_col1, row4_col2 = st.columns(2)
	with row4_col1:
		if len(numeric_cols) >= 5:
			st.plotly_chart(line_chart(df_filtered, date_col, [numeric_cols[4]], "나이키주식"), use_container_width=True)
	with row4_col2:
		if len(numeric_cols) >= 6:
			st.plotly_chart(line_chart(df_filtered, date_col, [numeric_cols[5]], "미래퇴직연금"), use_container_width=True)


if __name__ == "__main__":
	main()


