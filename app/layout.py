import streamlit as st


def make_filter_section() -> str:
	"""메인 컨텐츠 영역에 필터 섹션을 생성합니다."""
	st.markdown("### 📊 데이터 필터")
	# Time period filter with proper functionality
	time_filter = st.selectbox(
		"발췌 연도, 월", 
		options=[
			"최근 3개월",
			"최근 6개월", 
			"최근 9개월",
			"최근 12개월",
			"최근 18개월",
			"최근 24개월",
			"모든 데이터"
		], 
		index=6  # Default to "모든 데이터"
	)
	return time_filter


def container(title: str):
	return st.container(border=True).expander(title, expanded=True) if False else st.container(border=True)


