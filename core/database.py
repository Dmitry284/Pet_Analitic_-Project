import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError


def _validate_sql(sql: str) -> None:
    if not sql or not sql.strip():
        raise ValueError("SQL-запрос не может быть пустым.")

    sql_upper = sql.strip().upper()
    if not sql_upper.startswith("SELECT"):
        raise ValueError("Разрешены только SELECT-запросы.")

    forbidden = {"INSERT", "UPDATE", "DELETE", "DROP", "CREATE", "ALTER", "TRUNCATE"}
    for word in forbidden:
        if f" {word} " in sql_upper or sql_upper.startswith(word + " ") or sql_upper.endswith(" " + word):
            raise ValueError(f"Запрос содержит запрещённую команду: {word}")


def _prepare_sql(sql: str, max_rows: int = 5000) -> str:
    if "LIMIT" not in sql.upper():
        sql = f"{sql.rstrip(';')} LIMIT {max_rows}"
    return sql


def execute_query(conn_str: str, sql: str, max_rows: int = 5000) -> pd.DataFrame:
    _validate_sql(sql)
    safe_sql = _prepare_sql(sql, max_rows)

    engine = create_engine(conn_str)
    try:
        df = pd.read_sql(text(safe_sql), engine)
        return df
    except SQLAlchemyError as e:
        raise RuntimeError(f"Ошибка базы данных: {e}") from e
    except Exception as e:
        raise RuntimeError(f"Неизвестная ошибка: {e}") from e
    finally:
        engine.dispose()