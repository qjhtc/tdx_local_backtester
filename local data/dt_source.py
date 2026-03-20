import pandas as pd
import os
from pathlib import Path
import baostock as bs
from datetime import datetime, timedelta
from tqdm import tqdm

# --- 路径配置 ---
BASE_DIR = Path(__file__).resolve().parent
SOURCE_TXT_DIR = os.path.join(BASE_DIR, "tdx a-shr data")
MASTER_PARQUET = str(BASE_DIR / "a_shr_data_master.parquet")
print(f"✅ 已成功定位数据库: {MASTER_PARQUET}")

def initialize_master_file():
    """将所有 TXT 转换为一个大的 Parquet 文件"""
    files = [f for f in os.listdir(SOURCE_TXT_DIR) if f.endswith('.txt')]
    all_data = []

    print(f"正在读取 {len(files)} 个 TXT 文件并合并...")
    for f in tqdm(files):
        file_path = os.path.join(SOURCE_TXT_DIR, f)
        try:
            # 1. 提取首行name
            with open(file_path, 'r', encoding='gbk') as file:
                first_line = file.readline().strip()
                parts = first_line.split(' ')
                code, name = parts[0], parts[1]

            # 2. 读取数据
            df = pd.read_csv(file_path, skiprows=2, sep='\t', header=None,
                             names=['date', 'open', 'high', 'low', 'close', 'volume', 'amount'],
                             engine='python', encoding='gbk', skipfooter=1)
            
            if df.empty: continue
            
            # 3. 规范化
            df['date'] = pd.to_datetime(df['date'], format='%Y%m%d').dt.strftime('%Y-%m-%d')
            df['code'] = code
            df['name'] = name
            all_data.append(df)
        except:
            continue

    if all_data:
        master_df = pd.concat(all_data, ignore_index=True)
        # 排序：先按code，再按date。这对于后续计算均线至关重要
        master_df = master_df.sort_values(['code', 'date'])
        master_df.to_parquet(MASTER_PARQUET, index=False, compression='snappy')
        print(f"初始化完成！文件保存至: {MASTER_PARQUET}")
    else:
        print("未找到有效数据。")

def incremental_update_baostock():
    """基于 Master Parquet 进行增量更新"""
    if not os.path.exists(MASTER_PARQUET):
        print("Master 文件不存在，请先执行初始化。")
        return

    # 1. 读取现有大表
    print("正在加载本地数据库...")
    master_df = pd.read_parquet(MASTER_PARQUET)
    
    # 2. 登录 BaoStock
    bs.login()       
    today = datetime.now().strftime("%Y-%m-%d")
    
    # 统计变量
    success_count = 0
    fail_count = 0
    up_to_date_count = 0 # 最终date为今天的计数
    new_records_total = 0
    
    new_records = []

    # 3. 按code分组，找到每只股票需要补齐的起始date
    stock_groups = master_df.groupby(['code', 'name'])
    print(f"开始检查 {len(stock_groups)} 只股票的增量数据...")

    for (code, name), group in tqdm(stock_groups):
        last_date = pd.to_datetime(group['date']).max()
        last_date_in_db = pd.to_datetime(group['date']).max()
        start_date = (last_date + timedelta(days=1)).strftime("%Y-%m-%d")

        if start_date > today: 
            up_to_date_count += 1
            continue

        # 格式转换
        bs_code = f"sh.{code}" if code.startswith('6') else f"sz.{code}"
        
        #北交所code格式转换，baostock目前不支持
        #if code.startswith('8') or code.startswith('4') or code.startswith('9'): bs_code = f"bj.{code}"

        # 抓取缺失数据 (adjustflag=2 为前复权,adjustflag=1 为后复权)
        rs = bs.query_history_k_data_plus(
            bs_code, "date,open,high,low,close,volume,amount",
            start_date=start_date, end_date=today, 
            frequency="d", adjustflag="1"
        )

        # 判断更新是否成功
        if rs.error_code != '0':
            print(f"\n[!] {code} 更新失败: {rs.error_msg}")
            fail_count += 1
            continue
            
        # 4. 解析数据    
        data_list = []
        while rs.next():
            data_list.append(rs.get_row_data())

        if data_list:
            df_new = pd.DataFrame(data_list, columns=['date', 'open', 'high', 'low', 'close', 'volume', 'amount'])
            df_new['code'] = code
            df_new['name'] = name
            # 类型转换
            for col in ['open', 'high', 'low', 'close', 'volume', 'amount']:
                df_new[col] = pd.to_numeric(df_new[col])
            
            new_records.append(df_new)
            new_records_total += len(df_new)
        
        # 检查更新后的最后date是否为今天
            final_date = df_new['date'].iloc[-1]
            if final_date == today:
                up_to_date_count += 1
            success_count += 1
        else:
            # 虽然没新数据（可能停牌或未close），但原有数据如果就是今天，也算达标
            if last_date_in_db.strftime("%Y-%m-%d") == today:
                up_to_date_count += 1
            success_count += 1
            
    # 4. 合并并存回
    if new_records:
        updated_df = pd.concat([master_df] + new_records, ignore_index=True)
        updated_df = updated_df.sort_values(['code', 'date']).drop_duplicates(subset=['code', 'date'])
        updated_df.to_parquet(MASTER_PARQUET, index=False)
        print(f"增量更新完成，新增 {len(pd.concat(new_records))} 行数据。")
    else:
        print("所有数据已是最新。")

    bs.logout()

# --- 最终统计报告 ---
    print("\n" + "="*40)
    print(f"📊 增量更新统计报告 ({today})")
    print("-" * 40)
    print(f"· 尝试更新股票数: {len(stock_groups)}")
    print(f"· 更新成功 (含无需更新): {success_count + (len(stock_groups) - success_count - fail_count)}")
    print(f"· 更新失败 (网络/code错误): {fail_count}")
    print(f"· 新增数据条数: {new_records_total}")
    print(f"· 最终date为今日({today})的条目数: {up_to_date_count}")
    print("-" * 40)
    
    if up_to_date_count < len(stock_groups) * 0.8:
        print("⚠️ 提示：大部分数据未达到今日，请确认是否已close(16:00后)或今日为节假日。")
    else:
        print("✅ 数据已同步至最新交易日。")
    print("="*40)

if __name__ == "__main__":
    # 第一次运行请取消下面这行的注释
    #initialize_master_file()
    
    # 日常维护运行这行
    incremental_update_baostock()