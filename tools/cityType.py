# 一线城市
cityOne = ["北京","上海","广东广州","广东深圳","北京北京","上海上海"]
# 二线城市
cityTwo = ["浙江杭州","天津","天津天津","江苏南京","山东济南","重庆","重庆重庆","山东青岛","辽宁大连","浙江宁波","福建厦门","四川成都","湖北武汉"]
# 三线城市
cityThree = ["黑龙江哈尔滨","辽宁沈阳","陕西西安","吉林长春","湖南长沙","福建福州","河南郑州","河北石家庄","江苏苏州","广东佛山","广东东莞","江苏无锡","山东烟台","山西太原","安徽合肥","江西南昌","广西南宁","云南昆明","浙江温州","山东淄博","河北唐山"]
# 西部地区
cityWest = ["新疆","西藏"]
# 港澳台海外
cityForeign = ["香港","澳门","台湾"]
# 高危城市
cityRisk = ["福建龙岩"]
# 没有数据
error = ["没有","无"]


def get_city_type(x):
    if x in cityOne:
        return "first_tier"
    elif x in cityRisk:
        return "risk_area"
    elif x in cityForeign:
        return "foreign"
    elif x in cityWest:
        return "west"
    elif x in error:
        return "无"
    else:
        return "normal_city"