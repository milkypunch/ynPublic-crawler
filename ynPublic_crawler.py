import requests
import json
import execjs
from retrying import retry
import hashlib
import pymongo

with open("encParams.js", encoding= "utf-8") as f:
    jscode = f.read()
context = execjs.compile(jscode)

headers = {
    "Content-Type": "application/json;charset=UTF-8", # faut
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
    "appId": "84ded2cd478642b2",
}
def generate_params(headers_):
    initial_data = {
        "key": "query"
        }
    initial_params = context.call("get_params", initial_data)

    url = "https://www.ynjzjgcx.com/prod-api/mohurd-pub/vcode/genVcode"
    data = {
        "params": initial_params
    }
    data = json.dumps(data, separators=(',', ':'))
    response = requests.post(url, headers=headers_, data=data)

    res = json.loads(response.json()["data"])
    slideId = res["slideId"]
    smallImage = res["smallImage"]
    bigImage = res["bigImage"]
    return  slideId, smallImage, bigImage

def slide_verify(slide_image, background_image, verify_type="20111"):
    _headers = {
        'Content-Type': 'application/json'
    }
    _custom_url = "http://api.jfbym.com/api/YmServer/customApi"
    payload = {
        "slide_image": slide_image,
        "background_image": background_image,
        "token": '_DrOYPrOmEQ11FuwuMjcOPPBa_nx2cXrlEuFpzslZBY',
        "type": verify_type
    }
    resp = requests.post(_custom_url, headers=_headers, data=json.dumps(payload))
    
    return resp.json()['data']['data']

@retry(stop_max_attempt_number=5, wait_fixed=2000)
def get_records_list(page, headers_):
    slideId, smallImage, bigImage = generate_params(headers_)
    width = int(slide_verify(smallImage,bigImage)) # 图片不会刷新的情况
    print(width)
    data2 = {
        "pageNum": page,
        "pageSize": 10,
        "certificateType": "",
        "name": "",
        "slideId": slideId,
        "key": "query",
        "width": width  
    }

    params = context.call("get_params", data2)
    print(params)

    url_ = "https://www.ynjzjgcx.com/prod-api/mohurd-pub/dataServ/findBaseEntDpPage"
    data_ = {
        "params": params
    }
    data = json.dumps(data_, separators=(',', ':'))
    response = requests.post(url_, headers=headers, data=data)
    if response.json()["code"] == 200:
        print("获取参数请求成功")
        list_ = response.json()["data"]["records"]
        return list_
    else: 
        print(response.text)
        raise ValueError("Temporary failure")

def hash_string(s: str):
    """生成字符串的哈希值"""
    return hashlib.md5(s.encode()).hexdigest()


def process_data(_list):
    # list_ = res_dict["records"]
    seen_codes = set()  # 用于存储唯一的哈希值
    unique_items = []  # 用于存储唯一的条目

    for item in _list:
        creditCode = item["creditCode"]
        code_hash = hash_string(creditCode)  # 对名称进行哈希
        if code_hash not in seen_codes:  # 检查哈希值是否已经存在
            seen_codes.add(code_hash)  # 添加到集合中
            unique_items.append({
                "creditCode": creditCode,
                "name": item["name"],
                "address": item["address"]
            })
    print(unique_items, len(unique_items), 'items')
    return unique_items  # 返回唯一的条目列表

def save_movie_info(db, items):
    if items:
        db.insert_many(items)
        print('insert successfully: ', len(items), 'items')

def close(client_mongo):
    client_mongo.close()
    print("MongoDB connection closed")


mongo_client = pymongo.MongoClient()
collection = mongo_client['py_spider']['yn_enterprise']

for page in range(1,11):    
    try:
        item_list = get_records_list(page, headers)
        # print(f"Page{page} --->", item_list)
    except Exception as e:
        print(f"最终请求失败: {e}")
    
    unique_list = process_data(item_list)
    
    save_movie_info(collection, unique_list)

close(mongo_client)

