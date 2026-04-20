import streamlit as st
import pandas as pd
from core.database import execute_query
from core.analyzer import analyze_dataframe
from core.visualizer import create_chart

st.set_page_config(page_title="SQL & CSV Analyzer", layout="wide")
st.title("SQL & CSV Data Analyzer")

if "df" not in st.session_state:
    st.session_state.df = None


source = st.radio("Источник данных", ["PostgreSQL", "CSV-файл"], horizontal=True, key="source_selector")

if source == "PostgreSQL":
    st.sidebar.header("Подключение к БД")
    conn_str = st.sidebar.text_input("PostgreSQL URL", value="postgresql://dima:****@localhost:5432/study",
                                     type="password")
    query = st.text_area("SQL-запрос", height=80, value="SELECT version();")
    if st.button("Выполнить запрос", type="primary", key="run_query"):
        if "postgresql://" not in conn_str:
            st.error("Укажите корректную строку подключения")
        else:
            try:
                with st.spinner("Подключение и выполнение"):
                    st.session_state.df = execute_query(conn_str, query)
            except Exception as e:
                st.error(f"Ошибка БД: {e}")
else:
    uploaded_file = st.file_uploader("Вставьте CSV файл", type=["csv"])
    if uploaded_file:
        with st.spinner("Чтение файла"):
            st.session_state.df = pd.read_csv(uploaded_file)


st.sidebar.divider()
st.sidebar.header("Отображение")
display_limit = st.sidebar.selectbox("Показать строк в таблице", [10, 25, 50, 100, 250, 500], index=2)

st.sidebar.divider()
st.sidebar.header("Метрики анализа")
metrics_cfg = {}

with st.sidebar.expander("Основные"):
    metrics_cfg["shape"] = st.checkbox("Размерность", value=True)
    metrics_cfg["missing"] = st.checkbox("Пропуски (абс. + %)", value=True)
    metrics_cfg["unique"] = st.checkbox("Уникальные значения", value=False)

with st.sidebar.expander("Числовые метрики"):
    metrics_cfg["mean"] = st.checkbox("Среднее", value=True)
    metrics_cfg["median"] = st.checkbox("Медиана (50%)", value=True)
    metrics_cfg["std"] = st.checkbox("Станд. отклонение", value=True)
    metrics_cfg["quantiles"] = st.checkbox("Квантили (25/75)", value=True)
    metrics_cfg["min_max"] = st.checkbox("Min / Max", value=True)
    metrics_cfg["skew_kurt_iqr"] = st.checkbox("Skew / Kurt / IQR / Mode", value=False)

with st.sidebar.expander("Категориальные метрики"):
    metrics_cfg["top_values"] = st.checkbox("Топ-5 частот", value=True)

df = st.session_state.df
if df is not None and not df.empty:
    st.success(f"Загружено: {len(df)} строк, {len(df.columns)} столбцов")
    st.dataframe(df.head(display_limit), use_container_width=True, height=300)

    analysis = analyze_dataframe(df, metrics_cfg)


    if metrics_cfg.get("shape"):
        c1, c2 = st.columns(2)
        c1.metric("Строк", analysis["shape"][0])
        c2.metric("Столбцов", analysis["shape"][1])

    if metrics_cfg.get("missing"):
        st.markdown("Пропуски (NaN)")
        missing_df = pd.DataFrame({
            "Столбец": df.columns,
            "Пропуски": [analysis["missing"].get(c, 0) for c in df.columns],
            "%": [analysis["missing_pct"].get(c, 0.0) for c in df.columns]
        })
        st.dataframe(missing_df[missing_df["Пропуски"] > 0], use_container_width=True, hide_index=True)

    if metrics_cfg.get("unique"):
        st.markdown("Уникальные значения")
        st.dataframe(pd.DataFrame(analysis["unique"], index=["Уникальных"]).T, use_container_width=True, height=120)

    if analysis.get("numeric_stats"):
        stats_df = pd.DataFrame(analysis["numeric_stats"]).T

        if metrics_cfg.get("mean"):
            st.markdown("### Среднее значение")
            st.dataframe(stats_df[["mean"]].rename(columns={"mean": "Среднее"}), use_container_width=True)

        if metrics_cfg.get("median"):
            st.markdown("### Медиана")
            st.dataframe(stats_df[["50%"]].rename(columns={"50%": "Медиана"}), use_container_width=True)

        if metrics_cfg.get("std"):
            st.markdown("### Стандартное отклонение")
            st.dataframe(stats_df[["std"]].rename(columns={"std": "Std Dev"}), use_container_width=True)

        if metrics_cfg.get("quantiles"):
            st.markdown("### Квантили (25% и 75%)")
            st.dataframe(stats_df[["25%", "75%"]].rename(columns={"25%": "25%", "75%": "75%"}),
                         use_container_width=True)

        if metrics_cfg.get("min_max"):
            st.markdown("### Минимум / Максимум")
            st.dataframe(stats_df[["min", "max"]].rename(columns={"min": "Min", "max": "Max"}),
                         use_container_width=True)

    if metrics_cfg.get("skew_kurt_iqr") and analysis.get("skew"):
        st.markdown("### Продвинутая статистика")

        st.markdown("**Асимметрия (Skewness):**")
        st.dataframe(pd.Series(analysis["skew"], name="Skew").to_frame().T, use_container_width=True)

        st.markdown("**Эксцесс (Kurtosis):**")
        st.dataframe(pd.Series(analysis["kurtosis"], name="Kurt").to_frame().T, use_container_width=True)

        st.markdown("**Межквартильный размах (IQR):**")
        st.dataframe(pd.Series(analysis["iqr"], name="IQR").to_frame().T, use_container_width=True)

        st.markdown("**Мода (Mode):**")
        st.dataframe(pd.Series(analysis["mode"], name="Mode").to_frame().T, use_container_width=True)

    if analysis.get("categorical_top") and metrics_cfg.get("top_values"):
        st.markdown("### Топ категорий")
        for col, counts in list(analysis["categorical_top"].items())[:5]:
            st.write(f"`{col}`:")
            st.dataframe(pd.DataFrame(counts.items(), columns=["Значение", "Частота"]), use_container_width=True,
                         height=100)

    # Визуализация
    st.divider()
    st.subheader(" Визуализация")
    chart_type = st.selectbox("Тип графика", ["histogram", "bar", "line", "scatter", "box"])
    x_col = st.selectbox("Ось X", df.columns.tolist())
    y_col = st.selectbox("Ось Y (опц.)", [None] + df.columns.tolist())
    color_col = st.selectbox("Цвет/Группировка (опц.)", [None] + df.columns.tolist())

    if st.button("Построить", key="build_chart"):
        with st.spinner("Генерация..."):
            fig = create_chart(df, chart_type, x_col, y_col, color_col)
            if fig:
                st.plotly_chart(fig, use_container_width=True)

elif df is not None and df.empty:
    st.warning("Запрос вернул пустой результат.")
else:
    st.info("Выберите источник и загрузите данные.")