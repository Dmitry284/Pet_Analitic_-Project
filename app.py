# app.py
import streamlit as st
import pandas as pd
import numpy as np
from core.ab_test import run_ab_test
from core.database import execute_query
from core.analyzer import analyze_dataframe
from core.visualizer import create_chart

st.set_page_config(page_title="SQL & CSV Analyzer", layout="wide")
st.title("SQL & CSV Data Analyzer")

if "df" not in st.session_state:
    st.session_state.df = None

# 1. Выбор источника
source = st.radio("Источник данных", ["PostgreSQL", "CSV-файл"], horizontal=True, key="source_selector")

if source == "PostgreSQL":
    st.sidebar.header("Подключение к БД")
    conn_str = st.sidebar.text_input("PostgreSQL URL", value="postgresql://dima:****@localhost:5432/study", type="password")
    query = st.text_area("SQL-запрос", height=80, value="SELECT version();")
    if st.button("Выполнить запрос", type="primary", key="run_query"):
        if "postgresql://" not in conn_str:
            st.error("Укажите корректную строку подключения")
        else:
            try:
                with st.spinner("Подключение и выполнение..."):
                    st.session_state.df = execute_query(conn_str, query)
            except Exception as e:
                st.error(f"Ошибка БД: {e}")
else:
    uploaded_file = st.file_uploader("Вставьте CSV файл", type=["csv"])
    if uploaded_file:
        with st.spinner("Чтение файла..."):
            st.session_state.df = pd.read_csv(uploaded_file)

# 2. Настройки отображения
st.sidebar.divider()
st.sidebar.header("Отображение")
display_limit = st.sidebar.selectbox("Показать строк в таблице", [10, 25, 50, 100, 250, 500], index=2)

# 3. Настройки метрик
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

# 4. Основная область
df = st.session_state.df
if df is not None and not df.empty:
    st.success(f"Загружено: {len(df)} строк, {len(df.columns)} столбцов")
    st.dataframe(df.head(display_limit), use_container_width=True, height=300)

    # === ВКЛАДКИ ===
    tab_main, tab_ab = st.tabs(["Основной анализ", "A/B Тесты"])

    # ▼▼▼ ВКЛАДКА 1: Основной анализ ▼▼▼
    with tab_main:
        analysis = analyze_dataframe(df, metrics_cfg)

        if metrics_cfg.get("shape"):
            c1, c2 = st.columns(2)
            c1.metric("Строк", analysis["shape"][0])
            c2.metric("Столбцов", analysis["shape"][1])

        if metrics_cfg.get("missing"):
            st.markdown("### Пропуски (NaN)")
            missing_df = pd.DataFrame({
                "Столбец": df.columns,
                "Пропуски": [analysis["missing"].get(c, 0) for c in df.columns],
                "%": [analysis["missing_pct"].get(c, 0.0) for c in df.columns]
            })
            st.dataframe(missing_df[missing_df["Пропуски"] > 0], use_container_width=True, hide_index=True)

        if metrics_cfg.get("unique"):
            st.markdown("### Уникальные значения")
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
                st.dataframe(stats_df[["25%", "75%"]].rename(columns={"25%": "25%", "75%": "75%"}), use_container_width=True)

            if metrics_cfg.get("min_max"):
                st.markdown("### Минимум / Максимум")
                st.dataframe(stats_df[["min", "max"]].rename(columns={"min": "Min", "max": "Max"}), use_container_width=True)

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
                st.dataframe(pd.DataFrame(counts.items(), columns=["Значение", "Частота"]), use_container_width=True, height=100)

        # Визуализация
        st.divider()
        st.subheader("Визуализация")
        chart_type = st.selectbox("Тип графика", ["histogram", "bar", "line", "scatter", "box"], key="chart_main")
        x_col = st.selectbox("Ось X", df.columns.tolist(), key="x_main")
        y_col = st.selectbox("Ось Y (опц.)", [None] + df.columns.tolist(), key="y_main")
        color_col = st.selectbox("Цвет/Группировка (опц.)", [None] + df.columns.tolist(), key="color_main")

        if st.button("Построить", key="build_chart_main"):
            with st.spinner("Генерация..."):
                fig = create_chart(df, chart_type, x_col, y_col, color_col)
                if fig:
                    st.plotly_chart(fig, use_container_width=True)

    # ▼▼▼ ВКЛАДКА 2: A/B Тесты ▼▼▼
    with tab_ab:
        st.header("A/B Тестирование")
        st.info(
            "Выберите столбец для разделения на группы (должен содержать ровно 2 уникальных значения) и числовую метрику для сравнения.")

        num_cols = df.select_dtypes(include=[np.number]).columns.tolist()

        # Находим колонки, подходящие для группировки (ровно 2 уникальных значения)
        valid_group_cols = [col for col in df.columns if df[col].nunique() == 2]

        if len(valid_group_cols) == 0:
            st.warning(
                "В данных нет столбцов с ровно 2 уникальными значениями. Для A/B теста нужен столбец-разделитель групп (например, 'group': ['A', 'B']).")
            st.caption(
                "Подсказка: создайте такой столбец в запросе: SELECT *, CASE WHEN condition THEN 'A' ELSE 'B' END as group FROM table")
        elif len(num_cols) == 0:
            st.warning("Для A/B теста нужен хотя бы один числовой столбец-метрика.")
        else:
            group_col = st.selectbox("Столбец группировки (2 значения)", valid_group_cols, key="ab_group")
            metric_col = st.selectbox("Метрика для сравнения (числовая)", num_cols, key="ab_metric")

            # Показываем, какие именно значения в группах
            group_values = df[group_col].unique().tolist()
            st.caption(f"Значения в '{group_col}': {group_values[0]} и {group_values[1]}")

            if st.button("Запустить тест", type="primary", key="run_ab"):
                try:
                    with st.spinner("Вычисление статистики..."):
                        result = run_ab_test(df, group_col, metric_col)

                    st.success(result["conclusion"])

                    c1, c2, c3, c4 = st.columns(4)
                    c1.metric(f"Среднее ({result['group_a']})", f"{result['mean_a']:.3f}")
                    c2.metric(f"Среднее ({result['group_b']})", f"{result['mean_b']:.3f}")
                    c3.metric("Разница (Delta)", f"{result['diff']:+.3f}")
                    c4.metric("Эффект (Cohen's d)", f"{result['cohens_d']:.3f}")

                    st.dataframe(pd.DataFrame(result["sample_sizes"], index=["Размер выборки"]).T,
                                 use_container_width=True)

                    st.markdown("### Расшифровка")
                    st.write(f"**Тест:** {result['test_name']}")
                    st.write(
                        f"**p-value:** `{result['p_value']:.4f}` {'< 0.05 (значимо)' if result['significant'] else '>= 0.05 (не значимо)'}")
                    direction = f"{result['group_b']} > {result['group_a']}" if result[
                                                                                    'diff'] > 0 else f"{result['group_a']} > {result['group_b']}" if \
                    result['diff'] < 0 else "Равны"
                    st.write(f"**Направление:** {direction} ({result['relative_diff']:+.1f}%)")

                    with st.expander("Проверка предпосылок"):
                        st.info(
                            f"Нормальность: {'Да' if result['assumptions']['is_normal'] else 'Нет'} | Равенство дисперсий: {'Да' if result['assumptions']['equal_var'] else 'Нет'}")
                        st.caption("Автоматический выбор теста основан на проверках Шапиро-Уилка и Левена.")

                except Exception as e:
                    st.error(f"Ошибка: {e}")
                    
elif df is not None and df.empty:
    st.warning("Запрос вернул пустой результат.")
else:
    st.info("Выберите источник и загрузите данные.")