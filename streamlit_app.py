import streamlit as st
import pandas as pd

from app.data import load_sheet, coerce_date_column, safe_number, get_series_by_letter
from app.charts import line_chart, area_chart, stacked_bar_chart
from app.layout import make_sidebar


st.set_page_config(page_title="Financial Dashboard", layout="wide")

GOOGLE_SHEET_URL_DEFAULT = (
	"https://docs.google.com/spreadsheets/d/1HM_Jxv6zQzr-O5Spt06uq2HTyX1yFTVju2jzVjneL5M/edit?gid=462380555"
)

# GID for the "주식현황" (Stock Status) sheet
STOCK_SHEET_GID = "172728277"


def _prepare(df: pd.DataFrame) -> pd.DataFrame:
	# Attempt common column conversions
	for col in df.columns:
		col_str = str(col)  # Convert column name to string
		if col_str.lower().find("date") >= 0 or col_str.endswith(("월", "날짜", "일", "시간")):
			df = coerce_date_column(df, col)
		else:
			try:
				if df[col].dtype == object:
					# Best-effort numeric conversion for money-like fields
					maybe_numeric = safe_number(df[col])
					# Only replace if we actually got numbers in many rows
					if pd.notna(maybe_numeric).sum() >= max(3, int(0.5 * len(maybe_numeric))):
						df[col] = maybe_numeric
			except Exception:
				continue
	
	# Additional date detection for columns that might contain dates
	for col in df.columns:
		try:
			if df[col].dtype == object and col not in [c for c in df.columns if str(df[c].dtype).startswith("datetime")]:
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
		except Exception:
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
	# Header with title and refresh button in right top
	col_title, col_refresh = st.columns([3, 1])
	with col_title:
		st.markdown("<h1 style='font-size: 2.5rem; margin-bottom: 0;'>Financial Status</h1>", unsafe_allow_html=True)
	with col_refresh:
		st.write("")  # Add some spacing
		if st.button("🔄 데이터 고침", type="primary", use_container_width=True):
			st.cache_data.clear()
			st.rerun()

	time_filter = make_sidebar()

	with st.spinner("데이터 불러오는 중..."):
		df = load_sheet(GOOGLE_SHEET_URL_DEFAULT)
		df = _prepare(df)
		
		# Load the second sheet "주식현황" if GID is provided
		df_stock = pd.DataFrame()
		if STOCK_SHEET_GID != "0":
			try:
				df_stock_raw = load_sheet(GOOGLE_SHEET_URL_DEFAULT, gid=STOCK_SHEET_GID, skiprows=0)
				
				# Get the columns starting from Q (index 16) to AA (index 26)
				if not df_stock_raw.empty and df_stock_raw.shape[1] > 26:
					# Extract Q-AA columns (indices 16-26) and keep them separate
					# First letter=0 (Q), then W=6, X=7, Y=8, Z=9, AA=10 in the extracted range
					df_stock = df_stock_raw.iloc[:, 16:27].copy()
					# Use numeric column names to avoid encoding issues
					df_stock.columns = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
					# Skip the first row which contains headers
					df_stock = df_stock.iloc[1:].reset_index(drop=True)
					
					# Store the extracted data - don't use _prepare as it may cause issues
					# Convert data types manually if needed
				else:
					df_stock = df_stock_raw
			except Exception as e:
				st.warning(f"주식현황 시트를 불러오지 못했습니다: {e}")

	if df.empty:
		st.warning("데이터가 비어 있습니다. 공유 설정 또는 URL을 확인하세요.")
		return

	# Apply time filter
	df_filtered = _apply_time_filter(df, time_filter)
	
	st.caption(f"행 {len(df_filtered)} · 열 {len(df_filtered.columns)} · 필터: {time_filter}")

	# Helper function to calculate month-over-month change
	def get_mom_change(series):
		"""Calculate month-over-month change and return formatted string with color coding"""
		if len(series.dropna()) < 2:
			return "0", "gray"
		
		current = series.dropna().iloc[-1]
		previous = series.dropna().iloc[-2]
		
		change = current - previous
		change_pct = (change / previous * 100) if previous != 0 else 0
		
		# Format change amount
		if abs(change) >= 1_000_000_000:  # 1B+
			change_str = f"{change/1_000_000_000:+.1f}B"
		elif abs(change) >= 1_000_000:  # 1M+
			change_str = f"{change/1_000_000:+.1f}M"
		elif abs(change) >= 1_000:  # 1K+
			change_str = f"{change/1_000:+.1f}K"
		else:
			change_str = f"{change:+.0f}"
		
		# Format percentage
		pct_str = f"{change_pct:+.1f}%"
		
		# Color coding
		if change > 0:
			color = "green"
		elif change < 0:
			color = "red"
		else:
			color = "gray"
		
		return f"[{change_str} {pct_str}]", color
	
	# Helper function to calculate period change (first to last value in filtered period)
	def get_period_change(series):
		"""Calculate change from first to last value in the filtered period"""
		series_clean = series.dropna()
		if len(series_clean) < 2:
			return None, None, "gray"
		
		first_value = series_clean.iloc[0]
		last_value = series_clean.iloc[-1]
		
		change = last_value - first_value
		change_pct = (change / first_value * 100) if first_value != 0 else 0
		
		# Format change amount
		if abs(change) >= 1_000_000_000:  # 1B+
			change_str = f"{change/1_000_000_000:+.1f}B"
		elif abs(change) >= 1_000_000:  # 1M+
			change_str = f"{change/1_000_000:+.1f}M"
		elif abs(change) >= 1_000:  # 1K+
			change_str = f"{change/1_000:+.1f}K"
		else:
			change_str = f"{change:+.0f}"
		
		# Format percentage
		pct_str = f"{change_pct:+.1f}%"
		
		# Color coding
		if change > 0:
			color = "green"
		elif change < 0:
			color = "red"
		else:
			color = "gray"
		
		return f"해당 기간 변동 금액({change_str})[{pct_str}]", color

	# Layout similar to screenshot: 2-column top grid then 3-column sections
	row1_col1 = st.container()
	with row1_col1:
		# Use 'AM' column for net worth
		date_col = next((c for c in df_filtered.columns if str(df_filtered[c].dtype).startswith("datetime")), df_filtered.columns[0])
		
		# Get numeric columns for fallback charts
		numeric_cols = [c for c in df_filtered.columns if pd.api.types.is_numeric_dtype(df_filtered[c])]
		
		# Split first row into two columns: 50% for assets, 50% for net worth
		top_col1, top_col2 = st.columns(2)
		
		with top_col1:
			# Assets total chart (AG column)
			try:
				assets_series = safe_number(get_series_by_letter(df_filtered, "AG"))
				df_assets = pd.DataFrame({date_col: df_filtered[date_col], "자산합계": assets_series})
				latest_assets = assets_series.dropna().iloc[-1] if not assets_series.dropna().empty else 0
				mom_change, change_color = get_mom_change(assets_series)
				title_with_value = f"자산합계 ({latest_assets:,.0f}) {mom_change}"
				st.markdown(f"<h3 style='color: {change_color}; font-size: 1.4rem; margin-bottom: 0.5rem;'>{title_with_value}</h3>", unsafe_allow_html=True)
				period_change, period_color = get_period_change(assets_series)
				if period_change:
					st.markdown(f"<p style='color: {period_color}; font-size: 0.9rem; margin-top: -0.5rem; margin-bottom: 0.5rem;'>{period_change}</p>", unsafe_allow_html=True)
				st.plotly_chart(line_chart(df_assets, date_col, ["자산합계"], ""), use_container_width=True)
			except Exception:
				st.caption("자산합계 데이터를 불러올 수 없습니다.")
		
		with top_col2:
			# Net worth chart (AM column)
			try:
				networth_series = safe_number(get_series_by_letter(df_filtered, "AM"))
				target_networth_series = safe_number(get_series_by_letter(df_filtered, "AN"))
				df_networth = pd.DataFrame({
					date_col: df_filtered[date_col],
					"순자산합계": networth_series,
					"목표 순자산": target_networth_series
				})
				latest_networth = networth_series.dropna().iloc[-1] if not networth_series.dropna().empty else 0
				mom_change, change_color = get_mom_change(networth_series)
				title_with_value = f"순자산합계 ({latest_networth:,.0f}) {mom_change}"
				st.markdown(f"<h3 style='color: {change_color}; font-size: 1.4rem; margin-bottom: 0.5rem;'>{title_with_value}</h3>", unsafe_allow_html=True)
				period_change, period_color = get_period_change(networth_series)
				if period_change:
					st.markdown(f"<p style='color: {period_color}; font-size: 0.9rem; margin-top: -0.5rem; margin-bottom: 0.5rem;'>{period_change}</p>", unsafe_allow_html=True)
				st.plotly_chart(
					line_chart(df_networth, date_col, ["순자산합계", "목표 순자산"], "", show_mom_change=True),
					use_container_width=True
				)
			except Exception:
				# Fallback: heuristic first numeric column
				if len(numeric_cols) >= 1:
					st.plotly_chart(line_chart(df_filtered, date_col, numeric_cols[:1], "순자산합계"), use_container_width=True)
		
		# Three asset charts side by side
		asset_col1, asset_col2, asset_col3 = st.columns(3)
		
		with asset_col1:
			# Stock total chart
			try:
				stock_series = safe_number(get_series_by_letter(df_filtered, "X"))
				df_stock_chart = pd.DataFrame({date_col: df_filtered[date_col], "주식합계": stock_series})
				latest_stock = stock_series.dropna().iloc[-1] if not stock_series.dropna().empty else 0
				mom_change, change_color = get_mom_change(stock_series)
				title_with_value = f"주식합계 ({latest_stock:,.0f}) {mom_change}"
				st.markdown(f"<h4 style='color: {change_color}; font-size: 1.2rem; margin-bottom: 0.3rem;'>{title_with_value}</h4>", unsafe_allow_html=True)
				period_change, period_color = get_period_change(stock_series)
				if period_change:
					st.markdown(f"<p style='color: {period_color}; font-size: 0.85rem; margin-top: -0.3rem; margin-bottom: 0.3rem;'>{period_change}</p>", unsafe_allow_html=True)
				st.plotly_chart(line_chart(df_stock_chart, date_col, ["주식합계"], "", height=200, show_mom_change=True), use_container_width=True)
			except Exception:
				st.caption("주식합계 데이터를 불러올 수 없습니다.")
		
		with asset_col2:
			# Pension asset total chart
			try:
				pension_series = safe_number(get_series_by_letter(df_filtered, "AC"))
				df_pension = pd.DataFrame({date_col: df_filtered[date_col], "연금자산합계": pension_series})
				latest_pension = pension_series.dropna().iloc[-1] if not pension_series.dropna().empty else 0
				mom_change, change_color = get_mom_change(pension_series)
				title_with_value = f"연금자산합계 ({latest_pension:,.0f}) {mom_change}"
				st.markdown(f"<h4 style='color: {change_color}; font-size: 1.2rem; margin-bottom: 0.3rem;'>{title_with_value}</h4>", unsafe_allow_html=True)
				period_change, period_color = get_period_change(pension_series)
				if period_change:
					st.markdown(f"<p style='color: {period_color}; font-size: 0.85rem; margin-top: -0.3rem; margin-bottom: 0.3rem;'>{period_change}</p>", unsafe_allow_html=True)
				st.plotly_chart(line_chart(df_pension, date_col, ["연금자산합계"], "", height=200), use_container_width=True)
			except Exception:
				st.caption("연금자산합계 데이터를 불러올 수 없습니다.")
		
		with asset_col3:
			# Real estate asset total chart
			try:
				realestate_series = safe_number(get_series_by_letter(df_filtered, "AF"))
				df_realestate = pd.DataFrame({date_col: df_filtered[date_col], "부동산자산합계": realestate_series})
				latest_realestate = realestate_series.dropna().iloc[-1] if not realestate_series.dropna().empty else 0
				mom_change, change_color = get_mom_change(realestate_series)
				title_with_value = f"부동산자산합계 ({latest_realestate:,.0f}) {mom_change}"
				st.markdown(f"<h4 style='color: {change_color}; font-size: 1.2rem; margin-bottom: 0.3rem;'>{title_with_value}</h4>", unsafe_allow_html=True)
				period_change, period_color = get_period_change(realestate_series)
				if period_change:
					st.markdown(f"<p style='color: {period_color}; font-size: 0.85rem; margin-top: -0.3rem; margin-bottom: 0.3rem;'>{period_change}</p>", unsafe_allow_html=True)
				st.plotly_chart(line_chart(df_realestate, date_col, ["부동산자산합계"], "", height=200), use_container_width=True)
			except Exception:
				st.caption("부동산자산합계 데이터를 불러올 수 없습니다.")
		
		# Third row: ISA/Pension, Toss Stocks, and Debt
		row3_col1, row3_col2, row3_col3 = st.columns(3)
		
		with row3_col1:
			# Combined ISA/Pension chart (Q and S columns)
			try:
				isa_q_series = safe_number(get_series_by_letter(df_filtered, "Q"))
				isa_s_series = safe_number(get_series_by_letter(df_filtered, "S"))
				
				df_isa = pd.DataFrame({
					date_col: df_filtered[date_col], 
					"연희 미래 ISA/연금": isa_q_series,
					"철규 미래 ISA": isa_s_series
				})
				
				# Calculate latest values and changes
				latest_isa_q = isa_q_series.dropna().iloc[-1] if not isa_q_series.dropna().empty else 0
				latest_isa_s = isa_s_series.dropna().iloc[-1] if not isa_s_series.dropna().empty else 0
				
				mom_change_q, change_color_q = get_mom_change(isa_q_series)
				mom_change_s, change_color_s = get_mom_change(isa_s_series)
				
				title_with_value = f"ISA"
				st.markdown(f"<h3 style='font-size: 1.4rem; margin-bottom: 0.5rem;'>{title_with_value}</h3>", unsafe_allow_html=True)
				
				# Display individual metrics
				col_q, col_s = st.columns(2)
				with col_q:
					st.markdown(f"<p style='color: {change_color_q}; font-size: 1.1rem; margin: 0;'>연희: {latest_isa_q:,.0f} {mom_change_q}</p>", unsafe_allow_html=True)
				with col_s:
					st.markdown(f"<p style='color: {change_color_s}; font-size: 1.1rem; margin: 0;'>철규: {latest_isa_s:,.0f} {mom_change_s}</p>", unsafe_allow_html=True)
				
				# Calculate period change for combined ISA
				isa_total_series = isa_q_series + isa_s_series
				period_change, period_color = get_period_change(isa_total_series)
				if period_change:
					st.markdown(f"<p style='color: {period_color}; font-size: 0.9rem; margin-top: 0.3rem; margin-bottom: 0.3rem;'>{period_change}</p>", unsafe_allow_html=True)
				
				st.plotly_chart(line_chart(df_isa, date_col, ["연희 미래 ISA/연금", "철규 미래 ISA"], "", height=200), use_container_width=True)
			except Exception:
				st.caption("ISA/연금 데이터를 불러올 수 없습니다.")
		
		with row3_col2:
			# Combined Toss Stocks chart (P and T columns)
			try:
				toss_p_series = safe_number(get_series_by_letter(df_filtered, "P"))
				toss_t_series = safe_number(get_series_by_letter(df_filtered, "T"))
				
				df_toss = pd.DataFrame({
					date_col: df_filtered[date_col], 
					"연희 토스 주식": toss_p_series,
					"철규 토스 주식": toss_t_series
				})
				
				# Calculate latest values and changes
				latest_toss_p = toss_p_series.dropna().iloc[-1] if not toss_p_series.dropna().empty else 0
				latest_toss_t = toss_t_series.dropna().iloc[-1] if not toss_t_series.dropna().empty else 0
				
				mom_change_p, change_color_p = get_mom_change(toss_p_series)
				mom_change_t, change_color_t = get_mom_change(toss_t_series)
				
				title_with_value = f"토스 주식"
				st.markdown(f"<h3 style='font-size: 1.4rem; margin-bottom: 0.5rem;'>{title_with_value}</h3>", unsafe_allow_html=True)
				
				# Display individual metrics
				col_p, col_t = st.columns(2)
				with col_p:
					st.markdown(f"<p style='color: {change_color_p}; font-size: 1.1rem; margin: 0;'>연희: {latest_toss_p:,.0f} {mom_change_p}</p>", unsafe_allow_html=True)
				with col_t:
					st.markdown(f"<p style='color: {change_color_t}; font-size: 1.1rem; margin: 0;'>철규: {latest_toss_t:,.0f} {mom_change_t}</p>", unsafe_allow_html=True)
				
				# Calculate period change for combined Toss Stocks
				toss_total_series = toss_p_series + toss_t_series
				period_change, period_color = get_period_change(toss_total_series)
				if period_change:
					st.markdown(f"<p style='color: {period_color}; font-size: 0.9rem; margin-top: 0.3rem; margin-bottom: 0.3rem;'>{period_change}</p>", unsafe_allow_html=True)
				
				st.plotly_chart(line_chart(df_toss, date_col, ["연희 토스 주식", "철규 토스 주식"], "", height=200), use_container_width=True)
			except Exception:
				st.caption("토스 주식 데이터를 불러올 수 없습니다.")
		
		with row3_col3:
			# Debt total chart
			try:
				debt_series = safe_number(get_series_by_letter(df_filtered, "AL"))
				df_debt = pd.DataFrame({date_col: df_filtered[date_col], "부채합계": debt_series})
				latest_debt = debt_series.dropna().iloc[-1] if not debt_series.dropna().empty else 0
				mom_change, change_color = get_mom_change(debt_series)
				title_with_value = f"부채합계 ({latest_debt:,.0f}) {mom_change}"
				st.markdown(f"<h3 style='color: {change_color}; font-size: 1.4rem; margin-bottom: 0.5rem;'>{title_with_value}</h3>", unsafe_allow_html=True)
				period_change, period_color = get_period_change(debt_series)
				if period_change:
					st.markdown(f"<p style='color: {period_color}; font-size: 0.9rem; margin-top: -0.5rem; margin-bottom: 0.5rem;'>{period_change}</p>", unsafe_allow_html=True)
				st.plotly_chart(line_chart(df_debt, date_col, ["부채합계"], "", height=200), use_container_width=True)
			except Exception:
				st.caption("부채합계 데이터를 불러올 수 없습니다.")
		
		# Stock Status chart from second sheet
		if not df_stock.empty:
			st.divider()
			st.markdown("### 📈 주식현황")
			
		try:
			# Build a robust date parser for stock sheet (handles "YY. M. D." and "MM/DD")
			# Infer year from main sheet if available
			main_year = None
			date_candidate = next((c for c in df_filtered.columns if str(df_filtered[c].dtype).startswith("datetime")), None)
			if date_candidate is not None and not df_filtered[date_candidate].dropna().empty:
				try:
					main_year = int(df_filtered[date_candidate].dropna().iloc[-1].year)
				except Exception:
					main_year = None
			if main_year is None:
				main_year = pd.Timestamp.today().year
			
			def _parse_stock_date(value):
				if pd.isna(value):
					return None
				text = str(value).strip()
				# Case 1: "25. 9. 9." -> YY. M. D.
				if "." in text:
					# remove dots and split on whitespace
					parts = [p for p in text.replace(".", " ").split() if p]
					if len(parts) >= 3:
						try:
							year = 2000 + int(parts[0])
							month = int(parts[1])
							day = int(parts[2])
							return f"{year:04d}/{month:01d}/{day:01d}"
						except Exception:
							return None
					elif len(parts) == 2:
						# YY M -> assume day 1
						try:
							year = 2000 + int(parts[0])
							month = int(parts[1])
							return f"{year:04d}/{month:01d}/1"
						except Exception:
							return None
					return None
				# Case 2: "M/D" or "MM/DD" -> use main_year
				if "/" in text:
					return f"{main_year}/{text}"
				return None

			date_with_year = df_stock[0].apply(_parse_stock_date)
			date_series = pd.to_datetime(date_with_year, format='%Y/%m/%d', errors='coerce')

			# Build dataframes and drop rows with NaT dates
			mask_valid = date_series.notna()
			df_amount = pd.DataFrame({
				"Date": date_series,
				"SPY": safe_number(df_stock[1]),
				"QQQ": safe_number(df_stock[2]),
				"SCHD": safe_number(df_stock[3]),
				"GLD": safe_number(df_stock[4]),
				"Cash/Bond": safe_number(df_stock[5])
			})[mask_valid]

			# Create two columns for side-by-side graphs
			col1, col2 = st.columns(2)

			with col1:
				st.markdown("#### 1. 실제 금액")
				st.plotly_chart(line_chart(df_amount, "Date", ["SPY", "QQQ", "SCHD", "GLD", "Cash/Bond"], "", height=300), use_container_width=True)

			df_pct = pd.DataFrame({
				"Date": date_series,
				"Cash/Bond": safe_number(df_stock[10]),
				"GLD": safe_number(df_stock[9]),
				"SCHD": safe_number(df_stock[8]),
				"QQQ": safe_number(df_stock[7]),
				"SPY": safe_number(df_stock[6])
			})[mask_valid]

			with col2:
				st.markdown("#### 2. 비율 (%)")
				st.plotly_chart(stacked_bar_chart(df_pct, "Date", ["Cash/Bond", "GLD", "SCHD", "QQQ", "SPY"], "", height=300), use_container_width=True)
		except Exception as e:
			st.error(f"주식현황 그래프를 불러올 수 없습니다: {e}")
			import traceback
			st.code(traceback.format_exc())

	# Google Sheets URL input at the bottom
	st.divider()
	url = st.text_input("Google Sheets URL", value=GOOGLE_SHEET_URL_DEFAULT)
	st.caption("URL을 변경하려면 위 입력창에 새로운 URL을 입력하고 Enter를 누르세요.")


if __name__ == "__main__":
	main()


