import pandas as pd
import numpy as np
from pathlib import Path

class SLBullStrategy:
    def __init__(self, period, top_n):
        self.period = period
        self.top_n = top_n

    def generate_buy_signals(self, current_date, full_df, day_data):
        # 直接使用传入的当日截面数据 day_data
        bull_df = day_data[
            (day_data['close'] > day_data['ma5']) & 
            (day_data['ma5'] > day_data['ma10']) & 
            (day_data['ma10'] > day_data['ma20'])
        ].copy()
        
        if bull_df.empty: return pd.DataFrame()

        # 进一步加速：只对 full_df 做一次按code的分组，缓存起来
        if not hasattr(self, '_groups'):
            self._groups = {code: group for code, group in full_df.groupby('code')}
        
        ranking_list = []
        for _, row in bull_df.iterrows():
            code = row['code']
            name = row['name']
            # 从缓存的组里直接提取历史切片，比 full_df[mask] 快 100 倍
            stock_history = self._groups.get(code)
            if stock_history is None: continue
            
            # 截取截至今日的历史窗口
            y = stock_history[stock_history['date'] <= current_date]['ma5'].tail(self.period).values
            
            if len(y) < self.period: continue
            
            # ... 线性拟合逻辑不变 ...
            
            # Min-Max 标准化
            y_min, y_max = y.min(), y.max()
            if y_max == y_min: continue
            y_norm = (y - y_min) / (y_max - y_min)
            
            x = np.arange(self.period)
            slope, intercept = np.polyfit(x, y_norm, 1)
            
            # 必须是上升趋势
            if slope > 0:
                r2 = np.corrcoef(x, y_norm)[0, 1]**2
                if r2 > 0.90:
                    mse = np.mean((y_norm - (slope * x + intercept))**2)
                    ranking_list.append({
                        'date': current_date,
                        'code': code,
                        'name': name,
                        'MSE': mse
                    })
        
        if not ranking_list:
            return pd.DataFrame()
            
        # 3. 按平整度(MSE)排序，取前 TopN
        buy_signals = pd.DataFrame(ranking_list).sort_values('MSE').head(self.top_n)
        buy_signals['信号'] = 'BUY'
        
        return buy_signals[['date', 'code', 'name', '信号']]