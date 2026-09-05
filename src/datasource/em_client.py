"""东财数据源(APK主力源)：全市场快照+历史数据线，纯requests零依赖"""
导入请求请求
将熊猫作为pd导入pandas作为PD
从罗古鲁导入记录器罗古鲁进口记录器

UA={"用户代理"："Mozilla/5。0(Linux；Android12)AppleWebKit/537。36"}{"用户代理"："Mozilla/5。0(Linux；Android12)AppleWebKit/537。36"}

# ============ ① 全市场快照（漏斗第一层）============
snap_URL="https://82.push2.eastmoney.com/api/qt/clist/get""https://82.push2.eastmoney.com/api/qt/clist/get"
snap_FIELDS="f12，F14、F2、F3、F5、F6、F8、F9、F10、F20、F21、F22、F24、F25、F62""f12、F14、F2、F3、F5、F6、F8、F9、F10、F20、F21、F22、F24、F25、F62"
#f12代码f14名称f2最新价f3涨跌幅f5成交量(手)f6成交量f8换手率
#f9市盈率f10量比f20总市值f21流通市值f22涨速f24近60日涨幅f25年初至今f62主力净流入

定义fetch_market_snapshot(include_bse:bool=False)->pd。DataFrame:fetch_market_snapshot(include_bse:bool=False)->pd.DataFrame：
"""一次接口拉沪深全市场（默认不含北交所），~5400 只，约 8-15 秒""""""一次接口拉沪深全市场（默认不含北交所），~5400 只，约 8-15 秒"""
FS="m:0+t:6,m:0+t:80,m:1+t:2,m:1+t:23""m:0+t:6,m:0+t:80,m:1+t:2,m:1+t:23"
如果包含(_B)：如果包括_bse：
FS+=",m:0+t:81,m:0+t:81+s:2048"",m:0+t:81,m:0+t:81+s:2048"
rows，pn=[]，1[]，1
当为True时：while True：
params={{
"pn"：pn，"pz"：500，"po"：1，"np"：1，"pn"：pn，"pz"：500，"po"：1，"np"：1，
"FLTT"：2，"INVT"：2，"fid"："f12"，"FLTT"：2，"INVT"：2，"fid"："f12"，
"fs"：fs，"fields"：SNAP_FIELDS，"fs"：fs，"fields"：SNAP_FIELDS，
        }
R=请求.get(SNAP_URL，params=params，header=UA，timeout=20)get(SNAP_URL，params=params，header=UA，timeout=20)
r.aise_for_status()raise_for_status()
data=r.Json()。get("data")或{}json().get("data")或{}
diff=data.get("diff")或[]get("diff")或[]
如果没有差异：如果没有差异：
打破打破
rows.extend(diff)extend(diff)
total=data.get("total"，0)get("total"，0)
如果len(rows)>=total或pn>20：如果len(rows)>=total或pn>20：
打破打破
PN+=11
DF=pd.DataFrame(行)DataFrame(行)
如果df.mpty：如果df.mpty：
返回dfreturn df
DF=df。重命名(columns={"f12"："symbol"，"f14"："名称"，"f2"："price"，重命名(columns={"f12"："符号"，"f14"："名称"，"f2"："价格"，
"f3"："pct_chg"，"f6"："金额"，"f8"："营业额"，"F3"："pct_chg"，"f6"："金额"，"f8"："营业额"，
"f9"："pe"，"f10"："vol_ratio"，"f20"："total_mv"，"f9"："pe"，"f10"："vol_ratio"，"f20"："total_mv"，
"F21"："float_mv"，"f22"："speed"，"F21"："float_mv"，"f22"："speed"，
"f24"："pct_60d"，"F25"："pct_ytd"，"f24"："pct_60d"，"F25"："pct_ytd"，
"F62"："main_net_inflow"})"F62"："main_net_inflow"})
对于df.columns中的c:for c in df.columns：
如果c不在("符号"、"名称")中：如果c不在("符号"、"名称")中：
DF[c]=pd.to_numeric(df[c]，错误="强制")[c]=pd.to_numeric(df[c]，errors="cerce")
DF["symbol"]=df["symbol"].astype(str).str.zFill(6)["符号"]=df["symbol"].astype(str).str.zFill(6)
DF["is_st"]=df["name"].字符串包含("ST"，na=False)["is_st"]=df["name"].字符串包含("ST"，na=False)
返回dfreturn df

# ============ ② 历史日线（漏斗第三层，增量）============
Kline_URL="https://push2his.eastmoney.com/api/qt/stock/kline/get""https://push2his.eastmoney.com/api/qt/stock/kline/get"

Def_secid(符号：str)->str：_secid(symbol:str)->str：
如果symbol.startswith(("6"，"9"))，则返回f"1.{symbol}"，否则返回f"0".{symbol}"返回F"1.{symbol}"if symbol.startswith(("6"，"9"))else f"0.{symbol}"

Def fetch_daily(符号：str，开始：str，结束：str，FQT:int=1)->pd.DataFrame:fetch_daily(符号：str，开始：str，结束：str，FQT:int=1)->pd.DataFrame：
"""东财日线。 FQT:0不复权1前复权2后复权""""""东财日线。 FQT:0不复权1前复权2后复权"""
params={{
"secid"：_secid(符号)，"secid""：_secid(符号)，
"fields1"："f1，f2，f3，f4，f5，f6"，"fields1"："f1，f2，f3，f4，f5，f6"，
"fields2"："f51，F52，F53，F54，F55，F56，57层，F58、F59、F60、F61""fields2"："f51、F52、F53、F54、F55、F56、F57、F58、F59、F60、F61"
"KLT"：101，"FQT"：FQT，"KLT"：101，"FQT"：FQT，
“乞求”：开始。替换("-"，"")，"end"：结束.替换("-"，"")，"beg"：start.replace ("-"，"")，"end"： end.replace("-"，"")，
    }
尝试：尝试：
R=请求.get(KLINE_URL，params=params，header=UA，timeout=15)get(KLINE_URL，params=params，header=UA，timeout=15)
r.aise_for_status()raise_for_status()
KL=(r.JSON().get("数据")或{})。get("klines")或[](r.json()).get("数据")或{}.get("klines")或[]
例外情况除外，如E：例外情况除外e：
logger.warning(f"EM日线失败{symbol}：{e}")warning(f"EM日线失败{symbol}：{e}")
return pd.DataFrame()return pd.DataFrame()
如果不是KL：如果不是kl：
return pd.DataFrame()return pd.DataFrame()
Rec=[x.split("，")，单位：KL][x.split("，")for x in kl]
DF=pd.DataFrame(rec，columns=["日期"，"开"，"关"，"高"，"低"，DataFrame(rec，columns=["日期"，"开"，"关"，"高"，"低"，
"体积"，"量"，"幅度"，"体积"，"量"，"振幅"，
"pct_chg"，"change"，"curnover"])"pct_chg"，"change"，"curnover"])
对于df.columns[1：]中的c:for c in df.columns[1：]：
DF[c]=pd.to_numeric(df[c]，错误="强制")[c]=pd.to_numeric(df[c]，errors="cerce")
DF["date"]=pd.to_datetime(df["date"])["date"]=pd.to_datetime(df["date"])
DF["符号"]=符号["符号"]=符号
返回DF[["symbol"，"date"，"open"，"high"，"low"，"close"，return DF[["symbol"，"date"，"open"，"high"，"low"，"close"，
“成交量”、“金额”、"PCT_chg"、“营业额”]]"成交量"，"金额"，"PCT_chg"，"营业额"]]

Def fetch_name(符号：str)->str:fetch_name(symbol:str)->str：
尝试：尝试：
R=requests.get(get(
"https://push2.eastmoney.com/api/qt/stock/get"，"https://push2.eastmoney.com/api/qt/stock/get"，
params={"secid"：_secid(符号)，"字段"："F58"}，{"secid"：_secid(符号)，"字段"："F58"}，
标头=UA，超时=10)10)
return r.json().get("data"，{}).get("F58"，符号)
例外：例外：
返回符号返回符号
