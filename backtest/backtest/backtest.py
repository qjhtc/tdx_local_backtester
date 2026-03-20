import sys
import pandas as pd
from pathlib import Path
from datetime import datetime

# --- 1. 路径与环境配置 ---
BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent

STRATEGY_PATH = PROJECT_ROOT / "strategy"
if str(STRATEGY_PATH) not in sys.path:
    sys.path.append(str(STRATEGY_PATH))

DATA_PATH = PROJECT_ROOT / "local data" / "a_shr_data_master.parquet"

from engine_core import BacktestEngine
from performance_analyst import PerformanceAnalyst
from risk_manager import RiskManager
from slbull_strategy import SLBullStrategy

def main():
    # --- 2. 用户交互 ---
    print("="*30)
    print("📈 SLBull 全市场回测系统")
    print("="*30)
    start_input = input("开始date (YYYY-MM-DD): ").strip()
    end_input = input("结束date (YYYY-MM-DD): ").strip()
    
    # --- 3. 数据加载与指标计算 ---
    if not DATA_PATH.exists():
        print(f"❌ 错误：找不到数据库 {DATA_PATH}")
        return

    full_df = pd.read_parquet(DATA_PATH)
    full_df['date'] = pd.to_datetime(full_df['date']).dt.strftime('%Y-%m-%d')
    full_df = full_df.sort_values(['code', 'date'])

    # 预计算必要指标
    print("🛠️ 正在预计算 5/10/20 日均线...")
    full_df['ma5'] = full_df.groupby('code')['close'].transform(lambda x: x.rolling(5).mean())
    full_df['ma10'] = full_df.groupby('code')['close'].transform(lambda x: x.rolling(10).mean())
    full_df['ma20'] = full_df.groupby('code')['close'].transform(lambda x: x.rolling(20).mean())

    # 确定回测交易日序列
    all_days = sorted(full_df['date'].unique())
    target_days = [d for d in all_days if start_input <= d <= end_input]
    
    if not target_days:
        print("❌ 错误：指定区间无数据")
        return

    # --- 4. 初始化策略与引擎 ---
    strategy = SLBullStrategy(period=15, top_n=5)
    risk_ctrl = RiskManager(stop_loss_pct=0.10)
    engine = BacktestEngine(strategy, risk_ctrl, max_pos=20)

    # --- 5. 执行回测 ---
    raw_trades = engine.run(full_df, target_days)

    # --- 6. 结果处理与动态命名记录 ---
    analyst = PerformanceAnalyst()
    final_log = analyst.process_trades(raw_trades)
    
    if not final_log.empty:
        # 获取策略类名
        strat_name = strategy.__class__.__name__
        # 直接调用新方法，一键生成 Excel
        analyst.save_excel_report(final_log, strat_name, start_input, end_input)
        
        log_save_path = BASE_DIR
        
        print(f"\n✅ 回测完成！")
        print(f"📄 交易日志已保存至: {log_save_path.name}")

    else:
        print("\n ⚠️ 该区间内未触发任何交易信号。")

if __name__ == "__main__":
    main()