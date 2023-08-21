import airflow
from airflow import models, settings
from airflow.contrib.auth.backends.password_auth import PasswordUser

python


user = PasswordUser(models.User())
user.username = 'bingtao'
user.email = '1007530194@qq.com'
user.password = '15068733021'
user.superuser = 1 # 赋予管理员权限，如果是普通用户就不需要这个

session = settings.Session()
session.add(user)
session.commit()
session.close()
exit()
#airflow users create --role Admin --username bingtao --email 1007530194@qq.com --firstname bing --lastname tao --password 15068733021