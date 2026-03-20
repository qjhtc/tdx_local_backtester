import pandas as pd

class RiskManager:
    def __init__(self, stop_loss_pct=0.10):
        self.stop_loss_pct = stop_loss_pct

    def check_exit_signals(self, current_date, full_df, current_portfolio):
        """
        核心任务：检查持仓是否触发 20日线卖出 或 10% 止损
        current_portfolio: 格式 {code: {'buy_price': 10.5, 'name': 'xxx'}}
        """
        day_data = full_df[full_df['date'] == current_date]
        sell_signals = []

        for code, info in current_portfolio.items():
            stock_stat = day_data[day_data['code'] == code]
            if stock_stat.empty: continue
            
            curr_close = stock_stat['close'].values[0]
            ma20 = stock_stat['ma20'].values[0]
            buy_price = info['buy_price']
            
            # 逻辑 A: 跌破 20 日均线
            if curr_close < ma20:
                sell_signals.append({'date': current_date, 'code': code, 'reason': 'MA20_EXIT'})
                continue
                
            # 逻辑 B: 强制止损 (10%)
            if (curr_close / buy_price - 1) <= -self.stop_loss_pct:
                sell_signals.append({'date': current_date, 'code': code, 'reason': 'STOP_LOSS'})

        return pd.DataFrame(sell_signals)