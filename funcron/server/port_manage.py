import socket

import requests

# ps -ef | grep supervisord
# lsof -i:8000


def format_str(data, size):
    data = str(data)
    len_txt = len(data)
    len_txt_utf8 = len(data.encode('utf-8'))
    data_size = int((len_txt_utf8 - len_txt) / 2 + len_txt)
    return str(data) + " " * (size - data_size)


class Port:
    def __init__(self, name, port, desc=''):
        self.name = name
        self.port = port
        self.desc = desc

    def check_port_in_use(self, host):

        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(1)
                s.connect((host, int(self.port)))
                return "ON"
        except socket.error:
            return "OFF"

    def __str__(self):
        return f"{self.name}"


class PortManage:
    def __init__(self):
        self.host_inner = ''
        self.host_outer = ''
        self.port_list = [
            Port(name='Supervisor', port=8101, desc='Supervisor desc'),
            Port(name='notecron_webserver', port=8061, desc='notecron init webserver'),
            Port(name='notecron_flower', port=8062, desc='notecron init flower'),
            Port(name='notecron_scheduler', port=0, desc='notecron init scheduler'),


            Port(name='phpmyadmin', port=8051, desc='mysql数据管理'),
            Port(name='baota', port=31259, desc='宝塔'),
            Port(name='code-server', port=8443, desc='code-server'),
        ]
        self.get_host()

    def fprint(self):
        print("#" * 100)
        for port in self.port_list:
            status = port.check_port_in_use(self.host_inner)
            url = f"http://{self.host_outer}:{port.port} "
            print(f"# {format_str(status, 6)}"
                  f"{format_str(port.name, 20)} "
                  f"{format_str(url, 30)} "
                  f"{format_str(port.desc, 38)} "
                  f"#")
        print("#" * 100)

    def get_host(self):
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(('8.8.8.8', 80))
            self.host_inner = s.getsockname()[0]

        self.host_outer = requests.get('http://ifconfig.me/ip', timeout=1).text.strip()
