import yfinance as yf
import pandas as pd
import numpy as np

class FinancialAnalysis:
    '''
    Fields:
    - self.stock_data stores the last 5 years of market data for stock with 1  
         day intervals
    - self.benchmark_data same as stock_data but for benchmark
    - self.info stores info for stock
    - self.rs stores the expected return on stock = avg 1yr return over last
         5 years
    - self.rm same as rs but for benchmark (ie the market return)
    - self.rf stores the risk free rate = price of 13 week t-bill
    - self.eps store EPS TTM
    - self.price stores the price as of run time
    '''
    # FinancialAnalysis(stock, benchmark) initiates a new FinancialAnalysis
    #    object for stock and associated benchmark.
    # Str Str --> FinancialAnalysis
    # Requires: stock and benchmark are Yahoo Finance tickers
    def __init__(self, stock, benchmark):
        # yf tickers
        stock = yf.Ticker(stock)
        benchmark = yf.Ticker(benchmark)
        # stock info - not all have div --> error
        self.info = stock.info
        try:
            self.eps = self.info['epsTrailingTwelveMonths']
            self.currency = self.info['currency']
            self.price = self.info['regularMarketPrice']   
            self.pb = self.info['priceToBook']
            self.pe = self.info['trailingPE']
            self.name = self.info['longName']
            self.symbol = self.info['symbol']
            self.exchange = self.info['fullExchangeName']
            self.adv3m = self.info['averageDailyVolume3Month']
            self.div = self.info['trailingAnnualDividendRate']
            self.div_rate = self.div / self.price
        except:
            KeyError
        # historical market data df's
        self.stock_data = stock.history(period='5y', interval='1d')
        self.benchmark_data = benchmark.history(period='5y', interval='1d')
        # adds column 'Return %' to dataframes
        for yf_df in [self.stock_data, self.benchmark_data]:
            last_close = None
            for i, row in yf_df.iterrows():
                if last_close != None:
                    change = (row['Close'] - last_close) / last_close
                    yf_df.at[i, 'Return %'] = 100 * change
                last_close = row['Close']
        # returns
        self.rs = (self.stock_data['Return %'].sum() / 5) / 100
        self.rm = (self.benchmark_data['Return %'].sum() / 5) / 100
        t_bill = yf.Ticker('^IRX') # 13 week US T-bill ticker
        self.rf = t_bill.info['regularMarketPrice'] / 100
        # risk premiums
        self.erp = self.rs - self.rf # equity risk premium
        self.mrp = self.rm - self.rf # market risk premium        
               
            
    # self.beta() produces the five year beta for stock based on benchmark
    # beta: FinancialAnalsysis --> Float
    def beta(self):
        '''
        Beta measures a stocks volatility by explaining how the stock has 
        historically moved in relation to a 1% movement in the associated 
        benchmark.
        '''
        # 1. inner merge 'Returns %' for stock and benchmark
        left = self.stock_data[['Return %']]
        right = self.benchmark_data[['Return %']]
        left.rename(columns = {'Return %': 'Stock Return %'}, inplace=True)
        right.rename(columns = {'Return %': 'Benchmark Return %'}, inplace=True)
        data = pd.merge(left, right, on='Date', how='inner')
        # 2. calculate beta
        cov = data.cov().at['Stock Return %', 'Benchmark Return %']
        var = data['Benchmark Return %'].var()
        beta = cov / var
        return beta
    

    # self.capm() produces the expected return on the stocks capital assests
    #    according to the capital asset pricing model.
    # FinancialAnalysis --> Float
    def capm(self):
        '''
        CAPM generates the cost of equity for securities given the risk of
        those assets and the cost of capital.
        '''
        beta = self.beta()
        capm = self.rf + (beta * self.mrp)
        return capm
    

    # self.div_history() produces a dataframe containing dividends paid and
    #    corresponding payment dates
    # None --> DataFrame
    def div_history(self):
        divs = self.stock_data[['Dividends']].query('Dividends > 0')
        return divs
    

    # self.div_growth() produces the average growth rate of dividend payments
    # FinancialAnalysis --> Float
    def div_growth(self):
        divs = self.div_history()
        changes = []
        prev = None
        for i, row in divs.iterrows():
            curr = row['Dividends']
            if prev != None:
                change = (curr - prev) / prev
                changes += [change]
            prev = curr
        avg_change = np.mean(np.array(changes))
        return avg_change
    

    # self.ddm() produces the fair value of stock according to the assumptions
    #    of the dividend discount model
    # FinancialAnalysis --> Float
    def ddm(self):
        '''
        DDM is based on the theory that a company's value is the present value
        of its future dividend payments in perpetuity.
        '''
        equity_cost = self.capm()
        div_growth = self.div_growth()
        next_div = self.div * (1 + div_growth)
        value = next_div / (equity_cost - div_growth)
        return value
        

    # alt_rs(self, approach): produces the expected stock return according to
    #    chosen approach. It is an alternative to self.rs.
    # requires: approach is one of: earnings-based, div-based
    # FinancialAnalysis Str --> Float
    def alt_rs(self, approach):
        if approach == 'earnings-based':
            return self.eps / self.price
        elif approach == 'div-based':
            g = self.div_growth()
            return self.div_rate + g           
    

    # self.roi(buy_price, commission, quantity, unit) produces the return on
    #    investment in stock given buy_price, commission, quantity, and unit.
    # requires: unit is one of: percent, dollar
    # roi: FinancialAnalysis Num Num Num Str --> Num
    # note: uses price as of time the FA object was created
    def roi(self, buy_price, commission, quantity, unit):
        cost = (buy_price * quantity) + commission
        mv = self.price * quantity
        if unit is 'percent':
            roi = 100 * (mv - cost) / cost
        elif unit is 'dollar':
            roi = mv - cost           
        return roi
    

    # self.d2l(quantity) computes the number of days required to liquidate a
    #    position of size quantity assuming you can capture 20% of the 3 month 
    #    ADV.
    # d2l: FinancialAnalysis Num --> Num
    def d2l(self, quantity):
        adv_3m = self.adv3m
        d2l = quantity / (adv_3m * .2)
        return d2l