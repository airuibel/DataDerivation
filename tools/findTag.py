import requests



# 批量查询，输入手机号列表
def findMultiTag(mobile_list):
    url = "http://182.92.254.9:8211/v1/phone/tag/query-multiple/"
    data = {
        "phone_list":mobile_list
    }
    return requests.post(url,json=data).json()

# 查询单个号码
def fingOneTag(mobile):
    url = f"http://182.92.254.9:8211/v1/phone/tag/{mobile}/"
    return  requests.get(url).json()