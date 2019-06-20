import xgboost as xgb
import pandas as pd
from sklearn.model_selection import train_test_split
import math

# pandas 设置
pd.set_option('display.max_rows', None)
pd.set_option('display.max_columns', None)
pd.set_option('display.width', 10000)


# 数据读取
df_feature = pd.read_csv("datafeature/success/datafeature.csv",low_memory=False)
df_label = pd.read_csv("dataset/label/label.csv",low_memory=False)
# 字段预删除
df_label  = df_label .drop(columns=["start_time","name","idcard"])


# 数据关联join
data=df_label .merge(df_feature,on='mobile',how='inner')
# print(df_feature_label.columns)
# print(df_feature_label["mobile"].duplicated(keep='first').value_counts())
# print(df_feature_label.shape)


#验证集,取样本10%
valid=data.tail(1000)
data=data.head(data.shape[0]-1000)


#去掉特征文件无关字段和标签字段
drop_columns=["name","idcard","mobile_state","email","level",
              # 需要独热编码的字段
              "living_city","friends_city",
              # 需要把bool值映射成1,0的字段
              "keep_touch_7day","keep_touch_1m","living_city_attribution","living_city_friends_city","living_city_birthplace",
              "label"]


#去掉特征文件无关字段
feature = list(data.columns)
for name in drop_columns:
    print(name)
    feature.remove(name)


#训练集和测试集划分
x_train, x_test, y_train, y_test = train_test_split(data[feature], data["label"], train_size=0.7, random_state=101)
dtrain = xgb.DMatrix(x_train[feature], label=y_train)
dtest = xgb.DMatrix(x_test[feature], label=y_test)


#参数设置
param = {'max_depth': 2, 'eta': 1, 'silent': 1, 'objective': 'binary:logistic'}
param['nthread'] = 4
param['eval_metric'] = 'auc'
evallist = [(dtest, 'eval'), (dtrain, 'train')]


#训练模型
num_round = 10
bst = xgb.train(param, dtrain, num_round, evallist)


#预测
ypred = bst.predict(dtest)


#分值转换
for i in range(ypred.size):
    test_score=int(math.log2((1-ypred[i])/ypred[i])*50+450)
    print(test_score)