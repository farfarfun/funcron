# coding:utf -8
import smtplib
from email.mime.text import MIMEText
from time import sleep

import demjson
import numpy as np
import requests
from apscheduler.jobstores.memory import MemoryJobStore
from notecron.tool.mail import send_mail_163
from notetool import SecretManage
from notetool.tool.log import log

logger = log("ba-crawler")


class BodyGuardPharm:
    headers = {
        'Connection': 'keep-alive',
        'Accept': '*/*',
        'User-Agent': 'Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/86.0.4240.198 Mobile Safari/537.36',
        'X-Requested-With': 'XMLHttpRequest',
        'Sec-Fetch-Site': 'same-origin',
        'Sec-Fetch-Mode': 'cors',
        'Sec-Fetch-Dest': 'empty',
        'Referer': 'https://www.ba.de/',
        'Accept-Language': 'zh-CN,zh;q=0.9',
    }

    cookies = {
        'bfd_tma': '1117bc1791847d562bad71c8c70f9f7f.43982155.1603383362000',
        'bfd_tmd': '1117bc1791847d562bad71c8c70f9f7f.94043204.1603383362000',
        'frontend': 'IOUG3TTU3MVV7LC4IALOUVXRZ4XWYTRCXK6WMG6FCFLMV4Z27LZQ',
        '_uuid': '3295CD0F-94D4-4909-BE27-4577A16FC41D',
        '_itag': '1.33.10292.8051.85441',
        'Hm_lvt_2d4ccea8e83c69adfe112abcbb762893': '1604716003,1605109337,1606130420',
        'SA_SEARCH_FIRST_PAGE_SIZE': '40',
        'SA_SEARCH_FIRST_SORT': '0',
        'sensorsdata2015jssdkcross': '%7B%22distinct_id%22%3A%2233-662736%22%2C%22%24device_id%22%3A%22175511884cad-089ea9aba34d97-163f6152-1296000-175511884cbf7%22%2C%22props%22%3A%7B%22%24latest_traffic_source_type%22%3A%22%E7%9B%B4%E6%8E%A5%E6%B5%81%E9%87%8F%22%2C%22%24latest_referrer%22%3A%22%22%2C%22%24latest_search_keyword%22%3A%22%E6%9C%AA%E5%8F%96%E5%88%B0%E5%80%BC_%E7%9B%B4%E6%8E%A5%E6%89%93%E5%BC%80%22%7D%2C%22first_id%22%3A%22175511884cad-089ea9aba34d97-163f6152-1296000-175511884cbf7%22%7D',
        'LAST_SEARCH': '%7B%22search_page_num%22%3A%221%22%2C%22search_keyword%22%3A%22dolormin%22%2C%22search_result_num%22%3A%2217%22%2C%22is_first_search%22%3Atrue%2C%22search_filter%22%3Afalse%7D',
        'bfd_sid': '0c78d3a4b982d0df63d018647e8a6b5e',
        'bfd_tmc': '1117bc1791847d562bad71c8c70f9f7f.65408274.1606466124000',
        'cart_item_count': '11',
        'SA_RECOMMEND_INFO': '%7B%2206946190%22%3A%7B%22i%22%3A%22favorites-guessYouLike%22%2C%22s%22%3A%22baifendian%22%7D%7D',
        'Hm_lpvt_2d4ccea8e83c69adfe112abcbb762893': '1606466908',
    }

    def __init__(self):
        pass

    def add_cart(self, product_id=169826, qty=1):
        params = {
            'product_id': product_id,
            'qty': qty
        }

        response = requests.get('https://www.ba.de/v2/item/add',
                                headers=self.headers,
                                params=params,
                                cookies=self.cookies)

        return demjson.decode(response.text)


# res2 = ba.add_cart(product_id=44435)
def watch_product(product_id=44434):
    ba = BodyGuardPharm()
    res = ba.add_cart(product_id=44434)
    logger.info("product={},response={}".format(product_id, res))

    if res['status'] == 200:
        content = "抢到了，快找牛哥，晚了就没了,product={},response={}".format(
            product_id, res)
        send_mail_163(receive=["1007530194@qq.com",
                               '594210169@qq.com'], content=content)
        return True

    return False
