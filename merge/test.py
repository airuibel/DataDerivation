import pandas as pd


pd.set_option('display.max_rows', None)
pd.set_option('display.max_columns', None)
pd.set_option('display.width', 10000)


df1 = pd.read_csv("result.csv",low_memory=False)
df2 = pd.read_csv("label.csv",low_memory=False)
df2 = df2.drop(columns=["start_time","name","idcard"])


df_feature_label=df2.merge(df1,on='mobile',how='inner')
print(df_feature_label.columns)
print(df_feature_label["mobile"].duplicated(keep='first').value_counts())
print(df_feature_label.shape)

df_feature_label.to_csv("last_result.csv")