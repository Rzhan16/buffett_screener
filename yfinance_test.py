import yfinance as yf

def test_yfinance():
    try:
        df = yf.download('AAPL', start='2020-01-01', end='2020-01-10')
        print(df)
        if df.empty:
            print('Download succeeded but DataFrame is empty.')
        else:
            print('Download succeeded and DataFrame is not empty.')
    except Exception as e:
        print(f'Exception occurred: {e}')

test_yfinance() 