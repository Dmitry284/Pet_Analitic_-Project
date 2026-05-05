import pandas as pd
import numpy as np
from scipy import stats
from typing import Dict


def run_ab_test(df: pd.DataFrame, group_col: str, metric_col: str) -> Dict:
    """
    Запускает A/B тест для двух групп по выбранной числовой метрике.
    Автоматически выбирает тип теста на основе проверки предпосылок.
    """
    if group_col not in df.columns or metric_col not in df.columns:
        raise ValueError("Указанные столбцы отсутствуют в данных")

    # Удаляем пропуски только для выбранных колонок
    clean = df[[group_col, metric_col]].dropna()
    groups = clean.groupby(group_col)[metric_col].apply(list)

    if len(groups) != 2:
        raise ValueError("A/B тест требует ровно 2 уникальные группы в выбранном столбце")

    group_names = list(groups.index)
    data_a = np.array(groups.iloc[0])
    data_b = np.array(groups.iloc[1])

    if len(data_a) < 2 or len(data_b) < 2:
        raise ValueError("В каждой группе должно быть минимум 2 наблюдения")

    # 1. Проверка предпосылок (для автоматического выбора теста)
    # Шапиро-Уилк ограничен 5000 элементами, поэтому берём сэмпл
    _, p_norm_a = stats.shapiro(data_a[:5000])
    _, p_norm_b = stats.shapiro(data_b[:5000])
    is_normal = p_norm_a > 0.05 and p_norm_b > 0.05

    _, p_var = stats.levene(data_a, data_b)
    equal_var = p_var > 0.05

    # 2. Выбор и запуск теста
    if is_normal and equal_var:
        stat, p_value = stats.ttest_ind(data_a, data_b, equal_var=True)
        test_name = "Двухвыборочный t-тест (равные дисперсии)"
    elif is_normal:
        stat, p_value = stats.ttest_ind(data_a, data_b, equal_var=False)
        test_name = "t-тест Уэлча (неравные дисперсии)"
    else:
        stat, p_value = stats.mannwhitneyu(data_a, data_b, alternative="two-sided")
        test_name = "U-критерий Манна-Уитни (непараметрический)"

    # 3. Расчёт метрик
    mean_a, mean_b = float(np.mean(data_a)), float(np.mean(data_b))
    diff = mean_b - mean_a
    relative_diff = (diff / mean_a * 100) if mean_a != 0 else 0.0

    # Размер эффекта (Cohen's d)
    n_a, n_b = len(data_a), len(data_b)
    std_a, std_b = float(np.std(data_a, ddof=1)), float(np.std(data_b, ddof=1))
    pooled_std = np.sqrt(((n_a - 1) * std_a ** 2 + (n_b - 1) * std_b ** 2) / (n_a + n_b - 2))
    cohens_d = float(diff / pooled_std) if pooled_std > 0 else 0.0

    effect_label = "Малый" if abs(cohens_d) < 0.2 else ("Средний" if abs(cohens_d) < 0.8 else "Большой")
    significant = p_value < 0.05

    conclusion = (f"Различия {'статистически значимы' if significant else 'не значимы'} "
                  f"(p={p_value:.4f}). Эффект: {effect_label} (d={cohens_d:.3f})")

    return {
        "test_name": test_name,
        "group_a": str(group_names[0]), "group_b": str(group_names[1]),
        "mean_a": mean_a, "mean_b": mean_b,
        "diff": diff, "relative_diff": relative_diff,
        "p_value": float(p_value), "statistic": float(stat),
        "cohens_d": cohens_d, "effect_size": effect_label,
        "significant": significant,
        "conclusion": conclusion,
        "sample_sizes": {"n_a": n_a, "n_b": n_b},
        "assumptions": {"normality_check": "Шапиро-Уилк", "variance_check": "Левен",
                        "is_normal": is_normal, "equal_var": equal_var}
    }