import sys 
import random
import pandas as pd
import numpy as np
from collections import deque
from time import localtime, strftime

# Functions
def relu(x, m1=0.01, m2=1):
    if x <= 0:
        return m1*x
    else:
        return m2*x

def tanh(x):
    return (np.exp(2*x)-1)/(np.exp(2*x)+1)

def xabx(x):
    return x/(1 + np.abs(x))

def sigmoid(x):
    return 1/(1+np.exp(-x))

def testing123(model, NN_input_size, reset=False):
    '''Given a model and input dimensions, this generates data and retuns a history object.
    Parameters: model, the same NN_input_size used in Bots.py, reset model weights
    Returns: History object
    '''
    # Dummy Data
    X_train = np.random.random((1000, *NN_input_size))
    y_train = np.random.random((1000, NN_input_size[-1]))
    historyObject = model.fit(X_train, y_train, batch_size=100, epochs=1, validation_split=0.25)
    if reset:
        model.reset_states()
    return historyObject

def save_output(name, df):
    from time import localtime, strftime
    import os  
    if os.path.isdir('./output') and type(name) == str:
        df.to_csv('output/{}{}.csv'.format(name, strftime("%Y-%m-%d{%H-%M}", localtime())))

def save_bot(bot):
    from time import localtime, strftime
    import pickle
    import os  
    if os.path.isdir('./output'):
        filename = 'output/bot_{}.pickle'.format(strftime("%Y-%m-%d{%H-%M}", localtime()))
        print('saving bot at {}\n'.format(filename))
        with open(filename, 'wb') as f:
            # Pickle the 'data' dictionary using the highest protocol available.
            pickle.dump(bot, f, pickle.HIGHEST_PROTOCOL)

def Train(bot, scaler, symbol, state_vars, episode_count=3, shares=0, start_cash=20000, replay_size=32, use_reward=False):
    '''Notes of interest: This training procedure takes a cursor to train data, uses HER to
    Learn from past rewards. To summarize DQN, we just predict as we step through data.
    Periodically (I chose every replay_size steps), we fit on a batchsize of memories.
    Parameters:
        bot: actual capable bot object
        scaler: some scaler object fit to data coming in
        train_data: Cursor to specific db data (like output query of train data).
        window: Legth of timesteps for bot
        shares: Number of starting stock shares for little bot
        cash: amount of starting cash
        replay_size: Batch size for HER
    '''
    window = bot.NN_input_shape[0]
    if window > replay_size:
        raise ValueError('Window cannot be larger than replay size.')
    # Create Log
    this_log = pd.DataFrame(columns = ['Loss', 'Reward', 'Epsilon', 'Cash', 'Shares'])
    action_log = []
    # Routine Setup
    epsilon = 1
    discount = 0.01 #0.95
    options = ['buy', 'sell', 'hold']
    for episode in range(episode_count):
        state = np.zeros((1, window, len(state_vars) + 3)) # Allocate memory. This is of (1, #, #) for single fitting
        share_prices = deque([]) # Time Com. of O(1) for left popping...
        train_cursor, _ = sstt_cursors(symbol)
        cash = start_cash
        count = 0
        done = False
        for item in train_cursor:
            print(item['data']['date'])
            curr_price = item['data']['close']
            curr_change = item['data']['change']
            value = len(share_prices)*curr_price + cash
            # End Conditions (can't buy & can't sell)
            if cash < curr_price and len(share_prices) == 0:
                done = True
            # Simple window: Have state going back in time, save that, shift down, ammend this step
            previous_state = state
            state[0][1:,:] = state[0][:-1, :]
            # Generating State Vars
            if cash > curr_price:
                can_buy = 1
            else:
                can_buy = 0
            if len(share_prices) >= 1:
                can_sell = 1
            else:
                can_sell = 0
            cash_state = sigmoid(cash/start_cash)
            # NOTE: Scaler Transform requires alphabetical columns for proper prediction
            temp_state = [scaler.transform([[item['data'][j] for j in state_vars]])[0]]
            temp_state = np.array([np.append(temp_state[0], can_buy)])
            temp_state = np.array([np.append(temp_state[0], can_sell)])
            temp_state = np.array([np.append(temp_state[0], cash_state)])
            state[0][0,:] = temp_state
            if count >= window: # Start Bot once state is full enough
                actions = bot.predict(previous_state)
                # Exploration
                if random.random() < epsilon:
                    action = random.randrange(len(options))
                    choice = options[action]
                else:
                    # Greedy chooser, best action in bots world
                    action = np.argmax(actions)
                    choice = options[action]
                # Exploration Decay
                if epsilon > 0.01:
                    epsilon -= 0.002
                    print('Epsilon: ', round(epsilon, 5))
                else:
                    epsilon = 0.01
                # Reward Engineering [Buy, Sell, Hold] (0, 1, 2)
                reward = 0
                if use_reward:
                    if choice == 'buy':
                        if cash > curr_price:
                            cash -= curr_price
                            shares += 1
                            share_prices.append(curr_price)
                        else:
                            reward = -0.1
                    elif choice == 'sell':
                        if shares > 0:
                            shares -= 1
                            cash += curr_price
                            profit = curr_price - share_prices.popleft()
                            if profit >= 0:
                                if profit > 10:
                                    reward = 2
                                else:
                                    reward = 1
                            else:
                                reward = -0.5
                        else:
                            reward = -0.1
                    else: # Hold
                        reward = 0
                # Old Reward Structure
                #  if choice=='buy' and cash > curr_price: # Buy
                #     cash -= curr_price
                #     shares += 1
                #     share_prices.append(curr_price)
                #     if use_reward:
                #         reward = 0.1*(-0.5) # Fees. Future Action-Value needs to be appended in HER
                # elif choice=='sell' and shares > 0: # Sell
                #     cash += curr_price
                #     shares -= 1
                #     profit = curr_price - share_prices.pop()
                #     if use_reward:
                #         reward = 0.01*(-0.5 + profit) # Fees - Profit. Dampened
                # else:
                #     if use_reward:
                #         reward = 0.005*curr_change
                # It is important to note the memory deque is 1000 long.
                bot.memory.append((previous_state, action, reward, state, done))
                action_log.append(actions[0])
                # Hindsight Experience Replay
                if (count - window + 1) % replay_size == 0:
                    print('Replaying...')
                    batch = random.sample(bot.memory, replay_size)
                    for batch_state, batch_action, batch_reward, batch_new_state, batch_done in batch:
                        # Current buy, sell, hold predictions, Q(s, a)
                        targets = bot.predict(batch_state)
                        # Expected buy, sell, hold predictions
                        action_value = bot.predict(batch_new_state)
                        if use_reward:
                            # Adjusting target by return and discounted future return
                            # Must += instead of reassigning rewards because reward could be zero or negative
                            if not batch_done:
                                targets[0][batch_action] += batch_reward + discount*np.max(action_value)
                            else:
                                targets[0][batch_action] += batch_reward
                        history = bot.fit(batch_state, targets, batch_size=1, epochs=1, shuffle=False)
                        this_log = this_log.append({'Loss':history.history['loss'][0], 
                                                    'Reward':batch_reward, 
                                                    'Epsilon':epsilon, 
                                                    'Cash':cash,
                                                    'Shares':len(share_prices)},
                                                    ignore_index = True)
            if done:
                save_output('this_log', this_log)
                break
            else:
                print('Count: ', count, '\n')
                count += 1
        else:
            '''Wow! It Made it!'''
            print('The Bot Survived.')
            print('Episode: ', episode)
        save_output('this_log_episodes', this_log)
    return bot, this_log, action_log

def Test(bot, scaler, test_data, state_vars, shares=0, start_cash=20000):
    '''Notes of interest: This training procedure takes a cursor to train data, uses HER to
    Learn from past rewards. To summarize DQN, we just predict as we step through data.
    Periodically (I chose every replay_size steps), we fit on a batchsize of memories.
    Parameters:
        bot: actual capable bot object
        scaler: some scaler object fit to data coming in
        train_data: Cursor to specific db data (like output query of train data).
        window: Legth of timesteps for bot
        shares: Number of starting stock shares for little bot
        cash: amount of starting cash
        replay_size: Batch size for HER
    '''
    window = bot.NN_input_shape[0]
    # Create Log
    portfolio_log = pd.DataFrame(columns = ['Value', 'Action', 'Shares', 'Cash', 'Profits', 'Close'])
    # Routine Setup
    options = ['buy', 'sell', 'hold']
    state = np.zeros((1, window, len(state_vars) + 3))
    share_prices = deque([]) # Time Com. of O(1) for left popping...
    cash = start_cash
    profits = 0
    count = 0
    done = False
    for item in test_data:
        curr_price = item['data']['close']
        curr_change = item['data']['change']
        value = len(share_prices)*curr_price + cash
        # End Conditions (can't buy & can't sell)
        if cash < curr_price and len(share_prices) == 0:
            done = True
        # Simple window: Have state going back in time, save that, shift down, ammend this step
        previous_state = state
        state[0][1:,:] = state[0][:-1, :]
        # Generating State Vars
        if cash > curr_price:
            can_buy = 1
        else:
            can_buy = 0
        if len(share_prices) >= 1:
            can_sell = 1
        else:
            can_sell = 0
        cash_state = sigmoid(cash/start_cash)
        # NOTE: Scaler Transform requires alphabetical columns for proper prediction
        temp_state = [scaler.transform([[item['data'][j] for j in state_vars]])[0]]
        temp_state = np.array([np.append(temp_state[0], can_buy)])
        temp_state = np.array([np.append(temp_state[0], can_sell)])
        temp_state = np.array([np.append(temp_state[0], cash_state)])
        state[0][0,:] = temp_state
        if count >= window and not done: # Start Bot once state is full enough
            actions = bot.predict(previous_state)
            #print('State: \n', state, '\n')
            print('Actions: ', actions, '  ', np.argmax(actions), '\n')
            action = np.argmax(actions)
            choice = options[action]
            # No Exploration
            # Reward Engineering [Buy, Sell, Hold/Do Nothing] (0, 1, 2)
            if choice=='buy' and cash > curr_price:
                cash -= curr_price
                shares += 1
                share_prices.append(curr_price)
            elif choice=='sell' and shares > 0: 
                cash += curr_price
                shares -= 1
                profits += curr_price - share_prices.popleft()
            portfolio_log = portfolio_log.append({'Value':value, 'Action':action, 'Shares':shares, 'Cash':cash, 'Profits':profits, 'Close':curr_price}, ignore_index = True)
        elif done:
            print('Bot Died...')
            break
        count += 1
    else:
        '''Wow! It Made it!'''
        print('The Bot Survived.')
    return portfolio_log

def Test_random(bot, test_data, shares=0, start_cash=20000):
    '''Notes of interest: This training procedure takes a cursor to train data, uses HER to
    Learn from past rewards. To summarize DQN, we just predict as we step through data.
    Periodically (I chose every replay_size steps), we fit on a batchsize of memories.
    Parameters:
        bot: actual capable bot object
        scaler: some scaler object fit to data coming in
        train_data: Cursor to specific db data (like output query of train data).
        window: Legth of timesteps for bot
        shares: Number of starting stock shares for little bot
        cash: amount of starting cash
        replay_size: Batch size for HER
    '''
    window = bot.NN_input_shape[0]
    # Create Log
    portfolio_log = pd.DataFrame(columns = ['Value', 'Action', 'Shares', 'Cash', 'Profits', 'Close'])
    # Routine Setup
    options = ['buy', 'sell', 'hold']
    share_prices = deque([]) # Time Com. of O(1) for left popping...
    cash = start_cash
    profits = 0
    count = 0
    done = False
    for item in test_data:
        curr_price = item['data']['close']
        curr_change = item['data']['change']
        value = len(share_prices)*curr_price + cash
        # End Conditions (can't buy & can't sell)
        if cash < curr_price and len(share_prices) == 0:
            done = True
        # Generating State Vars
        if cash > curr_price:
            can_buy = 1
        else:
            can_buy = 0
        if len(share_prices) >= 1:
            can_sell = 1
        else:
            can_sell = 0
        cash_state = sigmoid(cash/start_cash)
        if count >= window and not done: # Start Bot once state is full enough
            action = random.randrange(len(options))
            choice = options[action]
            # No Exploration
            # Reward Engineering [Buy, Sell, Hold/Do Nothing] (0, 1, 2)
            if choice=='buy' and cash > curr_price:
                cash -= curr_price
                shares += 1
                share_prices.append(curr_price)
            elif choice=='sell' and shares > 0: 
                cash += curr_price
                shares -= 1
                profits += curr_price - share_prices.popleft()
            portfolio_log = portfolio_log.append({'Value':value, 'Action':action, 'Shares':shares, 'Cash':cash, 'Profits':profits, 'Close':curr_price}, ignore_index = True)
        elif done:
            print('Bot Died...')
            break
        count += 1
    else:
        '''Wow! It Made it!'''
        print('The Bot Survived.')
    return portfolio_log

if __name__ == "__main__":
    import pandas as pd
    from time import localtime, strftime
    from keras.callbacks import TensorBoard
    from sklearn.externals import joblib 
    import matplotlib.pyplot as plt 
    import seaborn as sns
    import pickle
    sys.path.append("./src")
    from Bots import Bot_LSTM
    from mongo import sstt_cursors
    # Specifics (Note alphabetic...for scaler)
    state_vars = ['change', 'close_vwap', 'high_low', 'open_close'] #, 'volume']
    bot = Bot_LSTM((14, len(state_vars)+3))
    scaler = joblib.load("resources/tech_scaler.pkl")
    '''Train'''
    # The flow of train is to train a bot on a stock and get back the bot, with a PD.DataFrame log
    # Ideally this would continue for numerous stocks for one bot.
    episodes = 1
    bot_r, train_log_random, action_log_random = Train(bot, scaler, 'INTC', state_vars, episode_count=episodes)
    action_df_random = pd.DataFrame(action_log_random, columns = ['buy', 'sell', 'hold'])
    _, test_cursor = sstt_cursors('INTC')
    portfolio_log_random = Test(bot_r, scaler, test_cursor, state_vars)
    bot, train_log, action_log = Train(bot, scaler, 'INTC', state_vars, episode_count=episodes, use_reward=True)
    action_df = pd.DataFrame(action_log, columns = ['buy', 'sell', 'hold'])
    _, test_cursor = sstt_cursors('INTC')
    portfolio_log = Test(bot, scaler, test_cursor, state_vars)
    _, test_cursor = sstt_cursors('INTC')
    random_log = Test_random(bot, test_cursor)
    #train_log.drop(columns = 'Unnamed: 0', inplace=True)
    bot.my_save('./output')
    #save_output('train_aapl2', train_log)
    #weights_filename = './output/bot_LSTM_2019-04-22{14-11}.h5'
    # '''Test'''
    #test_bot = Bot_LSTM((14, len(state_vars)+3), weights_filename=weights_filename)
    #portfolio_log.drop(columns = 'Unnamed: 0', inplace=True)
    #save_output('test_aapl2', portfolio_log)
    # import matplotlib.pyplot as plt 
    # train_log.plot(figsize = (14, 8))
    # portfolio_log.plot(figsize = (14, 8))
    # plt.show()
    # Drop Cash
    plt.rcParams.update({'font.size': 12, 'figure.subplot.hspace':0.1})
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize = (11, 7), sharex=True)
    sns.lineplot(data = train_log_random[['Reward', 'Loss', 'Epsilon']].astype('float'), ax=ax1, style='choice', palette=sns.cubehelix_palette(light=.8, n_colors=3))
    sns.lineplot(data = train_log_random['Shares'].astype('float'), ax=ax2, style='choice', palette=sns.cubehelix_palette(light=.8, n_colors=3))
    ax1.set_title('Untrained Model', fontsize=15)
    ax2.set_xlabel('Timesteps', fontsize=15)
    ax2.text(700, 9, 'Shares',
        verticalalignment='top', horizontalalignment='right',
        bbox={'facecolor':'blue', 'alpha':0.2, 'pad':10}, fontsize=15)
    plt.savefig('plots/train_log_random_bce1{}.png'.format(strftime("%Y-%m-%d{%H:%M}", localtime())))

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize = (11, 7), sharex=True)
    sns.lineplot(data = train_log[['Reward', 'Loss', 'Epsilon']].astype('float'), ax=ax1, style='choice', palette=sns.cubehelix_palette(light=.8, n_colors=3))
    sns.lineplot(data = train_log['Shares'].astype('float'), ax=ax2, style='choice', palette=sns.cubehelix_palette(light=.8, n_colors=3))
    ax1.set_title('Training Model', fontsize=15)
    ax2.set_xlabel('Timesteps', fontsize=15)
    ax2.text(700, 9, 'Shares',
        verticalalignment='top', horizontalalignment='right',
        bbox={'facecolor':'blue', 'alpha':0.2, 'pad':10}, fontsize=15)
    plt.savefig('plots/training_log_bce1{}.png'.format(strftime("%Y-%m-%d{%H:%M}", localtime())))

    plt.rcParams.update({'font.size': 12, 'figure.subplot.hspace':0.3})
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize = (12, 6), sharex=True, sharey=True)
    sns.lineplot(data = action_df.astype('float'), ax=ax1, style='choice', palette=sns.cubehelix_palette(light=.8, n_colors=3))
    sns.lineplot(data = action_df_random.astype('float'), ax=ax2, style='choice', palette=sns.cubehelix_palette(light=.8, n_colors=3))
    ax1.set_title('Training Model', fontsize=15)
    ax2.set_title('Untrained Model', fontsize=15)
    ax1.set_xlabel('Timesteps', fontsize=15)
    ax2.set_xlabel('Timesteps', fontsize=15)
    fig.suptitle('Action Probabilities Through Time (Softmax)', fontsize=22)
    plt.savefig('plots/action_log_bce1{}.png'.format(strftime("%Y-%m-%d{%H:%M}", localtime())))

    plt.rcParams.update({'font.size': 12, 'figure.subplot.hspace':0.8})
    fig, ax = plt.subplots(3, 1, figsize = (11, 8))
    sns.lineplot(data = portfolio_log[['Shares', 'Profits']].astype('float'), ax=ax[0], style='choice', palette=sns.cubehelix_palette(light=.8, n_colors=2))
    sns.lineplot(data = portfolio_log_random[['Shares', 'Profits']].astype('float'), ax=ax[1], style='choice', palette=sns.cubehelix_palette(light=.8, n_colors=2))
    sns.lineplot(data = random_log[['Shares', 'Profits']].astype('float'), ax=ax[2], style='choice', palette=sns.cubehelix_palette(light=.8, n_colors=2))
    ax[0].set_title('Trained Model', fontsize=15)
    ax[1].set_title('Untrained Model', fontsize=15)
    ax[2].set_title('Random Choice', fontsize=15)
    ax[2].set_xlabel('Timesteps', fontsize=13)
    plt.savefig('plots/shares_profits_bce1{}.png'.format(strftime("%Y-%m-%d{%H:%M}", localtime())))

    fig, ax = plt.subplots(3, 1, figsize = (11, 8))
    sns.lineplot(data = portfolio_log[['Cash', 'Value']].astype('float'), ax=ax[0], style='choice', palette=sns.cubehelix_palette(light=.8, n_colors=2))
    sns.lineplot(data = portfolio_log_random[['Cash', 'Value']].astype('float'), ax=ax[1], style='choice', palette=sns.cubehelix_palette(light=.8, n_colors=2))
    sns.lineplot(data = random_log[['Cash', 'Value']].astype('float'), ax=ax[2], style='choice', palette=sns.cubehelix_palette(light=.8, n_colors=2))
    ax[0].set_title('Trained Model', fontsize=15)
    ax[1].set_title('Untrained Model', fontsize=15)
    ax[2].set_title('Random Choice', fontsize=15)
    ax[2].set_xlabel('Timesteps', fontsize=13)
    plt.savefig('plots/cash_value_bce1{}.png'.format(strftime("%Y-%m-%d{%H:%M}", localtime())))
    plt.show()

    ''' Change Log
    Added Plotting
    Removed Saving for now
    Ran: 
        Changed from 32, 16, 8 to 64, 32, 8
        Changing epsilon
        Now predicting Sell Only
    Ran: 
        Changing Layer Structure
        Two LSTM's, one Dense with linear, into output, all same 32
        Changed LR to 0.1 from 0.001
        Loss and Actions skyrocketted. Going back, keeping LR
    Ran:
        Changed back to 32, 32, 8, action, LR = 0.1
        Loss Higher and Quicker than before.
        Predicts Hold Only!
    Ran: Added activation into model
        High error
    Ran:  Changed reward from 0.1,0.1 to 1,1
        Loss 25889 at 300
        Tripling neuron unit numbers
        Loss is now 219800 or 10x. Note. Sold Locked
    Ran: Loss at 300 is now 14600, making smaller and deeper. Note: Buy locked
        Loss at 300 is now 14000. Chasing error still. 
        Hold Locked
        Let me try increasing epsilon. Epsilon is like 80%. 
        Loss linearly increasing. 3900 at 300
    Ran: Lowered learning rate from 0.1 to 0.001. Also increasing epsilon to 0.9
        Adding kernel regularizer L1 to all layers
    Ran:
        Loss still growing. Added about 15 ms 
        Changed reward relu to xabx
        Added back in epsilon decay because test has no epsilon.
        Unless I forgot something loss is quite low.
        Count 550, loss 13, epsilon 0.48 
        Reward always negative...Wait had to remove reward = -curr_price from buy option
    Ran: Loss still growing but pretty low. 
        Running once with zero fitting. 
        May do more reward engineering
    Ran: Adding reward back in. Super Tiny xabx(profit)*0.001
    Recap: 
    '''