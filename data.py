from utils import Income, BalanceSheet, CashFlow, KeyMetrics, Period, Statements
from typing import Dict, List
import requests
from datetime import datetime
import redis
import json
import csv

DATE_FORMAT = '%Y-%m-%d'
REDIS_HOST_NAME = 'localhost'
REDIS_PORT = 6379
SYMBOLS_PATH = 'nasdaq_symbols.csv'

r = redis.Redis(
    host=REDIS_HOST_NAME,
    port=REDIS_PORT)

# SUPPORTED_STOCK_EXCHANGES = ['NASDAQ Capital Market', 'NASDAQ Global Market', 'NYSE', 'NYSE American', 'NYSE Arca',
#                              'NYSEArca', 'Nasdaq', 'Nasdaq Global Select', 'NasdaqCM', 'NasdaqGM', 'NasdaqGS',
#                              'New York Stock Exchange']

SUPPORTED_STOCK_EXCHANGES = ['NASDAQ Global Market', 'NYSE', 'NYSE American', 'NYSE Arca',
                             'NYSEArca', 'Nasdaq', 'Nasdaq Global Select', 'NasdaqGM', 'NasdaqGS',
                             'New York Stock Exchange']


def get_cached_url(url) -> Dict:
    """ Get URL from cache. If URL not in cache, get from source url and cache the response """
    try:
        resp = r.get(url)
        if resp is not None:
            return json.loads(resp)
    except redis.exceptions.ConnectionError:
        pass

    resp = requests.get(url).json()

    try:
        r.set(url, json.dumps(resp))
    except redis.exceptions.ConnectionError:
        pass

    return resp


def dict2income(d: Dict) -> Income:
    return Income(
        Date=d.get('date'),
        Revenue=d.get('Revenue'),
        CostOfRevenue=d.get('Cost of Revenue'),
        GrossProfit=d.get('Gross Profit'),
        RnDExpenses=d.get('R&D Expenses'),
        SGAExpense=d.get('SG&A Expense'),
        OperatingExpenses=d.get('Operating Expenses'),
        OperatingIncome=d.get('Operating Income'),
        InterestExpense=d.get('Interest Expense'),
        NetIncome=d.get('Net Income'),
        EBITDA=d.get('EBITDA'),
        EBIT=d.get('EBIT')
    )


def dict2balance_sheet(d: Dict) -> BalanceSheet:
    return BalanceSheet(
        Date=d.get('date'),
        CashAndCashEquivalents=d.get('Cash and cash equivalents'),
        ShortTermInvestments=d.get('Short-term investments'),
        Receivables=d.get('Receivables'),
        # Inventories=d.get('Inventories', ''),
        # TotalCurrentAssets=d.get('Total current assets'),
        PropertyPlantAndEquipmentNet=d.get('Property, Plant & Equipment Net'),
        GoodwillAndIntangibleAssets=d.get('Goodwill and Intangible Assets'),
        LongTermInvestments=d.get('Long-term investments'),
        TaxAssets=d.get('Tax assets'),
        TotalNonCurrentAssets=d.get('Total non-current assets'),
        TotalAssets=d.get('Total assets'),
        Payables=d.get('Payables'),
        ShortTermDebt=d.get('Short-term debt'),
        # LongTermDebt=d.get('Long-term debt'),
        TotalDebt=d.get('Total debt'),
        DeferredRevenue=d.get('Deferred revenue'),
        TaxLiabilities=d.get('Tax Liabilities'),
        DepositLiabilities=d.get('Deposit Liabilities'),
        TotalNonCurrentLiabilities=d.get('Total non-current liabilities'),
        TotalLiabilities=d.get('Total liabilities'),
        OtherComprehensiveIncome=d.get('Other comprehensive income'),
        RetainedEarnings=d.get('Retained earnings (deficit)'),
        TotalShareholdersEquity=d.get('Total shareholders equity'),
        Investments=d.get('Investments'),
        NetDebt=d.get('Net Debt'),
        OtherAssets=d.get('Other Assets'),
        OtherLiabilities=d.get('Other Liabilities'),
        TotalCurrentLiabilities=d.get('Total current liabilities'),
        CashAndShortTermInvestments=d.get('Cash and short-term investments'),
        InventoriesTotalCurrentAssets='',
    )


def dict2cash_flow(d: Dict) -> CashFlow:
    return CashFlow(
        Date=d.get('date'),
        #TODO: fill in
    )


def statements2url(statement: Statements) -> str:
    d = {
        Statements.Income: 'income-statement',
        Statements.BalanceSheet: 'balance-sheet-statement',
        Statements.CashFlow: 'cash-flow-statement'
    }
    return d[statement]


def get_financials(ticker: str, statement: Statements = Statements.Income,
                   period: Period = Period.Year) -> List[Income]:

    url = f'https://financialmodelingprep.com/api/v3/financials/{statements2url(statement)}/{ticker}/'
    if period == Period.Quarter:
        url += '?period=quarter'

    resp = get_cached_url(url)
    financial_list = []
    if statement == Statements.Income:
        financial_list = [dict2income(d) for d in resp['financials']]
    elif statement == Statements.BalanceSheet:
        financial_list = [dict2balance_sheet(d) for d in resp['financials']]
    elif statement == Statements.CashFlow:
        financial_list = [dict2cash_flow(d) for d in resp['financials']]

    financial_list.reverse()
    return financial_list


def get_ticker_list() -> List[str]:
    url = 'https://financialmodelingprep.com/api/v3/company/stock/list'
    ticker_list = []
    for x in get_cached_url(url)['symbolsList']:
        if x.get('exchange', None) in SUPPORTED_STOCK_EXCHANGES:
            name = x.get('name', '').lower()
            if name and 'fund' not in name and 'etf' not in name:
                ticker_list.append(x.get('symbol'))
    print(f'Number of supported stocks: {len(ticker_list)}')
    return ticker_list


def get_prices(ticker: str, start: datetime, end: datetime) -> List:
    # date format: 2018 - 03 - 12
    start_str = start.strftime('%Y-%m-%d')
    end_str = end.strftime('%Y-%m-%d')
    url = f'https://financialmodelingprep.com/api/v3/historical-price-full/{ticker}?from={start_str}&to={end_str}'
    resp = get_cached_url(url)
    return resp.get('historical', [])


def get_symbols():
    symbols = []
    nasdaq_symbol_pos = -1
    etf_pos = 4
    with open(SYMBOLS_PATH) as csvfile:
        reader = csv.reader(csvfile, delimiter='|')
        next(reader)
        for row in reader:
            if row[etf_pos] == "N":  # not an ETF
                symbols.append(row[nasdaq_symbol_pos])
    return symbols
