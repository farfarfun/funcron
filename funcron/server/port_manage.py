import socket

import requests

# ps -ef | grep supervisord
# lsof -i:8000


def format_str(data: object, size: int) -> str:
    """把 `data` 转成字符串并用空格补齐到显示宽度 `size`（按中文字符占 2 个显示位计算）。

    参数:
        data: 任意可转成字符串的值。
        size: 期望的显示宽度（考虑中文字符宽度后的对齐宽度）。
    返回:
        补齐空格后的字符串。
    """
    data = str(data)
    len_txt = len(data)
    len_txt_utf8 = len(data.encode("utf-8"))
    data_size = int((len_txt_utf8 - len_txt) / 2 + len_txt)
    return str(data) + " " * (size - data_size)


class Port:
    """描述一个需要在 `funcron status` 中展示状态的服务端口。"""

    def __init__(self, name: str, port: int, desc: str = "") -> None:
        """
        参数:
            name: 服务名称，用于展示。
            port: 服务监听端口。
            desc: 服务描述，默认为空字符串。
        """
        self.name = name
        self.port = port
        self.desc = desc

    def check_port_in_use(self, host: str) -> str:
        """探测 `host:self.port` 是否可连通。

        参数:
            host: 目标主机地址。
        返回:
            端口可连通返回 "ON"，连接失败（含超时）返回 "OFF"。
        """
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(1)
                s.connect((host, int(self.port)))
                return "ON"
        except OSError:
            return "OFF"

    def __str__(self) -> str:
        return f"{self.name}"


class PortManage:
    """汇总本机常用服务端口，供 `funcron status` 命令展示可访问性状态。"""

    def __init__(self) -> None:
        self.host_inner = ""
        self.host_outer = ""
        self.port_list = [
            Port(name="Supervisor", port=8101, desc="Supervisor desc"),
            Port(name="funcron_webserver", port=8061, desc="funcron init webserver"),
            Port(name="funcron_flower", port=8062, desc="funcron init flower"),
            Port(name="funcron_scheduler", port=0, desc="funcron init scheduler"),
            Port(name="phpmyadmin", port=8051, desc="mysql数据管理"),
            Port(name="baota", port=31259, desc="宝塔"),
            Port(name="code-server", port=8443, desc="code-server"),
        ]
        self.get_host()

    def fprint(self) -> None:
        """把各服务端口的可访问状态打印为一个对齐的表格。

        这是 `funcron status` 命令面向终端用户的正常输出（CLI 展示结果），
        不是诊断日志，因此使用 `print` 而非 farlog。
        """
        print("#" * 100)
        for port in self.port_list:
            status = port.check_port_in_use(self.host_inner)
            url = f"http://{self.host_outer}:{port.port} "
            print(
                f"# {format_str(status, 6)}"
                f"{format_str(port.name, 20)} "
                f"{format_str(url, 30)} "
                f"{format_str(port.desc, 38)} "
                f"#"
            )
        print("#" * 100)

    def get_host(self) -> None:
        """探测本机内网出口 IP 和公网 IP，分别写入 `host_inner` / `host_outer`。"""
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            self.host_inner = s.getsockname()[0]

        self.host_outer = requests.get("http://ifconfig.me/ip", timeout=1).text.strip()
