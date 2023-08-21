import time
from setuptools import find_packages, setup


install_requires = ["apscheduler", "gunicorn", "records", "gevent"]


setup(
    name="funcron",
    version=time.strftime("%Y%m%d%H%M", time.localtime()),
    description="funcron",
    author="bingtao",
    author_email="1007530194@qq.com",
    url="https://github.com/1007530194",
    packages=find_packages(),
    package_data={"": ["*.js", "*.*"]},
    # include_package_data=True,
    install_requires=install_requires,
    entry_points={"console_scripts": ["funcron = funcron.server.script:funcron"]},
)
