
import pymongo

'''Query Single Stock Train Test'''
def sstt_cursors(symbol, test_fraction = 0.40):
    '''Single Stock Train Test Cursors. Generates cursors for train [i.e. 2006-2010] and test [i.e. 2011]
    Parameters: Symbol, Test Fraction (Test is last test_fraction portion in time increasing data.)
    Returns: Cursors, Time Increasing, For both train and test on symbol
    Important: Assumes same nested "data" document structure from my earlier creation
        Assumes that nested data was create_index on date, and sorted by pymongo.ASCENDING on creation
    '''
    client = pymongo.MongoClient()
    equities = client.equities
    stocks = equities.stocks
    size = stocks.aggregate([{"$match":{"symbol":symbol}},{"$project": {"_id": 1, "count": {"$size": "$data"}}}])
    timesteps = size.next()['count']
    train_index = round(timesteps*(1-test_fraction))
    test_data = stocks.aggregate([{"$match":{"symbol":symbol}}, 
                                        {"$unwind": "$data"}, 
                                        {"$sort":{"data.date":1}},
                                        {"$skip":train_index}])
    train_data = stocks.aggregate([{"$match":{"symbol":symbol}}, 
                                            {"$unwind": "$data"}, 
                                            {"$sort":{"data.date":1}},
                                            {"$limit":train_index}])
    return train_data, test_data
'''/Query Single Stock Train Test'''

def stock_cursor(symbols, randomize=True):
    '''General Stock Cursor. Generates cursor on a stock in "symbols", can be random if "randomize". 
    Notes: Idealized usage is to pass list of valid symbol names, it will pick a stock and return a
        cursor to it. For TTS, I imagine you pass in a list excluding one for train and in a separate
        call, you include the single test run. 
    Parameters: Symbols, INT or LIST_LIKE, if List, returns random/ordered cursor over symbols entered. 
    Returns: Cursors, Time Increasing, For both train and test on symbol
    Important: Assumes same nested "data" document structure from my earlier creation
        Assumes that nested data was create_index on date, and sorted by pymongo.ASCENDING on creation
    '''
    import random
    client = pymongo.MongoClient()
    equities = client.equities
    stocks = equities.stocks
    if randomize:
        # TODO: Implement random finding of stock. 
        pass 
    data = stocks.aggregate([{"$match":{"symbol":symbol}}, 
                                        {"$unwind": "$data"}, 
                                        {"$sort":{"data.date":1}},
                                        {"$skip":train_index}])

    return train_data, test_data
'''Query All on Some Stock'''
# TODO: Make General Stock Finder. Useful for episodes spanning numerous stocks. 
'''/Query All on Some Stock'''

def db_to_ubiquitous_df(symbols, selection_vars, limit = 200, offset = 100):
    '''In need of a way to fit a general scaler, this creates an array of
    raw values for selection_vars of interest across all stocks in the DB.
    NOTE: It starts halfway through the data minus offset then takes "limit" 
    number of items. This was done to not leak into the test data, and get general numbers.  
    '''
    import pandas as pd
    import pymongo
    from tqdm import tqdm
    client = pymongo.MongoClient()
    equities = client.equities
    stocks = equities.stocks
    to_add = {i:[] for i in selection_vars}
    for symbol in tqdm(symbols):
        size_curr = stocks.aggregate([{"$match":{"symbol":symbol}},{"$project": {"_id": 1, "count": {"$size": "$data"}}}])
        size = size_curr.next()['count']
        target = round(size/2) - offset
        curr_data = stocks.aggregate([{"$match":{"symbol":symbol}}, 
                                        {"$unwind": "$data"}, 
                                        {"$sort":{"data.date":-1}},
                                        {"$skip":target},
                                        {"$limit":limit}])
        for item in curr_data:
            for name in to_add.keys():
                to_add[name].append(item['data'][name])
    item_lengths = {i:len(to_add[i]) for i in to_add.keys()}
    print('Success. Counts... \n{}'.format(item_lengths))
    return pd.DataFrame(to_add)

def make_standard_scaler(df, save=True):
    '''Makes general standard scaler, for me this is on the big tech companies.
    Min-Max is in Z score, or std. MUST INCLUDE SOME ACTIVATION into ANN (tanh, sigmoid).
    Notes: Standard scaler subtracts mean and divides by std. We could go into 
        detail on which is better. TanH loses resolution around +-2.65. Meaning...
        if 2.65 is fed to tanh, 0.9900+ is returned. if 2.70 is fed, 0.9910+ is returned. 
    Parameters: df from db_to_ubiquitous_df
    Returns: scaler, list_of_column_name_order
    '''
    from sklearn.preprocessing import StandardScaler
    from sklearn.externals import joblib 
    scaler = StandardScaler()
    sorted_df = df.reindex(sorted(df.columns), axis=1)
    scaler.fit(sorted_df.values)
    if save:
        filename = "resources/tech_scaler.pkl"
        print('saving scaler at {}\n'.format(filename))
        joblib.dump(scaler, filename)
    return scaler, list(sorted_df.columns)
    # Load with: scaler = joblib.load(filename)

def make_minmax_scaler(df, save=True):
    '''Makes general min-max scaler, for me this is on the big tech companies.
    Min-Max is between -1, 1 for ease of use with ANNs
    Notes: MinMax scaler uses the min and max found to squish data. always -1 to 1
    Parameters: df from db_to_ubiquitous_df
    Returns: scaler, list_of_column_name_order
    '''
    from sklearn.preprocessing import StandardScaler
    from sklearn.externals import joblib 
    scaler = StandardScaler()
    sorted_df = df.reindex(sorted(df.columns), axis=1)
    scaler.fit(sorted_df.values)
    if save:
        filename = "resources/tech_scaler.pkl"
        print('saving scaler at {}\n'.format(filename))
        joblib.dump(scaler, filename)
    return scaler, list(sorted_df.columns)
    # Load with: scaler = joblib.load(filename)

if __name__ == "__main__":
    '''NOTE: Running mongo.py requires database made by running iex.py '''
    print('This will replicate my scaler...\n')
    choice = input('Want to continue? ').lower()
    if choice == 'y':
        from tqdm import tqdm
        symbols = ['AAPL', 'MSFT', 'AMZN', 'INTC', 'AMD']
        state_vars = ['change', 'close_vwap', 'high_low', 'open_close'] #, 'volume']
        print('retrieving: {}\n'.format(symbols))
        df = db_to_ubiquitous_df(symbols, state_vars)
        scaler, column_order = make_general_scaler(df)
        print('Vars: df, scaler, column_order now in memory.\n')
    else:
        print('abandoning...\n')
    