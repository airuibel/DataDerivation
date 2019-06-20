import datetime
import calendar
import json
import re
import os
import requests

# 获取从现在开始几个月后的1号和末号，
def flexible_date_range(end_date, months=6):
    """
    获取从现在开始几个月后的1号和末号，
    如2018-11-01, 2018-11-30
    :param end_date: 最低结束时间
    :param months: 获取的几个月份，默认6个月
    :return: [(2018-11-01, 2018-11-30), (2018-10-01, 2018-10-31)]
    """
    dt = datetime.date.today().replace(
        day=calendar.monthrange(datetime.date.today().year, datetime.date.today().month)[1])
    dt_list = []
    for i in range(months):
        dt_list.append((dt, datetime.date(year=dt.year, month=dt.month, day=1)))
        if dt.month == 1:
            dt = datetime.date(year=dt.year - 1, month=12, day=1)
        dt = datetime.date(year=dt.year, month=dt.month - 1, day=calendar.monthrange(dt.year, dt.month - 1)[1])
        if dt <= end_date:
            break
    return dt_list


# 获取月份的列表
def create_month_list():
    dt = datetime.datetime.now()
    # dt = datetime.datetime.strptime('2018-01', "%Y-%m")
    year, month = dt.strftime('%Y-%m').split('-')
    dt_list = []
    for _ in range(6):
        if len(month) == 1:
            month = '0' + month
        dt_list.append(year + month)
        month = str(int(month) - 1)
        if month == '0':
            year = str(eval(year + '-1'))
            month = '12'
    return dt_list


# jsonp转换json
def loads_jsonp(_jsonp):
    try:
        return json.loads(re.match(".*?({.*}).*", _jsonp, re.S).group(1))
    except Exception as e:
        raise ValueError('Invalid Input')


# 出生日期获取星座
def zodiac(month, day):
    n = ('摩羯座', '水瓶座', '双鱼座', '白羊座', '金牛座', '双子座', '巨蟹座', '狮子座', '处女座', '天秤座', '天蝎座', '射手座')
    d = ((1, 20), (2, 19), (3, 21), (4, 21), (5, 21), (6, 22), (7, 23), (8, 23), (9, 23), (10, 23), (11, 23), (12, 23))
    return n[len(list(filter(lambda y: y <= (month, day), d))) % 12]


# 获取某一天是节假日还是工作日双休日
def get_date_type(date):
    """
    获取某一天是工作日（0），双休日（1），节假日（2）
    date: a datetime obj
    """
    strf_date = date.strftime("%Y%m%d")

    this_year = date.year
    this_year_str = str(this_year)
    next_year = this_year+1

    date_file = os.path.join(os.path.dirname(os.path.
            abspath(__file__)),'date.txt')
    if not os.path.exists(date_file):
        with open(date_file,'w') as f:
            f.write("{}")

    try:
        with open(date_file) as f:
            date_dict_gather =eval(f.read())
            date_dict = date_dict_gather.get(this_year_str,{})
    except Exception as e:
        date_dict_gather = {}
        date_dict = {}

    if not date_dict:
        day_begin = datetime.date(this_year,1,1)
        day_end = datetime.date(next_year,1,1)
        for i in range((day_end - day_begin).days):
            day = day_begin + datetime.timedelta(days=i)
            date = day.strftime("%Y%m%d")
            url = f"http://tool.bitefu.net/jiari/?d={date}"
            while 1:
                try:
                    res = requests.get(url,verify=False,timeout=2).text
                    if res in "012":
                        date_dict[date] = res
                        print(f"{date} == {res}")
                        break
                except:
                    pass

        date_dict_gather[str(this_year)] = date_dict
        with open(date_file,'w') as f:
            f.write(str(date_dict_gather))

    date_type = date_dict[strf_date]
    return date_type

