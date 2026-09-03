"""创建 Airflow 管理员账号的一次性脚本。

账号信息一律通过 funsecret 下发，不在代码中硬编码用户名/邮箱/密码；
未在密钥库中配置时会直接报错退出，而不是回落到任何默认账号密码。

用法：`python -m funcron.airflow.create_account`
（等价于 `airflow users create --role Admin ...` 命令行方式）
"""

from airflow import models, settings
from airflow.contrib.auth.backends.password_auth import PasswordUser
from funsecret import read_secret


def main() -> None:
    username = read_secret(cate1="funcron", cate2="airflow", cate3="admin", cate4="username", value="")
    email = read_secret(cate1="funcron", cate2="airflow", cate3="admin", cate4="email", value="")
    password = read_secret(cate1="funcron", cate2="airflow", cate3="admin", cate4="password", value="")
    if not (username and email and password):
        raise RuntimeError(
            "缺少 Airflow 管理员账号配置，请先通过 funsecret 写入 "
            "funcron/airflow/admin 下的 username/email/password"
        )

    user = PasswordUser(models.User())
    user.username = username
    user.email = email
    user.password = password
    user.superuser = True  # 赋予管理员权限，如果是普通用户就不需要这个

    session = settings.Session()
    try:
        session.add(user)
        session.commit()
    finally:
        session.close()


if __name__ == "__main__":
    main()