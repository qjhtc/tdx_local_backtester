# tdx_local_backtester
一个AI写的，基于通达信数据导出和Baostock的A股策略回测框架

数据源：来自于通达信数据导出-高级导出。导出后会获得无数以证券代码命名的txt文件，放在local data\tdx a-shr data文件夹下。

数据整理：运行local data\dt_source.py。首次运行要把代码最下面initialize_master_file()前的注释符号去掉。

回测框架：回测主要是读取策略生成的买入和卖出信号，现在瞎搞了一个策略生成买入信号，卖出信号则由风控模块生成，以后还要检查来自于交易策略的卖出信号

买入信号：buy_signals[['date', 'code', 'name', 'signals']]

卖出信号：sell_signals[['date', 'code', 'name', 'signals', 'reason']]

后面就是回测算收益，生成收益曲线和分布图，存到一个excel文件里

下面是AI写的readme

🚀 A-Share Quantitative Backtesting System (SLBull Strategy)

这是一个基于 Python 开发的高性能 A 股量化回测系统，专注于 趋势追踪 (Trend Following) 与 线性拟合评分 (MSE Scoring) 策略。系统支持 T+1 成交模拟、自动抓取沪深 300 基准对比，并生成一键式 Excel 综合分析报告。
✨ 核心特性 (Key Features)

    标准化数据处理：全链路采用英文 Schema (date, code, close, etc.)，兼容 Parquet 高速读取，彻底消除编码报错。

    T+1 回测引擎：严格模拟 A 股交易规则，支持多持仓位（20 仓）管理及自动名称匹配，杜绝未来函数。

    多维度风控：内置 MA20 技术止损与 -10% 硬止损逻辑。

    自动基准对比：通过 AkShare 实时调用东方财富数据源，获取沪深 300 (CSI 300) 指数进行 Alpha 对齐。

    全能 Excel 报告：生成包含交易日志、核心指标（胜率/均盈）以及**双子图报告（累计收益曲线 + 盈亏分布图）**的 .xlsx 文件。

🛠️ 环境要求 (Installation)

    克隆仓库：
    Bash

git clone https://github.com/你的用户名/你的项目名.git
cd 你的项目名

安装依赖：
Bash

    pip install pandas akshare xlsxwriter matplotlib tqdm numpy

📂 项目结构 (Project Structure)
Plaintext

├── backtest/
│   ├── backtest.py             # 回测启动主程序
│   ├── engine_core.py          # T+1 回测引擎核心
│   └── performance_analyst.py  # 业绩分析与 Excel 报告生成
├── strategy/
│   └── slbull_strategy.py      # SLBull 趋势拟合策略
├── local data/                 # 本地数据存放 (Parquet 格式)
├── .gitignore                  # 忽略大文件上传
└── README.md

🚀 快速上手 (Quick Start)

运行回测主程序并输入日期区间（如 2023-01-01 至 2024-01-01）：
Bash

python backtest/backtest.py

回测完成后，系统将在目录中生成名为 SLBullStrategy_起始日期_结束日期_时间戳.xlsx 的报告。
📊 报告展示 (Report Example)
Summary 分页包含：

    策略统计：总交易次数、胜率、平均盈亏。

    业绩曲线：策略累计净值与沪深 300 指数的直观对比。

    风险分布：单笔交易盈亏分布直方图，助你快速识别策略的风险特征（肥尾效应等）。

⚠️ 免责声明 (Disclaimer)

本系统仅用于量化研究与回测练习，不构成任何投资建议。股市有风险，入市需谨慎。
