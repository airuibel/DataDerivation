import re
import os
import json
import datetime
import jieba

import phone
import pandas as pd
import requests
from dateutil import rrule
from dateutil.relativedelta import relativedelta
from constant.region import REGION_DICT, MUNICIPALITY

from tools.date import zodiac


PHONE_QUERY_URL = "'http://182.92.254.9:8211/v1/'"
# 设置打印展示输出
pd.set_option('display.max_rows', None)
pd.set_option('display.max_columns', None)
pd.set_option('display.width', 10000)

PHONE_FIND = phone.Phone()
now = datetime.datetime.now()
week1_date = now - relativedelta(days=7)
month1_date = now - relativedelta(months=1)
month3_date = now - relativedelta(months=3)
month6_date = now - relativedelta(years=1)


class Report:

    def __init__(self, base_info, bill, call_record):
        self.base_info = base_info
        self.bill = pd.DataFrame.from_dict(bill)
        self.call_record = pd.DataFrame.from_dict(call_record)
        self.call_record['call_date'] = pd.to_datetime(self.call_record['call_date'])
        self.report = {}

    @staticmethod
    def to_json_by_rows(df):
        return df.to_json(lines=True, orient='records')

    @staticmethod
    def to_python_obj_by_rows(df):
        return df.to_dict(orient='record')

    @staticmethod
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



    # ================报表函数===========
    @staticmethod
    def personal_info(base_info):
        """个人信息,姓名身份证号是查询提供的"""
        now = datetime.datetime.now()
        form_cardid = base_info.get('form_cardid','')
        age = ''
        gender = ''
        constellation = ''
        region = ''
        province = ''
        city = ''
        county_area = ''
        if re.match(
                r'(^[1-9]\d{5}(18|19|([23]\d))\d{2}((0[1-9])|(10|11|12))(([0-2][1-9])|10|20|30|31)\d{3}[0-9Xx]$)|(^[1-9]\d{5}\d{2}((0[1-9])|(10|11|12))(([0-2][1-9])|10|20|30|31)\d{2}[0-9Xx]$)',
                form_cardid):
            age = now.year - int(form_cardid[6:10])
            gender = '男' if int(form_cardid[16:17]) % 2 else '女'
            constellation = zodiac(int(form_cardid[10:12]), int(form_cardid[12:14]))
            region = REGION_DICT.get(form_cardid[:6])
            r = list(jieba.cut(region))
            if r[0] in MUNICIPALITY:
                city, county_area = r
            else:
                if len(r) < 3:
                    province, city = r
                else:
                    province, city, county_area = r

        return dict(
                # 姓名
                name=base_info.get('form_name',''),
                # 身份证号码
                idcard=form_cardid,
                # 年龄
                gender=gender,
                # 星座
                age=age,
                # 星座
                constellation=constellation,
                # 所属省
                province=province,
                # 所属市
                city=city,
                # 所属县
                county_area=county_area,
                # 籍贯
                region=region
                )

    @staticmethod
    def mobile_basic_info(base_info,call_record):
        """手机号基本信息，姓名身份证号为运营商提供"""
        work_place = \
            call_record[(call_record['call_date'].dt.hour >= 9) & (call_record['call_date'].dt.hour < 18)].groupby(
                'other_area').size().sort_values().index[-1]
        living_place = \
            call_record[((call_record['call_date'].dt.hour >= 0) & (call_record['call_date'].dt.hour < 9)) | (
                    (call_record['call_date'].dt.hour >= 18) & (call_record['call_date'].dt.hour < 24))].groupby(
                'other_area').size().sort_values().index[-1]
        return dict(
                # 手机号
                mobile=base_info.get('mobile',''),
                #用户姓名
                name=base_info.get('name',''),
                # 身份证号
                idcard=base_info.get('idcard',''),
                # 开户时间
                opendate=base_info.get('opendate',''),
                # 开户时长
                net_age=base_info.get('net_age',''),
                # 用户邮箱
                email=base_info.get('email',''),
                # 地址
                address=base_info.get('address'),
                # 是否实名认证
                Certification=True,
                # 手机号码归属地
                attribution=base_info.get('attribution',''),
                # 居住地址
                living_place=living_place,
                # 工作地址
                work_place=work_place
            )

    @staticmethod
    def mobile_account_info(base_info):
        """手机号的账户信息"""
        return dict(
            # 套餐
            cur_plan_name=base_info.get('cur_plan_name',''),
            # 账户余额
            balance=base_info.get('balance',''),
            # 当前话费
            owe_fee=base_info.get('owe_fee',''),
            # 账户星级
            star_level=base_info.get('star_level',''),
            # 账户状态
            user_status=base_info.get('user_status',''),
            # 积分
            star_score=base_info.get('star_score','')
            )

    @staticmethod
    def bill_info(bill):
        """账单信息"""
        results = []
        for item in bill.itertuples():
            results.append({
                            # 账单周期
                            'month': item.date.replace('-01', ''),
                            # 费用合计
                            'total_fee': item.total_fee,
                            # 手机号
                            'mobile': item.mobile,
                            # 费用类型
                            'fee_type': '增值业务费,固定费用,短信,网络,通话,其他',
                            # 金额
                            'fee_info': f'增值业务费{item.business_fee},固定费用:{item.fixed_fee},短信:{item.message_fee},网络:{item.net_fee},通话:{item.voice_fee},其他:{item.other_fee}'
                            })
        return results

    @staticmethod
    def call_and_action_data(base_info, call_record):
        """通话详单和用户行为检测"""
        open_date = datetime.datetime.strptime(base_info.get('opendate',''), '%Y-%m-%d')
        months = rrule.rrule(rrule.MONTHLY, dtstart=open_date, until=now).count()
        mobile = str(base_info.get('mobile',''))

        def handle1(group):
            weekend = (group['call_date'].dt.weekday == 5) | (group['call_date'].dt.weekday == 6)
            weekday = (group['call_date'].dt.weekday >= 0) & (group['call_date'].dt.weekday < 5)
            week1 = group['call_date'] > week1_date
            month1 = group['call_date'] > month1_date
            month3 = group['call_date'] > month3_date
            month6 = group['call_date'] > month6_date
            caller = group['call_type'] == 1
            called = group['call_type'] == 2
            day = (7 < group['call_date'].dt.hour) & (group['call_date'].dt.hour <= 24)
            night = (0 < group['call_date'].dt.hour) & (group['call_date'].dt.hour <= 7)
            morning = (6 <= group['call_date'].dt.hour) & (group['call_date'].dt.hour < 12)
            noon = (12 <= group['call_date'].dt.hour) & (group['call_date'].dt.hour < 14)
            afternoon = (14 <= group['call_date'].dt.hour) & (group['call_date'].dt.hour < 18)
            evening = (18 <= group['call_date'].dt.hour) & (group['call_date'].dt.hour < 23)
            earlymorning = ((23 <= group['call_date'].dt.hour) & (group['call_date'].dt.hour < 24)) | (
                    24 <= group['call_date'].dt.hour) & (group['call_date'].dt.hour < 6)
            allday = morning & noon & afternoon & evening & earlymorning
            intimate = (((caller > 0) & (called > 0) & (group['call_long_hour'].max() > 60)) | (
                    group['call_long_hour'].max() > 180) | (group.shape[0] > 5) | (caller > 2))
            return pd.Series({
                'call_location': '^'.join(group['call_area'].unique()),
                'mobile': group.name,
                'attribution': group['other_area'][group.index[0]],
                'call_cnt': group.shape[0],
                'caller_cnt': group[caller].shape[0],
                'called_cnt': group[called].shape[0],
                'call_time': group['call_long_hour'].sum(),
                'caller_call_time': group[caller]['call_long_hour'].sum(),
                'called_call_time': group[called]['call_long_hour'].sum(),
                'call_cnt_1w': group[week1].shape[0],
                'call_cnt_1m': group[month1].shape[0],
                'call_cnt_3m': group[month3].shape[0],
                'call_cnt_6m': group[month6].shape[0],
                'call_time_1m': group[month1]['call_long_hour'].sum(),
                'call_time_3m': group[month3]['call_long_hour'].sum(),
                'call_time_6m': group[month6]['call_long_hour'].sum(),
                'caller_time_3m': group[month3 & caller]['call_long_hour'].sum(),
                'caller_time_6m': group[month6 & caller]['call_long_hour'].sum(),
                'called_time_3m': group[month3 & called]['call_long_hour'].sum(),
                'called_time_6m': group[month6 & called]['call_long_hour'].sum(),
                'caller_cnt_1m': group[month1 & caller].shape[0],
                'caller_cnt_3m': group[month3 & caller].shape[0],
                'caller_cnt_6m': group[month6 & caller].shape[0],
                'called_cnt_1m': group[month1 & called].shape[0],
                'called_cnt_3m': group[month3 & called].shape[0],
                'called_cnt_6m': group[month6 & called].shape[0],
                'call_cnt_day_1m': group[month1 & day].shape[0],
                'call_cnt_day_3m': group[month3 & day].shape[0],
                'call_cnt_day_6m': group[month6 & day].shape[0],
                'call_cnt_night_1m': group[month1 & night].shape[0],
                'call_cnt_night_3m': group[month3 & night].shape[0],
                'call_cnt_night_6m': group[month6 & night].shape[0],
                'call_cnt_weekday_1m': group[month1 & weekday].shape[0],
                'call_cnt_weekday_3m': group[month3 & weekday].shape[0],
                'call_cnt_weekday_6m': group[month6 & weekday].shape[0],
                'call_cnt_weekend_1m': group[month1 & weekend].shape[0],
                'call_cnt_weekend_3m': group[month3 & weekend].shape[0],
                'call_cnt_weekend_6m': group[month6 & weekend].shape[0],
                'call_cnt_allday_1m': group[month1 & allday].shape[0],
                'call_cnt_allday_3m': group[month3 & allday].shape[0],
                'call_cnt_allday_6m': group[month6 & allday].shape[0],
                'call_time_first': group['call_date'].sort_values().head(1).dt.strftime('%Y-%m-%d %H:%M:%S').values[0],
                'call_time_last':
                    group['call_date'].sort_values(ascending=False).head(1).dt.strftime('%Y-%m-%d %H:%M:%S').values[0],
                'call_time_longest': group['call_long_hour'].max(),
                'call_time_shortest': group['call_long_hour'].min(),
                'call_time_avg': round(group['call_long_hour'].mean(), 2),
                'is_intimate': bool(group[intimate].shape[0]),
            })

        queryset = call_record.groupby('other_mobile').apply(handle1).sort_values(['call_cnt', 'call_time'],
                                                                                  ascending=False).to_dict(
            orient='record')
        caller_mobiles = call_record[call_record['call_type'] == 1]['other_mobile'].unique()
        called_mobiles = call_record[call_record['call_type'] == 2]['other_mobile'].unique()
        a = set(caller_mobiles) & set(called_mobiles)
        inter_cnt = len(a)
        call_num = call_record['other_mobile'].nunique()
        result = []
        mobile_list = {"phone_list": [str(i['mobile']) for i in queryset]}

        # 查询标签，重试三次
        retry = 3
        while retry:
            try:
                tag_list = requests.post(PHONE_QUERY_URL + 'phone/tag/query-multiple/', json=mobile_list).json()
                break
            except Exception as e:
                print(e)
                retry -= 1
        else:
            tag_list = []

        tag_dict = dict()
        for tag in tag_list:
            mobile = tag.get('phone', '')
            if not mobile:
                continue
            tag_dict[mobile] = tag
        for _ in queryset:
            _['tag'] = tag_dict.get(str(_['mobile']), {}).get('tag', '未知')
            result.append(_)

        no_call_cnt = 180 - call_record['call_date'].dt.normalize().nunique()
        all_cnt = call_record.shape[0]
        all_time = call_record['call_long_hour'].sum()
        caller_cnt = call_record[call_record['call_type'] == 1].shape[0]
        called_cnt = call_record[call_record['call_type'] == 2].shape[0]
        caller_time = call_record[call_record['call_type'] == 1]['call_long_hour'].sum()
        called_time = call_record[call_record['call_type'] == 2]['call_long_hour'].sum()

        aomen_cnt = call_record[call_record['other_area'] == '澳门'].shape[0]
        aomen_caller_cnt = call_record[(call_record['other_area'] == '澳门') & (call_record['call_type'] == 1)].shape[0]
        aomen_called_cnt = call_record[(call_record['other_area'] == '澳门') & (call_record['call_type'] == 2)].shape[0]
        police_cnt = call_record[call_record['other_mobile'] == 110].shape[0]
        police_caller_cnt = call_record[(call_record['other_mobile'] == 110) & (call_record['call_type'] == 1)].shape[0]
        police_called_cnt = call_record[(call_record['other_mobile'] == 110) & (call_record['call_type'] == 2)].shape[0]
        emergency_cnt = call_record[call_record['other_mobile'] == 120].shape[0]
        emergency_caller_cnt = \
            call_record[(call_record['other_mobile'] == 120) & (call_record['call_type'] == 1)].shape[0]
        emergency_called_cnt = \
            call_record[(call_record['other_mobile'] == 120) & (call_record['call_type'] == 2)].shape[0]
        lawyer_cnt = 0
        lawyer_num = 0
        lawyer_caller_cnt = 0
        lawyer_caller_time = 0
        lawyer_called_cnt = 0
        lawyer_called_time = 0
        court_cnt = 0
        court_num = 0
        court_caller_cnt = 0
        court_caller_time = 0
        court_called_cnt = 0
        court_called_time = 0
        loan_cnt = 0
        loan_num = 0
        loan_caller_cnt = 0
        loan_caller_time = 0
        loan_called_cnt = 0
        loan_called_time = 0
        bank_cnt = 0
        bank_num = 0
        bank_caller_cnt = 0
        bank_caller_time = 0
        bank_called_cnt = 0
        bank_called_time = 0
        credit_card_cnt = 0
        credit_card_num = 0
        credit_card_caller_cnt = 0
        credit_card_caller_time = 0
        credit_card_called_cnt = 0
        credit_card_called_time = 0
        collection_cnt = 0
        collection_num = 0
        collection_caller_cnt = 0
        collection_caller_time = 0
        collection_called_cnt = 0
        collection_called_time = 0

        def contact_type(cnt):
            if cnt < 1:
                return '无通话记录'
            elif cnt < 5:
                return '很少被联系'
            else:
                return '经常被联系'

        def phone_status(cnt):
            if cnt < 10:
                return '数量很少'
            elif cnt < 50:
                return '数量较少'
            elif cnt < 100:
                return '数量较多'
            else:
                return '数量众多'

        for _ in result:
            if _['tag'].find('律师') != -1:
                lawyer_cnt += _['call_cnt']
                lawyer_num += 1
                lawyer_caller_cnt += _['caller_cnt']
                lawyer_caller_time += _['caller_call_time']
                lawyer_called_cnt += _['called_cnt']
                lawyer_called_time += _['called_call_time']

            elif _['tag'].find('法院') != -1:

                court_cnt += _['call_cnt']
                court_num += 1
                court_caller_cnt += _['caller_cnt']
                court_caller_time += _['caller_call_time']
                court_called_cnt += _['called_cnt']
                court_called_time += _['called_call_time']
            elif _['tag'].find('贷') != -1:

                loan_cnt += _['call_cnt']
                loan_num += 1
                loan_caller_cnt += _['caller_cnt']
                loan_caller_time += _['caller_call_time']
                loan_called_cnt += _['called_cnt']
                loan_called_time += _['called_call_time']
            elif _['tag'].find('银行') != -1:

                bank_cnt += _['call_cnt']
                bank_num += 1
                bank_caller_cnt += _['caller_cnt']
                bank_caller_time += _['caller_call_time']
                bank_called_cnt += _['called_cnt']
                bank_called_time += _['called_call_time']
            elif _['tag'].find('信用') != -1:

                credit_card_cnt += _['call_cnt']
                credit_card_num += 1
                credit_card_caller_cnt += _['caller_cnt']
                credit_card_caller_time += _['caller_call_time']
                credit_card_called_cnt += _['called_cnt']
                credit_card_called_time += _['called_call_time']

            elif _['tag'].find('催收') != -1:

                collection_cnt += _['call_cnt']
                collection_num += 1
                collection_caller_cnt += _['caller_cnt']
                collection_caller_time += _['caller_call_time']
                collection_called_cnt += _['called_cnt']
                collection_called_time += _['called_call_time']

        night_cnt = call_record[call_record['call_date'].dt.hour.isin([22, 23, 0, 1, 2, 3, 4, 5, 6, 7])].shape[0]
        circle_friends = call_record.groupby('other_area').size().sort_values().tail(1)
        f = {'attribution': circle_friends.index[0], 'call_cnt': circle_friends[0]}
        call_action = {
            'circle_friends': {
                'res': f['attribution'],
                'basis': '通话占比{}%'.format(round(f['call_cnt'] / all_cnt * 100, 2)),
            },
            'phone_status': {
                'res': f'{months}个月',
                'basis': f'根据号码[{mobile}]运营商提供的认证时间',
            },
            'shut_down_status': {
                'res': f'共关机{no_call_cnt}天',
                'basis': f'根据运营商详单数据，180天内关机{no_call_cnt}天',
            },
            'call_num': {
                'res': '数量正常（10 - 100)' if 10 < inter_cnt < 100 else '数量异常',
                'basis': '互通电话数{}, 比例{}%'.format(inter_cnt, round(inter_cnt / call_num * 100, 2)),
            },
            'aomen': {
                'res': f'{contact_type(aomen_cnt)}',
                'basis': f'主叫{aomen_caller_cnt}次，被叫{aomen_called_cnt}次' if aomen_cnt > 0 else '无通话记录',
            },
            '110': {
                'res': f'{contact_type(police_cnt)}',
                'basis': f'主叫{police_caller_cnt}次，被叫{police_called_cnt}次' if police_cnt > 0 else '无通话记录',
            },  # 与110通话情况
            '120': {
                'res': f'{contact_type(emergency_cnt)}',
                'basis': f'主叫{emergency_caller_cnt}次，被叫{emergency_called_cnt}次' if emergency_cnt > 0 else '无通话记录',
            },  # 与120通话情况
            'lawyer': {
                'res': f'{contact_type(lawyer_cnt)}',
                'basis': f'主叫{lawyer_caller_cnt}次共{lawyer_caller_time}秒，被叫{lawyer_called_cnt}次共{lawyer_called_time}秒，号码数{lawyer_num}' if lawyer_cnt > 0 else '无通话记录',
            },  # 与律师通话情况
            'court': {
                'res': f'{contact_type(court_cnt)}',
                'basis': f'主叫{court_caller_cnt}次共{court_caller_time}秒，被叫{court_called_cnt}次共{court_called_time}秒，号码数{court_num}' if court_cnt > 0 else '无通话记录',
            },  # 与法院通话情况
            'loan': {
                'res': f'{contact_type(loan_cnt)}',
                'basis': f'主叫{loan_caller_cnt}次共{loan_caller_time}秒，被叫{loan_called_cnt}次共{loan_called_time}秒，号码数{loan_num}' if loan_cnt > 0 else '无通话记录',
            },  # 与贷款通话情况
            'bank': {
                'res': f'{contact_type(bank_cnt)}',
                'basis': f'主叫{bank_caller_cnt}次共{bank_caller_time}秒，被叫{bank_called_cnt}次共{bank_called_time}秒，号码数{bank_num}' if bank_cnt > 0 else '无通话记录',
            },  # 与银行类通话情况
            'credit_card': {
                'res': f'{contact_type(credit_card_cnt)}',
                'basis': f'主叫{credit_card_caller_cnt}次共{credit_card_caller_time}秒，被叫{credit_card_called_cnt}次共{credit_card_called_time}秒，号码数{credit_card_num}' if credit_card_cnt > 0 else '无通话记录',
            },  # 与信用卡通话情况
            'collection': {
                'res': f'{contact_type(collection_cnt)}',
                'basis': f'主叫{collection_caller_cnt}次共{collection_caller_time}秒，被叫{collection_called_cnt}次共{collection_called_time}秒，号码数{collection_num}' if collection_cnt > 0 else '无通话记录',
            },  # 与催收类号码通话情况，
            'night_action': {
                'res': '很少夜间活动（低于20%)' if (night_cnt / all_cnt) < 0.2 else '经常在夜间活动（高于20%)',
                'basis': '占全天{}%'.format(round(night_cnt / all_cnt * 100, 2)),
            },
            'phone_call_status': {
                'res': f'{phone_status(call_num)}',
                'basis': f'通话号码数{call_num}；主叫{caller_cnt}次共{caller_time}秒；被叫{called_cnt}次共{called_time}秒',
            }
        }

        return result,call_action

    @staticmethod
    def basic_check_items(call_record, base_info):
        """基本信息校验点"""
        call_record = call_record.copy()
        check_name = base_info.get('name','')
        check_cardid = base_info.get('cardid','')
        form_name = base_info.get('form_name','')
        form_cardid = str(base_info.get('form_cardid',''))
        email = base_info.get('email','')
        address = base_info.get('address','')
        result = dict()
        result['address_valid'] = int(bool(re.match(
            r'^([\u4e00-\u9fa5]+(省|自治区)[\u4e00-\u9fa5]+市[\u4e00-\u9fa5]+([县,区]|.*)|[\u4e00-\u9fa5]+市[\u4e00-\u9fa5]+([县,区]|.*)|[\u4e00-\u9fa5]+(省|自治区)[\u4e00-\u9fa5]+(市|.*))$',
            address))) if address else -1
        result['idcard_valid'] = int(bool(re.match(
            r'(^[1-9]\d{5}(18|19|([23]\d))\d{2}((0[1-9])|(10|11|12))(([0-2][1-9])|10|20|30|31)\d{3}[0-9Xx]$)|(^[1-9]\d{5}\d{2}((0[1-9])|(10|11|12))(([0-2][1-9])|10|20|30|31)\d{2}[0-9Xx]$)',
            form_cardid))) if form_cardid else -1
        result['email_valid'] = int(
            bool(re.match(r'^[A-Za-z0-9\u4e00-\u9fa5]+@[a-zA-Z0-9_-]+(\.[a-zA-Z0-9_-]+)+$', email))) if email else -1
        name_pattern = '^' + re.sub(r'[^\u4e00-\u9fa5]+', '.+', check_name) + '$'
        result['name_match'] = int(bool(re.match(name_pattern, form_name))) if check_name else -1
        cardid_pattern = '^' + re.sub(r'[^0-9]+', '.+', check_cardid) + '$'
        result['idcard_match'] = int(bool(re.match(cardid_pattern, form_cardid))) if check_cardid else -1
        # 统计通话月数
        call_cnt_month = len(call_record.groupby(call_record['call_date'].apply(lambda x: x.month)))
        result['call_data_check'] = 1 if call_cnt_month >= 6 else 0 if call_cnt_month > 0 else -1

        # ===================
        # 号码沉默度

        call_score_6m = 0
        # 统计6个月通话次数
        call_cnt_6m = len(call_record)
        # 统计6个月通话天数
        call_cnt_day_6m = len(call_record.groupby(call_record['call_date'].apply(lambda x: x.dayofyear)))
        # 通话次数不大于25次并且通话天数不大于8天，通话评分为0
        if call_cnt_6m <= 50 and call_cnt_day_6m <= 16:
            call_score_6m = 0
        # 通话次数大于25次并且不大于2667次，或者通话天数大于8天并且不大于58天，通话评分为1
        elif call_cnt_6m <= 5200 and call_cnt_day_6m <= 106:
            call_score_6m = 1
        else:
            call_score_6m = 2
        silent_value_6m = 10 if call_score_6m == 0 else 3 if call_score_6m == 1 else 1 if call_score_6m == 2 else 6

        call_score_3m = 0
        # 统计3个月通话次数
        call_cnt_3m = len(call_record[call_record['call_date'] > month3_date])
        # 统计3个月通话天数
        call_cnt_day_3m = len(call_record[call_record['call_date'] > month3_date].groupby(
            call_record['call_date'].apply(lambda x: x.dayofyear)))
        # 通话次数不大于25次并且通话天数不大于8天，通话评分为0
        if call_cnt_3m <= 25 and call_cnt_day_3m <= 8:
            call_score_3m = 0
        # 通话次数大于25次并且不大于2667次，或者通话天数大于8天并且不大于58天，通话评分为1
        elif call_cnt_3m <= 2667 and call_cnt_day_3m <= 58:
            call_score_3m = 1
        else:
            call_score_3m = 2
        silent_value_3m = 10 if call_score_3m == 0 else 3 if call_score_3m == 1 else 1 if call_score_3m == 2 else 6
        result['silent_value_3m'] = silent_value_3m
        result['silent_value_6m'] = silent_value_6m
        return result

    @staticmethod
    def contact_area_data(call_record):
        """联系人区域汇总"""

        def handle(group):
            call_cnt = group.shape[0]
            call_time = group['call_long_hour'].sum()
            caller_cnt = group[group['call_type'] == 1].shape[0]
            caller_call_time = group[group['call_type'] == 1]['call_long_hour'].sum()
            called_cnt = group[group['call_type'] == 2].shape[0]
            called_call_time = group[group['call_type'] == 2]['call_long_hour'].sum()
            caller_per = caller_call_time / caller_cnt if caller_cnt else 0
            called_per = called_call_time / called_cnt if called_cnt else 0
            caller_cnt_per = caller_cnt / call_cnt if call_cnt else 0
            called_cnt_per = called_cnt / call_cnt if call_cnt else 0
            caller_time_per = caller_call_time / call_time if call_time else 0
            called_time_per = called_call_time / call_time if call_time else 0

            return pd.Series({
                # 地区名称
                'area': group.name,
                # 通话号码数
                'call_mobile_num': group['other_mobile'].nunique(),
                # 通话次数
                'call_cnt': call_cnt,
                # 通话时长（秒）
                'call_time': call_time,
                # 主叫次数
                'caller_cnt': caller_cnt,
                # 主叫时长（秒）
                'caller_call_time': caller_call_time,
                # 被叫次数
                'called_cnt': called_cnt,
                # 被叫时长（秒）
                'called_call_time': called_call_time,
                # 主叫平均时长（秒）
                'caller_avg': caller_per,
                # 被叫平均时长（秒）
                'called_avg': called_per,
                # 主叫次数占比
                'caller_cnt_per': caller_cnt_per,
                # 主叫时长占比
                'caller_time_per': caller_time_per,
                # 被叫次数占比
                'called_cnt_per': called_cnt_per,
                # 被叫时长占比
                'called_time_per': called_time_per,
            })

        df = call_record.groupby('other_area').apply(handle)
        return Report.to_python_obj_by_rows(df)

    @staticmethod
    def call_risk_analyze(call_record):
        """通话风险分析"""
        result = dict()

        one_months = call_record[(pd.datetime.now() - call_record['call_date']).dt.days < 30]
        result['1_months'] = pd.Series(dict(
            call_cnt=one_months.shape[0],
            call_cnt_avg=one_months.shape[0],
            call_time=one_months['call_long_hour'].sum(),
            caller_cnt=one_months[one_months["call_type"] == 1].shape[0],
            caller_time=one_months[one_months["call_type"] == 1]['call_long_hour'].sum(),
            called_cnt=one_months[one_months["call_type"] == 2].shape[0],
            called_time=one_months[one_months["call_type"] == 2]['call_long_hour'].sum(),
            contacts_cnt=one_months['other_mobile'].nunique(),
        )).to_dict()
        three_months = call_record[(pd.datetime.now() - call_record['call_date']).dt.days < 90]
        result['3_months'] = pd.Series(dict(
            # 近3月通话次数
            call_cnt=three_months.shape[0],
            # 近3月平均通话次数
            call_cnt_avg=three_months.shape[0] // 3,
            # 近3月通话时长（秒）
            call_time=three_months['call_long_hour'].sum(),
            # 近3月平均通话时长（秒）
            call_time_avg=three_months['call_long_hour'].sum() // 3,
            # 近3月主叫通话次数
            caller_cnt=three_months[three_months["call_type"] == 1].shape[0],
            # 近3月主叫月均通话次数
            caller_cnt_avg=three_months[three_months["call_type"] == 1].shape[0] // 3,
            # 近3月主叫通话时长
            caller_time=three_months[three_months["call_type"] == 1]['call_long_hour'].sum(),
            # 近3月主叫月均通话时长
            caller_time_avg=three_months[three_months["call_type"] == 1]['call_long_hour'].sum() // 3,
            # 近3个月被叫通话次数
            called_cnt=three_months[three_months["call_type"] == 2].shape[0],
            # 近3月被叫月均通话次数
            called_cnt_avg=three_months[three_months["call_type"] == 2].shape[0] // 3,
            # 近3月被叫通话时长
            called_time=three_months[three_months["call_type"] == 2]['call_long_hour'].sum(),
            # 近3月被叫月均通话时长
            called_time_avg=three_months[three_months["call_type"] == 2]['call_long_hour'].sum() // 3,
            contacts_cnt=three_months['other_mobile'].nunique(),
        )).to_dict()
        six_months = call_record[(pd.datetime.now() - call_record['call_date']).dt.days < 180]
        result['6_months'] = pd.Series(dict(
            call_cnt=six_months.shape[0],
            call_cnt_avg=six_months.shape[0] // 6,
            call_time=six_months['call_long_hour'].sum(),
            call_time_avg=six_months['call_long_hour'].sum() // 6,
            caller_cnt=six_months[six_months["call_type"] == 1].shape[0],
            caller_cnt_avg=six_months[six_months["call_type"] == 1].shape[0] // 6,
            caller_time=six_months[six_months["call_type"] == 1]['call_long_hour'].sum(),
            caller_time_avg=six_months[six_months["call_type"] == 1]['call_long_hour'].sum() // 6,
            called_cnt=six_months[six_months["call_type"] == 2].shape[0],
            called_cnt_avg=six_months[six_months["call_type"] == 2].shape[0] // 6,
            called_time=six_months[six_months["call_type"] == 2]['call_long_hour'].sum(),
            called_time_avg=six_months[six_months["call_type"] == 2]['call_long_hour'].sum() // 6,
            contacts_cnt=six_months['other_mobile'].nunique(),
        )).to_dict()
        return result

    @staticmethod
    def travel_record_analyze(call_record):
        """用户出行记录分析"""

        # 居住地
        living_place_series = \
            call_record[((call_record['call_date'].dt.hour >= 0) & (call_record['call_date'].dt.hour < 9)) | (
                    (call_record['call_date'].dt.hour >= 18) & (call_record['call_date'].dt.hour < 24))].groupby(
                'call_area').size().sort_values()
        location = living_place_series.index[-1] if not living_place_series.empty else ''

        # 添加首尾的临界值，为了让首尾的异地通话能算出行记录
        df = call_record.sort_values(by='call_date')
        first_location = df.loc[df.index[0],'call_area']
        if first_location != location:
            first_line = df.loc[df.index[0]].copy()
            first_line['call_area'] = '未知'
            first_line['call_date'] = first_line['call_date'] - pd.Timedelta('1 days')
            df = df.append(first_line,ignore_index=True)
            df = df.sort_values(by='call_date')
        last_location = df.loc[df.index[-1],'call_area']
        if last_location != location and last_location != location:
            last_line = df.loc[df.index[-1]].copy()
            last_line['call_area'] = '未知'
            last_line['call_date'] = last_line['call_date'] + pd.Timedelta('1 days')
            df = df.append(last_line,ignore_index=True)

        # 获取 打电话地点变更的记录(某地的最后一次，与某地的第一次)
        results = []
        ext = df.loc[df.index[0]]
        for _ in df.itertuples():
            if _.call_area != ext.call_area:
                item = dict(departure=ext.call_area, destination=_.call_area,
                            departure_time=ext.call_date.strftime('%Y-%m-%d %H:%M:%S'),
                            destination_time=_.call_date.strftime('%Y-%m-%d %H:%M:%S'),
                            day_type='双休日' if _.call_date.dayofweek in [5, 6] else '工作日'
                            )
                results.append(item)
            ext = _

        if not results: return []
        # 取出发地的最后一次通话和旅行地的最后一次通话时间
        # 排除目的地为居住地的旅游数据，根据上面的记录算出出行记录
        ext = results[0]
        new_results = []
        for _ in results:
            if _['departure'] == ext['destination']:
                destination = _['departure']
                departure_time = ext['departure_time']
                destination_time = _['departure_time']
                departure = ext['departure']
                # 判断时间段内有没有周末·
                time_list = pd.Series(pd.date_range(start=pd.to_datetime(departure_time),
                                                    end=pd.to_datetime(destination_time), freq='D'))
                time_type_list = [Report.get_date_type(_time) for _time in time_list]
                if '2' in time_type_list:
                    day_type = '法定节假日'
                if '2' not in  time_type_list and '1' in time_type_list:
                    day_type = '双休日'
                if '2' not in  time_type_list and '1' not in time_type_list:
                    day_type = '工作日'

                # # # 判断出发当天是不是周末
                # day_type_num = Report.get_date_type(departure_time)
                # if '2' in day_type_num:
                #     day_type = '法定节假日'
                # if '1' in day_type_num:
                #     day_type = '双休日'
                # if '0' in day_type_num:
                #     day_type = '工作日'

                new_results.append(dict(
                    # 目的地
                    destination=destination,
                    # 出发时间
                    departure_time=departure_time,
                    # 返回时间
                    destination_time=destination_time,
                    # 出发地
                    departure=departure,
                    # 时候有节假日
                    day_type=day_type
                ))
            ext = _

        return new_results


    def gen_report(self):
        # 个人信息
        self.report['personal_info'] = self.personal_info(self.base_info)
        # 手机号信息
        self.report['mobile_basic_info'] = self.mobile_basic_info(self.base_info,self.call_record)
        # 账户信息
        self.report['mobile_account_info'] = self.mobile_account_info(self.base_info)
        # 账单信息
        self.report['bill_info'] = self.bill_info(self.bill)
        # 通话详单和用户行为检测
        self.report['contact_detail'], self.report['contact_action']= self.call_and_action_data(self.base_info, self.call_record)
        # 基本信息校验点
        self.report['basic_check_items'] = self.basic_check_items(self.call_record, self.base_info)
        # 联系人区域汇总
        self.report['contact_area_data'] = self.contact_area_data(self.call_record)
        # 通话风险分析
        self.report['call_risk_analyze'] = self.call_risk_analyze(self.call_record)
        # 出行记录分析
        self.report['travel_record_analyze'] = self.travel_record_analyze(self.call_record)
        return self.report


def main(data, _encode=False):

    basicInfo = data['basicInfo']
    billRecords = data['billRecords']
    callRecords = data['callRecords']

    # 增加callRecords的other_areas字段
    for call in callRecords:
        try:
            _find = PHONE_FIND.find(call['other_mobile'])
            attribution = _find['province'] + _find['city']
        except Exception:
            attribution = '全国'
        call["other_area"] = attribution

    # 生成报表
    obj = Report(base_info=basicInfo, bill=billRecords, call_record=callRecords)
    res = obj.gen_report()
    #添加充值记录报表
    res.update({'pay_records': data.get('payRecords','')})

    # 返回报表
    if _encode:
        return json.dumps(res).encode(_encode)
    return res



if __name__ == '__main__':
    Report.get_date_type(datetime.datetime.now())
    # with open('constant/sample.json', encoding='utf-8') as f:
    #     data = json.loads(f.read())['data']
    # print(json.dumps(main(data)))