import pandas as pd
from tqdm import tqdm

class BacktestEngine:
    def __init__(self, strategy, risk_manager, max_pos=20):
        self.strategy = strategy
        self.risk_manager = risk_manager
        self.max_pos = max_pos
        self.portfolio = {}
        self.pending_buys = pd.DataFrame()
        self.pending_sells = pd.DataFrame()

    def run(self, full_df, test_days):
        # --- 核心优化：将 DataFrame 转换为按date分组的字典 ---
        print("⚡ 正在建立时间索引以加速回测...")
        # 预先 set_index 可以让后续 loc 速度提升 10 倍
        indexed_df = full_df.set_index(['date', 'code']).sort_index()
        # 按date拆分数据
        data_by_day = {day: group for day, group in full_df.groupby('date')}
        
        all_trades = []
        trade_days = test_days

        print(f"🚀 开始回测 (优化版): {trade_days[0]} 至 {trade_days[-1]}")
        for today in tqdm(trade_days):
            day_data = data_by_day.get(today, pd.DataFrame())
            if day_data.empty: continue
            
            # 建立name映射表，方便快速查找
            name_lookup = day_data.set_index('code')['name'].to_dict()
            price_lookup = day_data.set_index('code')['close'].to_dict()

            # --- 1. 执行卖出 (处理昨日卖出信号) ---
            if not self.pending_sells.empty:
                for _, row in self.pending_sells.iterrows():
                    code = row['code']
                    reason = row.get('reason', 'EXIT') # 获取卖出reason
                    if code in self.portfolio and code in price_lookup:
                        curr_price = price_lookup[code]
                        # 传入reason和正确的name
                        all_trades.append(self._create_trade_record(code, curr_price, today, "SELL", reason))
                        del self.portfolio[code]

            # --- 2. 执行买入 (处理昨日买入信号) ---
            if not self.pending_buys.empty:
                for _, row in self.pending_buys.iterrows():
                    if len(self.portfolio) >= self.max_pos: break
                    code = row['code']
                    # 修复：直接从当日数据获取name
                    name = name_lookup.get(code, row.get('name', 'Unknown'))
                    
                    if code not in self.portfolio and code in price_lookup:
                        curr_price = price_lookup[code]
                        self.portfolio[code] = {
                            'buy_price': curr_price, 
                            'name': name, 
                            'buy_date': today
                        }
                        all_trades.append(self._create_trade_record(code, curr_price, today, "BUY", "SIGNAL"))

            # --- 3. 产生明日信号 ---
            # 风险管理检查
            self.pending_sells = self.risk_manager.check_exit_signals(today, day_data, self.portfolio)
            
            # 只有席位不满才计算买入（最耗时的线性拟合在这里被保护）
            if len(self.portfolio) < self.max_pos:
                needed = self.max_pos - len(self.portfolio) + len(self.pending_sells)
                self.strategy.top_n = needed
                # 注意：策略类也需要优化，传入已经过滤好的 day_data
                self.pending_buys = self.strategy.generate_buy_signals(today, full_df, day_data)
            else:
                self.pending_buys = pd.DataFrame()

        return pd.DataFrame(all_trades)

    def _create_trade_record(self, code, price, date, action, reason="-"):
        # 统一从 portfolio 获取name，如果不存在（买入瞬间），则从临时变量中获取逻辑已写在 run 中
        return {
            'code': code,
            'name': self.portfolio[code]['name'] if code in self.portfolio else "Unknown",
            'date': date,
            'action': action,
            'price': price,
            'buy_price': self.portfolio[code]['buy_price'] if action == "SELL" else price,
            'reason': reason  # 新增列
        }