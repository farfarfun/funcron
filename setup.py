from funpypi import setup


install_requires = [
    "supervisor",
    "apscheduler",
    "gunicorn",
    "records",
    "gevent",
    "redi",
    "apache-airflow",
    "apache-airflow-providers-celery",
]


setup(
    name="funcron",
    install_requires=install_requires,
    entry_points={"console_scripts": ["funcron = funcron.server.script:funcron"]},
)
