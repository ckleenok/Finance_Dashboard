import streamlit as st


def make_sidebar() -> None:
	st.sidebar.header("필터")
	# Placeholder filters; real filters can be wired to data columns later
	st.sidebar.selectbox("발췌 연도, 월", options=["(전체)", "최근 12개월", "최근 24개월"], index=0)


def container(title: str):
	return st.container(border=True).expander(title, expanded=True) if False else st.container(border=True)


