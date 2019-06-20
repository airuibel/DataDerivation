import xgboost as xgb
import pandas as pd
from sklearn.model_selection import train_test_split
import math

# 数据读取
data = pd.read_csv("last_result.csv")


#去掉特征文件无关字段和标签字段
drop_columns=["name","idcard","mobile_state","email","living_city","friends_city",
              "keep_touch_7day","keep_touch_1m","living_city_attribution","living_city_friends_city",
              "living_city_birthplace","level","label"]

#去掉特征文件无关字段
feature = list(data.columns)
for name in drop_columns:
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