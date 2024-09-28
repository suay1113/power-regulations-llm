"""
Translate Tool

这个脚本提供了百度翻译相关功能，账号为免费账户，每月50W token

Author: Suanyang
Date: 2023-08-18
Content: suanyang@mininglamp.com
"""

import requests
import random
import json
from hashlib import md5

def translate_text(query, from_lang='auto', to_lang='en', appid = '20240301001978745', appkey = 'UXXfWcMpja1ysPPC77ld'):
    """
    翻译文本：注意翻译过程中部分标点比如"!, *, ..."等可能失效

    :param query:     待翻译的文本
    :param from_lang: 源语言，默认为'auto'（自动检测语言）
    :param to_lang:   目标语言，默认为'en'(英文) ，可选'zh'（中文）等
    :param appid:     百度翻译API的应用ID     chenxu:20230905001804960  say:20230607001703473  gzh:20240301001978745
    :param appkey:    百度翻译API的应用密钥   chenxu:HcgkiPb5cDmRgXqyibAt   say: cjq58oFRdAP4VL7sSgIi  gzh:UXXfWcMpja1ysPPC77ld
    :return:          翻译后的文本
    """
    
    endpoint = 'http://api.fanyi.baidu.com'
    path = '/api/trans/vip/translate'
    url = endpoint + path

    def make_md5(s, encoding='utf-8'):
        return md5(s.encode(encoding)).hexdigest()

    salt = random.randint(32768, 65536)
    sign = make_md5(appid + query + str(salt) + appkey)

    headers = {'Content-Type': 'application/x-www-form-urlencoded'}
    payload = {'appid': appid, 'q': query, 'from': from_lang, 'to': to_lang, 'salt': salt, 'sign': sign}

    r = requests.post(url, params=payload, headers=headers)
    result = r.json()
    # print(result)
    translate_list = []
    for ans in result['trans_result']:
        translate_list.append(ans['dst'])

    return '\n'.join(translate_list)

if __name__ =='__main__':
    query = """
    The attributes of the bottom in the picture are:\n* Material: The bottle is made of glass.
    * Style: The bottle has a sleek and modern design with a pink flower pattern on it.
    * Feeling: The image gives off a serene and refreshing vibe, which suggests that the product is likely related to wellness or skincare.
    * Form: The bottle is cylindrical in shape with a rounded bottom and a narrow neck.
    * Shape: The bottle is shaped like a traditional water bottle.
    * Capacity: It is not visible in the image, but based on its size, it appears to hold a reasonable amount of water for drinking or use in skincare.
    * Color: The bottle is pink in color with a white pink flower design.
    * Country: Based on the image, it is difficult to determine the country of origin.
    * Scene: The image shows the bottle of water standing next to a beautiful floral arrangement, which could be taken at a spa, wellness center, or a retail store selling skincare products."""
    query = "这段代码在做什么？"
    translate_list = translate_text(query)
    print(translate_list)
