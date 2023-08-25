cp airflow.cfg ~/airflow/airflow.cfg

airflow db init


#启动webserver
#后台运行  airflow webserver -p 8080 -D
airflow webserver -p 8080

#启动scheduler
#后台运行  airflow scheduler -D
airflow scheduler
#启动worker
#后台运行  airflow worker -D
#如提示addres already use ，则查看 worker_log_server_port = 8793 是否被占用，如是则修改为 8974 等
#未被占用的端口
airflow celery worker
#启动flower -- 可以不启动
#后台运行  airflow flower -D
airflow celery flower -p 8052