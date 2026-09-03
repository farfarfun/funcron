"""funcron.server.port_manage 的单测：格式化辅助函数与端口探测，不依赖网络。"""

from funcron.server.port_manage import Port, format_str


def test_format_str_pads_ascii_to_width():
    assert format_str("ON", 6) == "ON    "


def test_format_str_counts_chinese_char_as_double_width():
    # "宝塔" 两个中文字符按 4 个显示位计算，补齐到宽度 6 应只补 2 个空格。
    assert format_str("宝塔", 6) == "宝塔  "


def test_port_str_returns_name():
    port = Port(name="funcron_webserver", port=8061, desc="desc")
    assert str(port) == "funcron_webserver"


def test_check_port_in_use_off_for_closed_port():
    # 127.0.0.1 上一个几乎不可能被占用的高位端口，预期探测为关闭。
    port = Port(name="closed", port=59, desc="")
    assert port.check_port_in_use("127.0.0.1") == "OFF"
