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


def line_chart(df: pd.DataFrame, x_col: str, y_cols: List[str], title: str, height: int = 280) -> go.Figure:
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
			)
		)
	# Trendline removed - no longer adding trendlines to charts
	# first = y_cols[0] if y_cols else None
	# if first and first in df.columns:
	# 	_add_trendline(fig, df[x_col], df[first])
	fig.update_layout(margin=dict(l=10, r=10, t=40, b=10), title=title, height=height)
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
			)
		]
	)
	fig.update_layout(margin=dict(l=10, r=10, t=40, b=10), title=title, height=200)
	return fig


