import time
from datetime import datetime

from airflow import DAG
from airflow.operators.python import PythonOperator
from notecoin.strategy.binance.strategy2 import Strategy2Task
from notecoin.task import AccountTask, MarketTask, Ticker24HTask


def refresh_markets():
    return MarketTask().refresh()


def refresh_data_24h():
    return Ticker24HTask().refresh()


def sell_auto():
    Strategy2Task().run_job()





with DAG("notecoin-binance-strategy", description="notecoin",
         default_args={"owner": "bingtao", "start_date": datetime(2022, 12, 15)},
         schedule_interval='*/5 * * * *',
         catchup=True) as dag:
    
    t2 = PythonOperator(dag=dag,
                        task_id='refresh-markets',
                        python_callable=refresh_markets,
                        op_args=[],
                        op_kwargs={},
                        depends_on_past=True,
                        wait_for_downstream=True)
    t3 = PythonOperator(dag=dag,
                        task_id='refresh-24h',
                        python_callable=refresh_data_24h,
                        op_args=[],
                        op_kwargs={},
                        depends_on_past=True,
                        wait_for_downstream=True)


with DAG("notecoin-binance-strategy-sell", description="notecoin",
         default_args={"owner": "bingtao", "start_date": datetime(2023, 12, 1)},
         schedule_interval='0 0 1 12 *',
         catchup=True) as dag:
    t5 = PythonOperator(dag=dag,
                        task_id='sell-auto',
                        python_callable=sell_auto,
                        op_args=[],
                        op_kwargs={},
                        depends_on_past=True,
                        wait_for_downstream=True)

