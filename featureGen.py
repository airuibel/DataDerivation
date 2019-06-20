import pandas as pd
import numpy as np
import json
import time
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta


from tools.findRegion import findAttribution,findRegion
from tools.date import  get_date_type
from tools.cityType import cityOne, cityTwo, cityWest, cityForeign, cityRisk ,get_city_type



# =============设置打印展示输出===========
pd.set_option('display.max_rows', None)
pd.set_option('display.max_columns', None)
pd.set_option('display.width', 10000)


# 时间段
day7 = 7
m1 = 30
m3 = 90
m5 = 150
m6 = 180
# 对应时间段的天数
def days_type(x):
    if x == 7:
        return "day7"
    elif x ==30:
        return "m1"
    elif x ==90:
        return "m3"
    elif x == 150:
        return "m5"
    else:
        return "m6"


# 1.本人基础数据
def call_basic(callRecord,basicInfo):
    birthplace = findRegion(basicInfo["idcard"])
    attribution = findAttribution(basicInfo["mobile"])
    callRecord_c = callRecord.copy()

    try:
        # 生活城市 dataFrame为空时[0]错误
        # 当取不到众数是，把localtion设置为"无"
        location = callRecord[(callRecord["time"].dt.hour > 19) | (callRecord["time"].dt.hour < 7)]["location"].mode()[0]
    except:
        location = "无"
    living_city = get_city_type(location)
    try:
        # 朋友圈城市 正则筛选手机号，然后用手机号给对象去重，再取众数城市为朋友圈城市
        friends_city_ = callRecord_c[callRecord_c["peer_number"].str.match("1[\d]{10}")]. \
            loc[~callRecord_c["peer_number"].duplicated(keep='first')]["peer_localtion"].mode()[0]
    except:
        friends_city_ = "没有"
    friends_city = get_city_type(friends_city_)
    # 最近一次通话的时长
    try:
        last_contact_time = callRecord_c[callRecord_c["time"] ==callRecord_c["time"].max()]["duration"].values[0]
    except:
        last_contact_time = None
    # 五个月关机天数
    callRecord_m5 = callRecord[(callRecord['time'].max() - callRecord['time']).dt.days < m5].copy()
    silence_5m = m5 - callRecord_m5['time'].dt.strftime("%Y-%m-%d").nunique()
    # 五个月通话记录完整性，比值，有通话天数除所有天数
    contacts_completeness = callRecord_m5['time'].dt.strftime("%Y-%m-%d").nunique()/m5
    # 近7天是否一直联系,最近一次通话往前推7天
    callRecord_day7 = callRecord[(callRecord['time'].max() - callRecord['time']).dt.days < day7].copy()
    keep_touch_7day = callRecord_day7['time'].dt.strftime("%Y-%m-%d").nunique() == 7
    # 近30天是否一直联系，同上
    callRecord_m1 = callRecord[(callRecord['time'].max()  - callRecord['time']).dt.days < m1].copy()
    keep_touch_1m = callRecord_m1['time'].dt.strftime("%Y-%m-%d").nunique() == 30
    # 生活城市是否为归属地
    living_city_attribution = location == attribution
    # 生活城市是否为朋友圈城市
    living_city_friends_city = location == friends_city_
    # 生活城市是否为出生城市
    living_city_birthplace = location in birthplace if birthplace else False
    # 连续通话的最大天数
    # 排序时间后迭代时间，把累加的连续天数加入一个列表，取列表的最大值
    time_sort_df = callRecord_c["time"].sort_values()
    last_day = None
    day_period = 0
    day_period_list = []
    for now_day in time_sort_df:
        if last_day:
            days = (now_day-last_day).days
            # 下一个时间比上一个多1，day_period+1
            if days == 1:
                day_period +=1
            # 下一个时间比上一个多1以上，day_period+1加入列表，置零 day_period
            if days > 1:
                day_period_list.append(day_period)
                day_period = 0
        last_day = now_day
    keep_touch_max_day = max(day_period_list) if day_period_list else None
    return {
        "living_city":living_city,
        "friends_city":friends_city,
        "last_contact_time":last_contact_time,
        "silence_5m":silence_5m,
        "keep_touch_max_day":keep_touch_max_day,
        "contacts_completeness":contacts_completeness,
        "keep_touch_7day":keep_touch_7day,
        "keep_touch_1m":keep_touch_1m,
        "living_city_attribution":living_city_attribution,
        "living_city_friends_city":living_city_friends_city,
        "living_city_birthplace":living_city_birthplace,
    }


# 2按照通话时长的分类
def call_duration(callRecord,duration=m5):
    def get_groups_name(x):
        if x <=10:
            return "duration-0_10"
        elif 10 <x <=20:
            return "duration-10_20"
        elif 20 < x <= 30:
            return "duration-20_30"
        elif 30 < x <= 60:
            return "duration-30_60"
        elif 60 < x <= 120:
            return "duration-60_120"
        elif 120 < x <= 180:
            return "duration-120_180"
        elif x > 180:
            return "duration-180_up"
    def get_groups(group):
        letter = group.name.split("-")[-1]
        caller = group["dial_type"] ==1
        called = group["dial_type"] ==0
        return pd.Series({
                # 联系人个数
                f"contacter_{letter}_cnt_{month_letter}":group["peer_number"].nunique(),
                # 联系人个数占比
                f"contacter_{letter}_rate_{month_letter}":group["peer_number"].nunique()/contacter_cnt if contacter_cnt else None,
                # 通话次数
                f"call_{letter}_cnt_{month_letter}":group.shape[0],
                # 通话次数占比
                f"call_{letter}_rate_{month_letter}":group.shape[0]/call_cnt if call_cnt else None,
                # 主叫通话次数
                f"caller_{letter}_cnt_{month_letter}":group[caller].shape[0],
                # 被叫通话次数
                f"called_{letter}_cnt_{month_letter}":group[called].shape[0],
                # 互相通话次数
                f"calls_{letter}_cnt_{month_letter}":len(set(group[caller]["peer_number"].unique()) &
                                                         set(group[called]["peer_number"].unique()))
            })

    # 初始化变量
    result = dict()
    month_letter = days_type(duration)
    callRecord_c = callRecord[(callRecord['time'].max() - callRecord['time']).dt.days < duration].copy()
    if not len(callRecord_c):
        return {}
    contacter_cnt = callRecord_c["peer_number"].nunique()
    call_cnt = callRecord_c.shape[0]

    # 分组通话时长
    callRecord_c["group"] = callRecord_c["duration"].map(get_groups_name)
    group_result = callRecord_c.groupby("group").apply(get_groups)
    # 分组后，不同分组若字段名不一样会返回series，字段一样的时候会返回dataframe，
    if isinstance(group_result,pd.Series):
        result.update(group_result.reset_index(level=0,drop=1).to_dict())
    else:
        # 只有一个分组时回返回dataframe
        result.update(group_result.to_dict(orient="records")[0])

    return result


# 4.按照通话时段的分类，早中晚，周末，工作日节假日
def call_period(callRecord,duration=m5):
    def get_groups_name(x):
        minute = x.hour*60 + x.minute
        if  330<=minute<540:
            return "early_morning"
        elif 540<=minute<690:
            return "morning"
        elif 690<=minute<810:
            return "afternoon"
        elif 810<=minute<1050:
            return "toward_evening"
        elif 1050<=minute<1410:
            return "evening"
        elif minute>=1410 or minute<90:
            return "small_hour"
        elif 90<=minute<330:
            return "midnight"
    def get_groups_name_2(x):
        dayType = get_date_type(x)
        if dayType=="0":
            return "weekday"
        elif dayType=="1":
            return "weekend"
        elif dayType=="2":
            return "holiday"
    def get_groups(group):
        letter = group.name
        return pd.Series({
            f"call_{letter}_cnt_{month_letter}":group.shape[0],
            f"call_{letter}_rate_{month_letter}":group.shape[0]/call_cnt if call_cnt else None,
            f"call_{letter}_time_{month_letter}":group["duration"].sum(),
            f"contacter_{letter}_cnt_{month_letter}":group["peer_number"].nunique()
        })

    # 初始化变量
    result = dict()
    month_letter = days_type(duration)
    callRecord_c = callRecord[(callRecord['time'].max() - callRecord['time']).dt.days < duration].copy()
    if not len(callRecord_c):
        return {}
    call_cnt = callRecord_c.shape[0]

    # 1.分组 时段
    callRecord_c["group"] = callRecord_c["time"].map(get_groups_name)
    group_result = callRecord_c.groupby("group").apply(get_groups)
    if isinstance(group_result, pd.Series):
        result.update(group_result.reset_index(level=0, drop=1).to_dict())
    else:
        result.update(group_result.to_dict(orient="records")[0])

    # 2.分组 节假日类型
    callRecord_c["group"] = callRecord_c["time"].map(get_groups_name_2)
    group_result = callRecord_c.groupby("group").apply(get_groups)
    if isinstance(group_result, pd.Series):
        result.update(group_result.reset_index(level=0, drop=1).to_dict())
    else:
        result.update(group_result.to_dict(orient="records")[0])

    return result


# 6.联系人地区,按联系人归属地来分类
def contacter_location(callRecord,duration=m5):
    def get_groups_name(x):
        if x in cityOne:
            return "first_tier_city"
        elif x in cityRisk:
            return "risk_area"
        elif x in cityForeign:
            return "foreign"
        elif x in cityWest:
            return "west"
        else:
            return "normal_city"
    def get_groups(group):
        letter = group.name
        return pd.Series({
            f"contacter_{letter}_cnt_{month_letter}":group["peer_number"].shape[0],
            f"contacter_{letter}_rate_{month_letter}":group["peer_number"].shape[0]/contacter_cnt if contacter_cnt else None,
            f"call_{letter}_time_{month_letter}":group["duration"].sum(),
            f"call_{letter}_cnt_{month_letter}":group.shape[0],
            f"call_{letter}_rate_{month_letter}":group.shape[0]/call_cnt if call_cnt else None,
        })

    result = dict()
    month_letter = days_type(duration)
    callRecord_c = callRecord[(callRecord['time'].max() - callRecord['time']).dt.days < duration].copy()
    if not len(callRecord_c):
        return {}
    # 清空无地点的数据
    callRecord_c =callRecord_c[~(callRecord_c["location"] == "")]
    call_cnt = callRecord_c.shape[0]
    contacter_cnt = callRecord_c["peer_number"].nunique()

    # 1 异地的情况
    try:
        location = callRecord[(callRecord["time"].dt.hour > 19) | (callRecord["time"].dt.hour < 7)]["location"].mode()[0]
    except:
        location = "无"
    nonlocal_df = callRecord_c[callRecord_c["location"]!=location]
    result.update({
        f"contacter_city_cnt_{month_letter}":nonlocal_df["location"].shape[0],
        f"contacter_nonlocal_cnt_{month_letter}": nonlocal_df["peer_number"].shape[0],
        f"contacter_nonlocal_rate_{month_letter}": nonlocal_df["peer_number"].shape[0] / contacter_cnt if contacter_cnt else None,
        f"call_nonlocal_time_{month_letter}": nonlocal_df["duration"].sum(),
        f"call_nonlocal_cnt_{month_letter}": nonlocal_df.shape[0],
        f"call_nonlocal_rate_{month_letter}": nonlocal_df.shape[0] / call_cnt if call_cnt else None,
    })

    # 2 城市类型分组
    callRecord_c["group"] = callRecord_c["peer_localtion"].map(get_groups_name)
    group_result = callRecord_c.groupby("group").apply(get_groups)
    if isinstance(group_result, pd.Series):
        result.update(group_result.reset_index(level=0, drop=1).to_dict())
    else:
        result.update(group_result.to_dict(orient="records")[0])

    return result


# 7.联系人数量
def contacter_num(callRecord,duration=m5,num=5,dnum=1,_sum=100,_dsum=3):
    # num :月均通话次数的阈值
    # dnum :月均通话次数的阈值
    # _sum :月均通话时长(秒)的阈值
    # _dsum :日均通话时长(秒)的阈值
    def group_handle_1(group):
        return group["duration"].sum()/(duration/30)>_sum
    def group_handle_2(group):
        return group["duration"].sum() / duration > _dsum

    month_letter = days_type(duration)
    callRecord_c = callRecord[(callRecord['time'].max() - callRecord['time']).dt.days < duration].copy()
    if not len(callRecord_c):
        return {}
    contacter_cnt = callRecord_c["peer_number"].nunique()
    caller = callRecord_c["dial_type"] ==1
    called = callRecord_c["dial_type"] ==0

    # 月均联系超多少次的联系人个数
    contacts_month_over_cnt_ = (callRecord_c["peer_number"].value_counts() / (duration / 30) > num).value_counts()
    contacts_month_over_cnt = contacts_month_over_cnt_[True] if True in contacts_month_over_cnt_.index else 0
    # 月均联系时长超多少次的联系人个数
    contacts_month_time_over_cnt_ = callRecord_c.groupby("peer_number").apply(group_handle_1).value_counts()
    contacts_month_time_over_cnt = contacts_month_time_over_cnt_[True] if True in contacts_month_over_cnt_.index else 0
    # 月均联系超多少次的联系人个数占比
    contacts_month_over_rate = contacts_month_over_cnt /contacter_cnt if contacter_cnt else None
    # 月均联系时长超多少次的联系人个数占比
    contacts_month_time_over_rate = contacts_month_time_over_cnt/contacter_cnt if contacter_cnt else None
    # 日均联系超多少次的联系人个数
    contacts_day_over_cnt_ = (callRecord_c["peer_number"].value_counts()/(duration)>dnum).value_counts()
    contacts_day_over_cnt =  contacts_day_over_cnt_[True] if True in contacts_day_over_cnt_.index else 0
    # 日均联系时长超多少次的联系人个数
    contacts_day_time_over_cnt_ = callRecord_c.groupby("peer_number").apply(group_handle_2).value_counts()
    contacts_day_time_over_cnt = contacts_day_time_over_cnt_[True] if True in contacts_day_time_over_cnt_ else 0
    # 日均联系超多少次的联系人个数占比
    contacts_day_over_rate = contacts_day_over_cnt /contacter_cnt if contacter_cnt else None
    # 日均联系时长超多少次的联系人个数占比
    contacts_day_time_over_rate = contacts_day_time_over_cnt/contacter_cnt if contacter_cnt else None

    # 互通的联系人集合
    contacts_set = set(callRecord_c[caller]["peer_number"].unique()) & set(callRecord_c[called]["peer_number"].unique())
    # 互通联系人的通话 Dataframe
    contacts_df = callRecord_c[callRecord_c["peer_number"].isin(contacts_set)].loc[callRecord_c["duration"]>=60]
    # 亲密联系人，通话次数超过5次，主叫超过两次为亲密，最长通话时间超过180s,通话的天数大于一天
    contacts_intimate_set = set()
    for _ in contacts_df["peer_number"].unique():
        if contacts_df[contacts_df["peer_number"]==_].shape[0] >5 and \
                contacts_df[contacts_df["dial_type"] ==1].loc[contacts_df["peer_number"]==_].shape[0] >2 and\
                contacts_df[contacts_df["duration"] >180].loc[contacts_df["peer_number"]==_].shape[0] >0 and\
                contacts_df[contacts_df["peer_number"]==_]["time"].dt.day.nunique()>1:
            contacts_intimate_set.add(_)

    return {
        f"contacts_month_over_cnt_{month_letter}":contacts_month_over_cnt,
        f"contacts_month_time_over_cnt_{month_letter}":contacts_month_time_over_cnt,
        f"contacts_month_over_rate_{month_letter}":contacts_month_over_rate,
        f"contacts_month_time_over_rate_{month_letter}":contacts_month_time_over_rate,
        f"contacts_day_over_cnt_{month_letter}":contacts_day_over_cnt,
        f"contacts_day_time_over_cnt_{month_letter}":contacts_day_time_over_cnt,
        f"contacts_day_over_rate_{month_letter}":contacts_day_over_rate,
        f"contacts_day_time_over_rate_{month_letter}":contacts_day_time_over_rate,
        f"contacter_cnt_{month_letter}":contacter_cnt,
        f"contacts_cnt_{month_letter}":len(contacts_set),
        f"contacts_intimate_{month_letter}":len(contacts_intimate_set)
    }


# 8.通话汇总
def call_summarizing(callRecord,duration=m5):
    def get_groups(group):
        if group.name==0:
            letter = "called"
        else:
            letter = "caller"
        return pd.Series({
            f"{letter}_month_cnt_{month_letter}":group.shape[0],
            f"{letter}_month_rate_{month_letter}":group.shape[0]/call_cnt if call_cnt else None,
            f"{letter}_avg_month_cnt_{month_letter}":group.shape[0]/(duration/30),
            f"{letter}_month_time_{month_letter}":group["duration"].sum(),
            f"{letter}_month_time_rate_{month_letter}":group["duration"].sum()/call_time if call_time else None,
            f"{letter}_avg_month_time_{month_letter}":group["duration"].sum()/(duration/30),
        })

    # 初始化变量
    result = dict()
    month_letter = days_type(duration)
    callRecord_c = callRecord[(callRecord['time'].max() - callRecord['time']).dt.days < duration].copy()
    if not len(callRecord_c):
        return {}
    call_cnt = callRecord_c.shape[0]
    call_time = callRecord_c["duration"].sum()

    # 1.未分组 所有通话
    result.update({
        f"call_max_time_{month_letter}":callRecord_c["duration"].max(),
        f"call_month_cnt_{month_letter}":callRecord_c.shape[0],
        f"call_avg_month_cnt_{month_letter}":callRecord_c.shape[0]/(duration / 30),
        f"call_month_time_{month_letter}":callRecord_c["duration"].sum(),
        f"call_avg_month_time_{month_letter}":callRecord_c["duration"].sum()/(duration / 30)
    })

    # 2.分组 主被叫
    group_result = callRecord_c.groupby("dial_type").apply(get_groups)
    if isinstance(group_result, pd.Series):
        result.update(group_result.reset_index(level=0, drop=1).to_dict())
    else:
        result.update(group_result.to_dict(orient="records")[0])

    # 3.分组 互通
    caller = callRecord_c["dial_type"] == 1
    called = callRecord_c["dial_type"] == 0
    calls_numer = set(callRecord_c[caller]["peer_number"].unique()) & set(callRecord_c[called]["peer_number"].unique())
    calls_df = callRecord_c[callRecord_c["peer_number"].isin(calls_numer)]
    calls_result = {
        f"calls_month_cnt_{month_letter}": calls_df.shape[0],
        f"calls_month_rate_{month_letter}": calls_df.shape[0] / call_cnt if call_cnt else None ,
        f"calls_avg_month_cnt_{month_letter}": calls_df.shape[0] / (duration / 30),
        f"calls_month_time_{month_letter}": calls_df["duration"].sum(),
        f"calls_month_time_rate_{month_letter}": calls_df["duration"].sum() / call_time if call_time else None,
        f"calls_avg_month_time_{month_letter}": calls_df["duration"].sum() / (duration / 30),
    }
    result.update(calls_result)

    return  result


# 10.按照通话费用的分组
def call_fee(callRecord,duration=m5):
    def get_groups_name(x):
        if x<=2:
            return "fee-0_2"
        if 2<x<=5:
            return "fee-2_5"
        if 5<x<=10:
            return "fee-5_10"
        if 10<x<=50:
            return "fee-10_50"
        if x>50:
            return "fee-50_up"
    def get_groups(group):
        letter = group.name.split("-")[-1]
        return pd.Series({
            f"call_fee_{letter}_cnt_{month_letter}":group.shape[0],
            f"call_fee_{letter}_rate_{month_letter}":group.shape[0]/call_cnt if call_cnt else None,
            f"contacter_call_fee_{letter}_cnt_{month_letter}":group["peer_number"].nunique()
        })

    # 初始化变量
    result = dict()
    month_letter = days_type(duration)
    callRecord_c = callRecord[(callRecord['time'].max() - callRecord['time']).dt.days < duration].copy()
    if not len(callRecord_c):
        return {}
    call_cnt = callRecord_c.shape[0]

    # 分组 按照每天的时间段来分组
    callRecord_c["group"] = callRecord_c["fee"].map(get_groups_name)
    group_result = callRecord_c.groupby("group").apply(get_groups)
    if isinstance(group_result, pd.Series):
        result.update(group_result.reset_index(level=0, drop=1).to_dict())
    else:
        result.update(group_result.to_dict(orient="records")[0])

    return result


# ============== weiwei =======================
def get_info_data(data, total_dict):
    now_time = time.strptime(datetime.strftime(datetime.now(), '%Y-%m-%d'), "%Y-%m-%d")
    open_time = time.strptime(data['open_time'], "%Y-%m-%d")
    date1 = datetime(now_time[0], now_time[1], now_time[2])
    date2 = datetime(open_time[0], open_time[1], open_time[2])


    total_dict["name"] = data['name']
    total_dict["mobile"] = data['mobile']
    total_dict["idcard"] = data['idcard']
    total_dict["email"] = data['email']

    if "*" not in data['idcard']:
        total_dict["age"] = int(time.strftime("%Y")) - int(data['idcard'][6:10])
    else:
        total_dict["age"] = None
    total_dict["open_days"] = (date1 - date2).days
    total_dict["mobile_state"] = data['state']
    total_dict["level"] = data['level']
    total_dict["available_balance"] = data['available_balance']

    return total_dict



def get_sms_feature(data, total_dict):
    sms_df = pd.DataFrame()
    sms_df['idcard'] = [] * len(data)
    peer_number_list = [data[i]["peer_number"] for i in range(len(data))]
    sms_df["peer_number"] = [j for j in peer_number_list]
    sms_time_list = [data[i]["time"] for i in range(len(data))]
    sms_df["sms_time"] = [j for j in sms_time_list]
    sms_fee_list = [data[i]["fee"] for i in range(len(data))]
    sms_df["sms_fee"] = [j for j in sms_fee_list]
    send_type_list = [data[i]["send_type"] for i in range(len(data))]
    sms_df["send_type"] = [j for j in send_type_list]

    data = sms_df.copy()
    if len(data) == 0:return total_dict
    data['peer_number'] = data['peer_number']
    data['sms_time'] = pd.to_datetime(data['sms_time'])
    data['sms_day'] = data['sms_time'].map(lambda x: datetime.strftime(x, '%Y-%m-%d'))
    data['sms_month'] = data['sms_time'].map(lambda x: datetime.strftime(x, '%Y-%m'))
    data['time_slot'] = data['sms_time'].map(lambda x: datetime.strftime(x, '%H:%M:%S'))

    month_tuple = [("1m", 30), ('3m', 90), ('6m', 180)]
    now_data = datetime.strptime(datetime.now().strftime('%Y-%m-%d'), '%Y-%m-%d')

    # 近n个月短信总条数
    for month in month_tuple:
        total_dict['msg_cnt_sum_' + month[0]] = data[data.sms_day >= (now_data - timedelta(days=month[1])).strftime("%Y-%m-%d")].shape[0]


    # 近n个月短信平均值
    for month in month_tuple[1:]:
        total_dict['msg_cnt_mean_' + month[0]] = total_dict['msg_cnt_sum_' + month[0]] // int(month[0][0])

    # 近n个月短信发送次数
    for month in month_tuple:
        total_dict['msg_send_cnt_sum_' + month[0]] = data[(data.sms_day >= (now_data - timedelta(days=month[1])).strftime("%Y-%m-%d"))
                                                          & (data.send_type == "SEND")].shape[0]

    # 近n个月短信发送次数平均值
    for month in month_tuple[1:]:
        total_dict['msg_send_cnt_mean_' + month[0]] = total_dict['msg_send_cnt_sum_' + month[0]] // int(month[0][0])

    month1 = data[data.sms_day >= (now_data - timedelta(days=30)).strftime("%Y-%m-%d")].shape[0]
    month2 = data[data.sms_day >= (now_data - timedelta(days=60)).strftime("%Y-%m-%d")].shape[0] - month1
    month3 = data[data.sms_day >= (now_data - timedelta(days=90)).strftime("%Y-%m-%d")].shape[0] - (month1 + month2)
    month4 = data[data.sms_day >= (now_data - timedelta(days=120)).strftime("%Y-%m-%d")].shape[0] - (month1 + month2 + month3)
    month5 = data[data.sms_day >= (now_data - timedelta(days=150)).strftime("%Y-%m-%d")].shape[0] - (month1 + month2 + month3 + month4)
    month6 = data[data.sms_day >= (now_data - timedelta(days=150)).strftime("%Y-%m-%d")].shape[0] - (
            month1 + month2 + month3 + month4 + month5)
    month_list = [month1, month2, month3, month4, month5, month6]

    # 近n个月短信次数的最大值
    for month in month_tuple[1:]:
        np_month = np.array(month_list[:int(month[0][0])])
        total_dict['msg_cnt_max_' + month[0]] = np_month.max()

    # 近n个月短信发送次数的稳定性
    for month in month_tuple[1:]:
        np_month = np.array(month_list[:int(month[0][0])])
        try:
            total_dict['msg_send_cnt_month_stab_' + month[0]] = np_month.std() / np_month.mean()
        except:
            total_dict['msg_send_cnt_month_stab_' + month[0]] = None

    return total_dict



def get_pay_feature(data, total_dict):
    pay_df = pd.DataFrame()
    pay_df['idcard'] = [] * len(data)
    recharge_time_list = [data[i]["recharge_time"] for i in range(len(data))]
    pay_df["recharge_time"] = [j for j in recharge_time_list]
    amount_list = [data[i]["amount"] for i in range(len(data))]
    pay_df["amount"] = [j for j in amount_list]
    type_list = [data[i]["type"] for i in range(len(data))]
    pay_df["type"] = [j for j in type_list]

    data = pay_df.copy()
    data['recharge_time'] = pd.to_datetime(data['recharge_time'])
    data['recharge_day'] = data['recharge_time'].map(lambda x: datetime.strftime(x, '%Y-%m-%d'))
    data['amount'] = data['amount'].map(lambda x: float(x))

    data2 = pd.DataFrame()
    month_tuple = [('3m', 90), ('6m', 180)]
    money = [10, 30, 50, 70, 90]
    now_data = datetime.strptime(datetime.now().strftime('%Y-%m-%d'), '%Y-%m-%d')

    # 近n个月充值总金额/平均值/最大值/次数/平均充值次数
    for month in month_tuple:
        total_dict['recharge_amount_sum_' + month[0]] = \
            data[data.recharge_day >= (now_data - timedelta(days=month[1])).strftime("%Y-%m-%d")]["amount"].sum()
        total_dict['recharge_amount_mean_' + month[0]] = \
            data[data.recharge_day >= (now_data - timedelta(days=month[1])).strftime("%Y-%m-%d")]["amount"].mean()
        total_dict['recharge_amount_max_' + month[0]] = \
            data[data.recharge_day >= (now_data - timedelta(days=month[1])).strftime("%Y-%m-%d")]["amount"].max()
        total_dict['recharge_cnt_sum_' + month[0]] = \
            data[data.recharge_day >= (now_data - timedelta(days=month[1])).strftime("%Y-%m-%d")].shape[0]
        total_dict['recharge_cnt_mean_' + month[0]] = total_dict['recharge_cnt_sum_' + month[0]] // int(month[0][0])


    # 近n个月充值金额大于m的次数
    for month in month_tuple:
        for m in money:
            count_true = \
                (data[data.recharge_day >= (now_data - timedelta(days=month[1])).strftime("%Y-%m-%d")]["amount"] >= m * 100).value_counts()
            if True in count_true:
                total_dict['recharge_amount' + str(m) + '_cnt_' + month[0]] = count_true[True]
            else:
                total_dict['recharge_amount' + str(m) + '_cnt_' + month[0]] = 0

    month1 = data[data.recharge_day >= (now_data - timedelta(days=30)).strftime("%Y-%m-%d")].shape[0]
    month2 = data[data.recharge_day >= (now_data - timedelta(days=60)).strftime("%Y-%m-%d")].shape[0] - month1
    month3 = data[data.recharge_day >= (now_data - timedelta(days=90)).strftime("%Y-%m-%d")].shape[0] - (month1 + month2)
    month4 = data[data.recharge_day >= (now_data - timedelta(days=120)).strftime("%Y-%m-%d")].shape[0] - (month1 + month2 + month3)
    month5 = data[data.recharge_day >= (now_data - timedelta(days=150)).strftime("%Y-%m-%d")].shape[0] - (month1 + month2 + month3 + month4)
    month6 = data[data.recharge_day >= (now_data - timedelta(days=150)).strftime("%Y-%m-%d")].shape[0] - (
            month1 + month2 + month3 + month4 + month5)
    month_list = [month1, month2, month3, month4, month5, month6]

    # 近n个月充值次数的最大值
    for month in month_tuple:
        np_month = np.array(month_list[:int(month[0][0])])
        # data2['recharge_cnt_max_' + month[0]] = np_month.max()
        total_dict['recharge_cnt_max_' + month[0]] = np_month.max()

    return total_dict


def get_bill_feature(data, total_dict):
    bill_df = pd.DataFrame()
    bill_df["idcard"] = [] * len(data)
    bill_month_list = [data[i]["bill_month"] for i in range(len(data))]
    bill_df["bill_month"] = [j for j in bill_month_list]
    total_fee_list = [data[i]["total_fee"] for i in range(len(data))]
    bill_df["total_fee"] = [j for j in total_fee_list]

    data = bill_df.copy()
    data['bill_month'] = data['bill_month'].map(lambda x: datetime.strptime(x, '%Y-%m'))
    data['total_fee'] = data['total_fee'].map(lambda x: float(x))
    data2 = pd.DataFrame()
    now_data = datetime.strptime(datetime.now().strftime('%Y-%m'), '%Y-%m')
    month_tuple = [('3m', 90), ('6m', 180)]
    money = [30, 50, 70, 90, 110]

    # 近n个月总费用之和、最大值、平均值
    for month in month_tuple:
        total_dict['bill_total_fee_sum_' + month[0]] = \
            data[data.bill_month > (now_data - relativedelta(months=int(month[0][0]))).strftime("%Y-%m-%d")]["total_fee"].sum()
        total_dict['bill_total_fee_max_' + month[0]] = \
            data[data.bill_month > (now_data - relativedelta(months=int(month[0][0]))).strftime("%Y-%m-%d")]["total_fee"].max()
        total_dict['bill_total_fee_mean_' + month[0]] = \
            data[data.bill_month > (now_data - relativedelta(months=int(month[0][0]))).strftime("%Y-%m-%d")]["total_fee"].mean()

    # 近n个月充值金额大于m的次数
    for month in month_tuple:
        for m in money:
            count_true = \
                (data[data.bill_month >= (now_data - relativedelta(months=int(month[0][0]))).strftime("%Y-%m-%d")][
                     "total_fee"] >= m * 100).value_counts()
            if True in count_true:
                total_dict['bill_totalfee' + str(m) + '_cnt_' + month[0]] = count_true[True]
            else:
                total_dict['bill_totalfee' + str(m) + '_cnt_' + month[0]] = 0

    # 近6个月充值稳定性、偏度、最大增长率、平均增长率、最小增长率
    total_dict['bill_total_fee_stab_6m'] = data[data.bill_month > (now_data - relativedelta(months=6)).strftime("%Y-%m-%d")][
                                               "total_fee"].std() / \
                                           data[data.bill_month > (now_data - relativedelta(months=6)).strftime("%Y-%m-%d")][
                                               "total_fee"].mean()
    total_dict['bill_total_fee_skew_6m'] = data[data.bill_month > (now_data - relativedelta(months=6)).strftime("%Y-%m-%d")][
        "total_fee"].skew()


    data = data.sort_values(by="bill_month", ascending=False)
    rate_list = []

    for i in range(data["total_fee"].shape[0]-1):
        rate_list.append(data["total_fee"][i] / data["total_fee"][i + 1])

    if len(rate_list) != 0:
        rate_arr = np.array(rate_list)
        total_dict['bill_total_fee_rise_rate_max_6m'] = rate_arr.max()
        total_dict['bill_total_fee_rise_rate_min_6m'] = rate_arr.min()
        total_dict['bill_total_fee_rise_rate_mean_6m'] = rate_arr.mean()

    return total_dict



def write_resutl_to_file(result):
    values = []
    with open("head") as f:
        head = f.read().replace("\n","").split("^")
        for field in head:
            value =result.get(field,"")
            values.append(value)
    line = ",".join(list(map(lambda x:str(x),values))) + "\n"
    with open("result.csv","a",encoding="utf-8") as f:
        f.write(line)



def main():
    for i in range(1,160):
        real_name =  f"ykd_clear_file/ykd_{i}.txt"
        f = open(real_name,encoding="utf-8")
        for index,line in enumerate(f):
            print(real_name,index)
            record = json.loads(line)
            try:
                basicInfo_ = record["basicInfo"]
                billRecord_ = record["billRecord"]
                callRecord_ = record["callRecord"]
                payRecord_ = record["payRecord"]
                smsRecord_ = record["smsRecord"]
                # 删除detail_id,location_type特征
                basicInfo = basicInfo_
                callRecord = pd.DataFrame(pd.read_json(json.dumps(callRecord_)))
                callRecord.drop(["details_id", "location_type"], axis=1, inplace=True)
                # 格式化时间
                callRecord["time"] = pd.to_datetime(callRecord["time"])
                # 格式化手机号
                callRecord["peer_number"] = callRecord["peer_number"].astype("str")
                # 转化成主叫1，被叫0
                callRecord["dial_type"] = callRecord["dial_type"].map(lambda x: 1 if x == "DIAL" else 0)
                # 添加联系人的归属地
                callRecord["peer_localtion"] = callRecord["peer_number"].map(findAttribution)

                result = dict()
                result.update(call_basic(callRecord,basicInfo))
                for i in [m1,m3,m5]:
                    result.update(call_duration(callRecord,i))
                    result.update(call_period(callRecord,i))
                    result.update(contacter_location(callRecord,i))
                    result.update(contacter_num(callRecord,i))
                    result.update(call_summarizing(callRecord,i))
                    result.update(call_fee(callRecord,i))
                # ==========微微==========
                result = get_info_data(basicInfo_, result)
                result = get_sms_feature(smsRecord_, result)
                result =get_pay_feature(payRecord_, result)
                result =get_bill_feature(billRecord_, result)
                write_resutl_to_file(result)
            except Exception as e:
                with open("failed","a",encoding="utf") as f:
                    f.write(real_name +"^"+line)
        f.close()





main()
