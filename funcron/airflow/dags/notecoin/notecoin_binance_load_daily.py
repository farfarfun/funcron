from datetime import datetime

from airflow import DAG
from airflow.operators.python import PythonOperator
from funcoin.task.load import LoadKlineDailyTask, LoadKlineWeeklyTask, LoadTradeDailyTask


def load_kline_daily(ds, *args, **kwargs):
    LoadKlineDailyTask().refresh(ds)


def load_kline_weekly(ds, *args, **kwargs):
    LoadKlineWeeklyTask().refresh(ds)


def load_trade(ds, *args, **kwargs):
    LoadTradeDailyTask().refresh(ds)


with DAG(
    "funcoin-binance-load-daily",
    description="funcoin",
    default_args={"owner": "bingtao", "start_date": datetime(2021, 9, 1)},
    schedule_interval="0 0 * * *",
) as dag:
    t1 = PythonOperator(
        dag=dag,
        task_id="funcoin-binance-load-daily-kline",
        # provide_context=False,
        python_callable=load_kline_daily,
        op_args=[],
        op_kwargs={"keyword_argument": "which will be passed to function"},
        depends_on_past=True,
        wait_for_downstream=True,
    )

with DAG(
    "funcoin-binance-load-weekly",
    description="funcoin",
    default_args={"owner": "bingtao", "start_date": datetime(2021, 9, 14)},
    schedule_interval="0 2 * * 3",
) as dag:
    t2 = PythonOperator(
        dag=dag,
        task_id="funcoin-binance-load-weekly-kline",
        # provide_context=False,
        python_callable=load_kline_weekly,
        op_args=[],
        op_kwargs={"keyword_argument": "which will be passed to function"},
        depends_on_past=True,
        wait_for_downstream=True,
    )
