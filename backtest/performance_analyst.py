import pandas as pd
import matplotlib.pyplot as plt
import io
import akshare as ak
import numpy as np
from datetime import datetime

class PerformanceAnalyst:
    @staticmethod
    def process_trades(df):
        if df.empty: return df
        df = df.copy()
        df['pnl_pct'] = np.nan
        sell_mask = df['action'] == "SELL"
        # 计算单笔盈亏百分比
        df.loc[sell_mask, 'pnl_pct'] = (df['price'] / df['buy_price'] - 1) * 100
        return df

    @staticmethod
    def save_excel_report(df, strategy_name, start_input, end_input):
        """将交易记录、统计数据和包含对比曲线及分布图的图片全部写入 XLSX"""
        s_str = start_input.replace("-", "")
        e_str = end_input.replace("-", "")
        timestamp = datetime.now().strftime("%H%M%S")
        file_name = f"{strategy_name}_{s_str}_{e_str}_{timestamp}.xlsx"

        # 1. 准备统计数据 (Summary)
        sells = df[df['action'] == "SELL"].copy()
        win_rate = (sells['pnl_pct'] > 0).mean() * 100 if not sells.empty else 0
        avg_ret = sells['pnl_pct'].mean() if not sells.empty else 0
        
        summary_df = pd.DataFrame({
            'Metric': ['Strategy Name', 'Test Period', 'Total Trades', 'Win Rate (%)', 'Avg Return (%)'],
            'Value': [strategy_name, f"{start_input} to {end_input}", len(sells), f"{win_rate:.2f}", f"{avg_ret:.2f}"]
        })

        # 2. 生成包含对比曲线和分布图的综合图片 (2 Subplots)
        fig = PerformanceAnalyst._generate_combined_plot(df, strategy_name, start_input, end_input)
        img_data = io.BytesIO()
        # 增加 DPI 以保证在 Excel 中清晰
        fig.savefig(img_data, format='png', bbox_inches='tight', dpi=120)
        plt.close(fig)

        # 3. 写入 Excel
        # 确保已安装 xlsxwriter: pip install xlsxwriter
        with pd.ExcelWriter(file_name, engine='xlsxwriter') as writer:
            # Sheet 1: 交易日志
            df.to_excel(writer, sheet_name='Trade_Logs', index=False)
            
            # Sheet 2: 统计摘要与图表
            summary_df.to_excel(writer, sheet_name='Summary', index=False)
            
            worksheet = writer.sheets['Summary']
            # 将图片插入到 Summary 表格右侧 (D2 单元格位置)
            # 你可以调整此位置，确保不遮挡数据
            worksheet.insert_image('D2', 'performance_report.png', {'image_data': img_data})

        print(f"✅ Full Excel report (data, stats, chart) saved: {file_name}")

    @staticmethod
    def _generate_combined_plot(df, strategy_name, start_input, end_input):
        """内部绘图逻辑：生成双子图报告 (收益对比 + 盈亏分布)"""
        sells = df[df['action'] == "SELL"].copy()
        sells['date'] = pd.to_datetime(sells['date'])
        sells = sells.sort_values('date')
        
        # --- 创建双子图布局 ---
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))

        # =========================================================
        # 图 1 (左)：累计收益对比曲线 (Strategy vs CSI 300)
        # =========================================================
        # 计算策略累计收益 (假设20个持仓位，资金利用率 1/20)
        daily_pnl = sells.groupby('date')['pnl_pct'].sum() / 20
        strat_cum_ret = (1 + daily_pnl / 100).cumprod() - 1
        strat_pct = strat_cum_ret * 100

        # 绘制策略曲线
        ax1.plot(strat_pct.index, strat_pct.values, label=f'Strategy: {strategy_name}', color='#d62728', lw=2.5)

        # 获取并绘制沪深300基准
        try:
            print(f"🌐 Fetching CSI 300 from Eastmoney (EM)...")
            # 接口改为东方财富源，通常更稳定
            bench_df = ak.stock_zh_index_daily_em(symbol="sh000300")
            bench_df['date'] = pd.to_datetime(bench_df['date'])
            
            # 严格对齐日期区间
            mask = (bench_df['date'] >= pd.to_datetime(start_input)) & \
                   (bench_df['date'] <= pd.to_datetime(end_input))
            bench_sub = bench_df.loc[mask].sort_values('date').copy()
            
            if not bench_sub.empty:
                # 归一化基准：以区间第一天为基准点 (0%)
                first_close = bench_sub['close'].iloc[0]
                bench_pct = (bench_sub['close'] / first_close - 1) * 100
                ax1.plot(bench_sub['date'], bench_pct, label='Benchmark: CSI 300', color='#7f7f7f', ls='--', alpha=0.8)
        except Exception as e:
            print(f"⚠️ Warning: Could not plot CSI300 benchmark due to: {e}")

        # 左图装饰
        ax1.set_title(f"Cumulative Return Comparison", fontsize=13)
        ax1.set_xlabel("Date")
        ax1.set_ylabel("Return (%)")
        ax1.axhline(0, color='black', lw=0.8)
        ax1.legend()
        ax1.grid(True, linestyle=':', alpha=0.5)

        # =========================================================
        # 图 2 (右)：单笔交易盈亏分布直方图
        # =========================================================
        # 移除 NaN 值
        pnl_data = sells['pnl_pct'].dropna()
        
        if not pnl_data.empty:
            # 自动计算合适的 Bins 数量
            n_bins = min(max(int(len(pnl_data)/5), 10), 50)
            
            # 绘制直方图
            n, bins, patches = ax2.hist(pnl_data, bins=n_bins, color='#1f77b4', edgecolor='white', alpha=0.8)
            
            # 标记盈亏平衡线
            ax2.axvline(0, color='red', linestyle='-', linewidth=1.5, label='Break Even')
            
            # 为盈利和亏损的柱子填充不同的颜色 (可选，增强视觉)
            for patch, left_edge in zip(patches, bins):
                if left_edge < 0:
                    patch.set_facecolor('#d62728') # 亏损红色 (或橙色)
                else:
                    patch.set_facecolor('#2ca02c') # 盈利绿色
                    
            # 右图装饰
            ax2.set_title(f"Individual Trade PnL Distribution (%)", fontsize=13)
            ax2.set_xlabel("Return %")
            ax2.set_ylabel("Trade Count")
            ax2.grid(True, axis='y', linestyle=':', alpha=0.5)
            
            # 打印最大/最小盈亏
            print(f"Max Single Profit: {pnl_data.max():.2f}%")
            print(f"Max Single Loss:   {pnl_data.min():.2f}%")
        else:
            ax2.set_title("No PnL data to plot")

        # 整体布局优化
        fig.suptitle(f"Backtest Analysis Report: {strategy_name} ({start_input} to {end_input})", fontsize=15, y=1.02)
        plt.tight_layout()
        
        return fig