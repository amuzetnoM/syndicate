import yfinance as yf

if __name__ == '__main__':
    df = yf.download('GC=F', period='5d', interval='1d', progress=False)
    if not df.empty:
        print(df['Close'].dropna().iloc[-1])
    else:
        print('No data')
