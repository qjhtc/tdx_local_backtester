# tdx_local_backtester
一个AI写的，基于通达信数据导出和Baostock的A股策略回测框架

数据源：来自于通达信数据导出-高级导出。导出后会获得无数以证券代码命名的txt文件，放在local data\tdx a-shr data文件夹下。

数据整理：运行local data\dt_source.py。首次运行要把代码最下面initialize_master_file()前的注释符号去掉。

回测框架：回测主要是读取策略生成的买入和卖出信号，现在瞎搞了一个策略生成买入信号，卖出信号则由风控模块生成，以后还要检查来自于交易策略的卖出信号

买入信号：buy_signals[['date', 'code', 'name', 'signals']]

卖出信号：sell_signals[['date', 'code', 'name', 'signals', 'reason']]

后面就是回测算收益，生成收益曲线和分布图，存到一个excel文件里
