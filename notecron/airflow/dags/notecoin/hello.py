"""
Airflow的第一个DAG
"""
from datetime import datetime

from airflow import DAG
from airflow.operators.bash_operator import BashOperator

default_args = {
    "owner": "bingtao",
    "start_date": datetime(2022, 1, 1)
}

with DAG("Hello-World2",
          description="第一个DAG",
          default_args=default_args,
          schedule_interval='0 0 * * *',
          catchup=True) as dag:
    t1 = BashOperator(task_id="hello", bash_command="echo 'Hello World, today is {{ ds }}'", dag=dag)
