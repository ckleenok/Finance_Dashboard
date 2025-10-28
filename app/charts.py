from typing import List, Optional, Tuple

import pandas as pd
import plotly.graph_objects as go


def _add_trendline(fig: go.Figure, x, y, name: str = "Trend") -> None:
	if len(x) < 2:
		return
	# Simple linear regression via numpy polyfit to draw a dashed trend
	import numpy as np
	mask = pd.notna(y)
	if mask.sum() < 2:
		return
	coef = np.polyfit(pd.to_numeric(pd.Series(x)[mask].rank()), y[mask], 1)
	x_idx = pd.Series(x).rank()
	trend = coef[0] * x_idx + coef[1]
	fig.add_trace(
		go.Scatter(
			x=x,
			y=trend,
			mode="lines",
			name=name,
			line=dict(color="#888", dash="dash"),
			showlegend=False,
		)
	)


def line_chart(df: pd.DataFrame, x_col: str, y_cols: List[str], title: str, height: int = 250) -> go.Figure:
	fig = go.Figure()
	for col in y_cols:
		if col not in df.columns:
			continue
		fig.add_trace(
			go.Scatter(
				x=df[x_col],
				y=df[col],
				mode="lines+markers",
				name=col,
				hovertemplate="<b>%{x}</b><br>" +
							f"<b>{col}:</b> %{{y:,.0f}}<br>" +
							"<extra></extra>"
			)
		)
	# Trendline removed - no longer adding trendlines to charts
	# first = y_cols[0] if y_cols else None
	# if first and first in df.columns:
	# 	_add_trendline(fig, df[x_col], df[first])
	
	# Set x-axis range to match filtered data
	if not df.empty and x_col in df.columns:
		x_min = df[x_col].min()
		x_max = df[x_col].max()
		fig.update_xaxes(range=[x_min, x_max])
	
	# Format y-axis to show B, M, K units with custom formatting
	fig.update_yaxes(
		tickformat=".0f",
		tickprefix="",
		ticksuffix="",
		separatethousands=True
	)
	
	# Custom Y-axis labels for better readability
	if not df.empty and y_cols:
		# Get the range of values to determine appropriate tick values
		all_values = []
		for col in y_cols:
			if col in df.columns:
				all_values.extend(df[col].dropna().tolist())
		
		if all_values:
			max_val = max(all_values)
			min_val = min(all_values)
			range_val = max_val - min_val
			
			if max_val >= 1_000_000_000:  # 1B+
				# Create more tick points for better readability
				tick_count = 6
				tick_vals = []
				tick_texts = []
				for i in range(tick_count):
					val = min_val + (range_val * i / (tick_count - 1))
					tick_vals.append(val)
					tick_texts.append(f"{val/1_000_000_000:.1f}B")
				
				fig.update_yaxes(
					tickvals=tick_vals,
					ticktext=tick_texts,
					nticks=tick_count
				)
			elif max_val >= 1_000_000:  # 1M+
				tick_count = 6
				tick_vals = []
				tick_texts = []
				for i in range(tick_count):
					val = min_val + (range_val * i / (tick_count - 1))
					tick_vals.append(val)
					tick_texts.append(f"{val/1_000_000:.1f}M")
				
				fig.update_yaxes(
					tickvals=tick_vals,
					ticktext=tick_texts,
					nticks=tick_count
				)
			elif max_val >= 1_000:  # 1K+
				tick_count = 6
				tick_vals = []
				tick_texts = []
				for i in range(tick_count):
					val = min_val + (range_val * i / (tick_count - 1))
					tick_vals.append(val)
					tick_texts.append(f"{val/1_000:.1f}K")
				
				fig.update_yaxes(
					tickvals=tick_vals,
					ticktext=tick_texts,
					nticks=tick_count
				)
	
	# Position legend at bottom
	fig.update_layout(
		margin=dict(l=2, r=2, t=20, b=50), 
		title=title, 
		height=height,
		legend=dict(
			orientation="h",
			yanchor="top",
			y=-0.25,
			xanchor="center",
			x=0.5
		)
	)
	return fig


def area_chart(df: pd.DataFrame, x_col: str, y_col: str, title: str) -> go.Figure:
	fig = go.Figure(
		data=[
			go.Scatter(
				x=df[x_col],
				y=df[y_col],
				mode="lines",
				fill="tozeroy",
				name=y_col,
				hovertemplate="<b>%{x}</b><br>" +
							f"<b>{y_col}:</b> %{{y:,.0f}}<br>" +
							"<extra></extra>"
			)
		]
	)
	
	# Set x-axis range to match filtered data
	if not df.empty and x_col in df.columns:
		x_min = df[x_col].min()
		x_max = df[x_col].max()
		fig.update_xaxes(range=[x_min, x_max])
	
	# Format y-axis to show B, M, K units with custom formatting
	fig.update_yaxes(
		tickformat=".0f",
		tickprefix="",
		ticksuffix="",
		separatethousands=True
	)
	
	# Custom Y-axis labels for better readability
	if not df.empty:
		all_values = df[y_col].dropna().tolist()
		if all_values:
			max_val = max(all_values)
			min_val = min(all_values)
			range_val = max_val - min_val
			
			if max_val >= 1_000_000_000:  # 1B+
				tick_count = 6
				tick_vals = []
				tick_texts = []
				for i in range(tick_count):
					val = min_val + (range_val * i / (tick_count - 1))
					tick_vals.append(val)
					tick_texts.append(f"{val/1_000_000_000:.1f}B")
				
				fig.update_yaxes(
					tickvals=tick_vals,
					ticktext=tick_texts,
					nticks=tick_count
				)
			elif max_val >= 1_000_000:  # 1M+
				tick_count = 6
				tick_vals = []
				tick_texts = []
				for i in range(tick_count):
					val = min_val + (range_val * i / (tick_count - 1))
					tick_vals.append(val)
					tick_texts.append(f"{val/1_000_000:.1f}M")
				
				fig.update_yaxes(
					tickvals=tick_vals,
					ticktext=tick_texts,
					nticks=tick_count
				)
			elif max_val >= 1_000:  # 1K+
				tick_count = 6
				tick_vals = []
				tick_texts = []
				for i in range(tick_count):
					val = min_val + (range_val * i / (tick_count - 1))
					tick_vals.append(val)
					tick_texts.append(f"{val/1_000:.1f}K")
				
				fig.update_yaxes(
					tickvals=tick_vals,
					ticktext=tick_texts,
					nticks=tick_count
				)
	
	fig.update_layout(margin=dict(l=2, r=2, t=20, b=10), title=title, height=180)
	return fig


def stacked_bar_chart(df: pd.DataFrame, x_col: str, y_cols: List[str], title: str = "", height: int = 250) -> go.Figure:
	"""Create a horizontal stacked bar chart from a DataFrame."""
	fig = go.Figure()
	
	# Normalize each row to 100%
	df_normalized = df.copy()
	df_normalized['_total'] = df_normalized[y_cols].sum(axis=1)
	# Avoid division by zero
	df_normalized['_total'] = df_normalized['_total'].replace(0, 1)

	# Build one-line date strings and lock category order
	if pd.api.types.is_datetime64_any_dtype(df_normalized[x_col]):
		date_str = df_normalized[x_col].dt.strftime('%b %d')
		# If year changes within data, append year where it changes
		years = df_normalized[x_col].dt.year.fillna(method='ffill')
		if years.nunique() > 1:
			date_str = df_normalized[x_col].dt.strftime('%b %d %Y')
	else:
		date_str = df_normalized[x_col].astype(str)

	for col in y_cols:
		if col not in df_normalized.columns:
			continue
		# Normalize to percentage of total
		df_normalized[col] = (df_normalized[col] / df_normalized['_total']) * 100
	
	# Add traces for each column
	for col in y_cols:
		if col not in df_normalized.columns:
			continue
		fig.add_trace(
			go.Bar(
				name=col,
				orientation='h',
				y=date_str,
				x=df_normalized[col],
				hovertemplate=f"<b>%{{y}}</b><br><b>{col}:</b> %{{x:.2f}}%<extra></extra>",
				text=df_normalized[col].apply(lambda x: f"{x:.2f}%" if pd.notna(x) else ""),
				textposition='inside'
			)
		)
	
	# Update layout
	fig.update_layout(
		barmode='stack',
		margin=dict(l=100, r=20, t=40, b=30),
		title=title,
		height=height,
		xaxis=dict(
			title="Percentage (%)",
			range=[0, 100],
			ticksuffix="%"
		),
		yaxis=dict(title="", type='category', categoryorder='array', categoryarray=date_str.tolist()),
		legend=dict(
			orientation="h",
			yanchor="bottom",
			y=1.02,
			xanchor="center",
			x=0.5
		)
	)
	
	return fig

