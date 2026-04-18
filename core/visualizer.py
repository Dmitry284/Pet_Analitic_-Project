import plotly.express as px


def create_chart(df, chart_type: str, x_col: str, y_col: str = None, color_col: str = None):
    if df.empty:
        return None

    try:
        if chart_type == "histogram":
            fig = px.histogram(df, x=x_col, color=color_col, title=f"Гистограмма: {x_col}")
        elif chart_type == "bar":
            fig = px.bar(df, x=x_col, y=y_col, color=color_col, title=f"Столбчатая: {x_col} vs {y_col}")
        elif chart_type == "line":
            fig = px.line(df, x=x_col, y=y_col, title=f"Линейный: {x_col} vs {y_col}")
        elif chart_type == "scatter":
            fig = px.scatter(df, x=x_col, y=y_col, color=color_col, title=f"Точечный: {x_col} vs {y_col}")
        elif chart_type == "box":
            fig = px.box(df, x=x_col, y=y_col, color=color_col, title=f"Boxplot: {x_col} vs {y_col}")
        else:
            raise ValueError(f"Неизвестный тип: {chart_type}")
        return fig
    except Exception as e:
        raise RuntimeError(f"Ошибка построения графика: {e}") from e