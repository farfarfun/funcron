from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator
from ccxt import binance
from notecoin.coins.base.file import DataFileProperty

path_root = '/home/bingtao/workspace/tmp'


def parse_day(ds=None):
    ds = ds or '2022-09-01'
    first = datetime.strptime(ds, '%Y-%m-%d') - timedelta(days=1)
    last = first + timedelta(days=1) - timedelta(seconds=1)
    return first, last


def parse_week(ds=None):
    ds = ds or '2022-12-14'
    first = datetime.strptime(ds, '%Y-%m-%d')
    first = first - timedelta(days=first.weekday()) - timedelta(days=1)
    first = datetime(first.year, first.month, first.day)
    last = first + timedelta(weeks=1) - timedelta(seconds=1)
    return first, last


def load_kline(ds, *args, **kwargs):
    start, end = parse_day(ds)
    file_pro = DataFileProperty(exchange=binance(), path=path_root)
    file_pro.file_format = '%Y%m%d'
    file_pro.change_data_type('kline')
    file_pro.change_timeframe('1m')
    file_pro.change_freq('daily')
    file_pro.load_daily(start, end)


def load_trade(ds, *args, **kwargs):
    start, end = parse_day(ds)
    file_pro = DataFileProperty(exchange=binance(), path=path_root)
    file_pro.file_format = '%Y%m%d'
    file_pro.change_data_type('trade')
    file_pro.change_timeframe('detail')
    file_pro.change_freq('daily')
    file_pro.load_daily(start, end)


default_args = {"owner": "bingtao", "start_date": datetime(2022, 12, 1)}

dag = DAG("notecoin-binance-load-daily", description="notecoin",
          default_args=default_args, schedule_interval='0 8 * * *')

t1 = PythonOperator(dag=dag,
                    task_id='notecoin-binance-load-daily-kline',
                    #provide_context=False,
                    python_callable=load_kline,
                    op_args=[],
                    op_kwargs={'keyword_argument': 'which will be passed to function'},
                    depends_on_past=True,
                    wait_for_downstream=True)
