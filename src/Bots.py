
# __init__()
import keras
from keras.models import Sequential
from keras.layers import Dense, Activation, Dropout, Flatten 
from keras.optimizers import Adam
from keras.models import load_model
# LSTM __init__()

# save()
from os.path import isdir
from time import localtime, strftime
# remember()
from collections import deque
import random

'''Class Bot
A Basic ANN that inherits from Keras Sequential and extends for reinforcement learning and
hindsight experience replay support. 
'''
class Bot(Sequential):
    '''See help(Sequential). Inheritance here from Keras Sequential()
    Notes: The ANN wants unwound data. For windowed state, it unwraps into a single instance.
    Parameters:
        NN_input_shape()
            This tuple must be compatible with the Sequential() input layer input_shape. 
    Extra Methods: 
        remember() 
            The act of remembering one "event" for hindsight experience replay. See SARSA
        my_save() 
            Given a valid directory, this will generate an h5 model file with an 
            autogenerated name including the current date
        replay()
            Using a batch_size, returns a collection of memories
    Returns: Instance of Sequential() with additional methods 
    '''

    def __init__(self, NN_input_shape, action_space=3, weights_filename=None, verbose=True):
        # Params
        self.NN_input_shape = NN_input_shape
        self.action_space = action_space
        self.verbose = verbose
        self.memory = deque(maxlen=1000)
        # Init
        self.make()
        if weights_filename:
            self.weights_filename = weights_filename
            print('Loading Model Weights...')
            self.load_weights(weights_filename)
        if self.verbose:
            print(self.summary())
    
    def make(self):
        print('Creating Model...')
        # This inherits from Sequential.
        super().__init__()
        self.add(Dense(units=64, input_shape=self.NN_input_shape, activation="relu"))
        self.add(Dense(units=32, activation="relu"))
        self.add(Dense(units=8, activation="relu"))
        self.add(Dense(self.action_space, activation="linear"))
        self.compile(loss="mse", optimizer=Adam(lr=0.00001))
    
    def my_save(self, directory):
        '''Given a valid directory in scope, say resources (no slash) this method will
        save the model level h5 (as opposed to the weight level h5 for a given architecture)
        and append the filename with the timestamp.
        Parameters: directory
        Returns: None
        '''
        if isdir(directory):
            if directory[-1] != '/':
                self.save_weights(directory + '/bot_LSTM_{}.h5'.format(strftime("%Y-%m-%d{%H:%M}", localtime())))
            else:
                self.save_weights(directory + 'bot_LSTM_{}.h5'.format(strftime("%Y-%m-%d{%H:%M}", localtime())))
        else:
            print('not a directory')

    def remember(self, memory):
        '''Typically in the form:
            (state, action, reward, new_state)
        '''
        self.memory.append(memory)

    def replay(self, batch_size):
        '''Given a long enough memory, this will return a random sample from it.
        Parameters: batch_size, the number of items to return
        Returns: List of len(batch_size) full of memories
        '''
        return random.sample(self.memory, batch_size)
'''End Bot Class - Usage: bot = Bot((21,))'''




'''Class Bot_LSTM
A basic recurrent neural network bot that inherits from Keras Sequential and extends 
for reinforcement learning and
hindsight experience replay support. 
'''
class Bot_LSTM(Sequential):
    '''See help(Sequential). Inheritance here from Keras Sequential()
    Notes: Linear, MSE, Adam(lr=very low) would be used for RL
    Parameters:
        NN_input_shape()
            This tuple must be compatible with the Sequential() input layer input_shape. For LSTMs 
            this is always 3D data, you are responsible for the last two. Given (samples, timesteps, features)
            you should enter a tuple of (timesteps, features)
    Extra Methods: 
        remember() 
            The act of remembering one "event" for hindsight experience replay. See SARSA
        my_save() 
            Given a valid directory, this will generate an h5 model file with an 
            autogenerated name including the current date
        replay()
            Using a batch_size, returns a collection of memories
    Returns: Instance of Sequential() with additional methods 
    '''

    from keras.layers import LSTM
    
    def __init__(self, NN_input_shape, action_space=3, weights_filename=None, verbose=True):
        # Params
        self.NN_input_shape = NN_input_shape
        self.action_space = action_space
        self.weights_filename = weights_filename
        self.verbose = verbose
        self.memory = deque(maxlen=1000)
        # Init
        self.make()
        if weights_filename:
            print('Loading Model Weights...')
            self.load_weights(weights_filename)
        if self.verbose:
            print(self.summary())

    def make(self):
        print('Creating Model...')
        # This inherits from Sequential. 
        super().__init__()
        self.add(Activation('tanh', input_shape=self.NN_input_shape))
        self.add(LSTM(units=8, return_sequences = True))
        self.add(LSTM(units=8))
        self.add(Dense(self.action_space, activation="linear"))
        self.compile(loss="mse", optimizer=Adam(lr=0.0001))

    def my_save(self, directory):
        '''Given a valid directory in scope, say resources (no slash) this method will
        save the model level h5 (as opposed to the weight level h5 for a given architecture)
        and append the filename with the timestamp.
        Parameters: directory
        Returns: None
        '''
        if isdir(directory):
            if directory[-1] != '/':
                self.save_weights(directory + '/bot_LSTM_{}.h5'.format(strftime("%Y-%m-%d{%H:%M}", localtime())))
            else:
                self.save_weights(directory + 'bot_LSTM_{}.h5'.format(strftime("%Y-%m-%d{%H:%M}", localtime())))
        else:
            print('not a directory')
    
    def remember(self, memory):
        '''Typically in the form:
            (state, action, reward, new_state)
        '''
        self.memory.append(memory)
    
    def replay(self, batch_size):
        '''Given a long enough memory, this will return a random sample from it.
        Parameters: batch_size, the number of items to return
        Returns: List of len(batch_size) full of memories
        '''
        return random.sample(self.memory, batch_size)
'''End Bot Class - Usage: bot = Bot_LSTM((21,3)) < LSTM's require 3D data, see above LSTM docs '''



'''Class Bot_CNN_LSTM
A basic CNN to RNN with LSTM bot that inherits from Keras Sequential and extends 
for reinforcement learning and hindsight experience replay support. 
'''
class Bot_CNN_LSTM(Sequential): # Didn't get there yet
    '''See help(Sequential). Inheritance here from Keras Sequential()
    Notes: The CNNs want 2D data. Being in TD wrapper, need "features" wide by single tall input shape. 
    Parameters:
        NN_input_shape()
            This tuple must be compatible with the Sequential() input layer input_shape. For LSTMs 
            this is always 3D data, you are responsible for the last two. Given (samples, timesteps, features)
            you should enter a tuple of (timesteps, features)
    Extra Methods: 
        remember() 
            The act of remembering one "event" for hindsight experience replay. See SARSA
        my_save() 
            Given a valid directory, this will generate an h5 model file with an 
            autogenerated name including the current date
        replay()
            Using a batch_size, returns a collection of memories
    Returns: Instance of Sequential() with additional methods 
    '''
    from keras.layers import LSTM, Conv2D, MaxPooling2D, TimeDistributed
    def __init__(self, NN_input_shape, action_space=3, weights_filename=None, verbose=True):
        # Params
        self.NN_input_shape = NN_input_shape
        self.action_space = action_space
        self.weights_filename = weights_filename
        self.verbose = verbose
        self.memory = deque(maxlen=1000)
        # Init
        self.make()
        if weights_filename:
            print('Loading Model Weights...')
            self.load_weights(weights_filename)
        if self.verbose:
            print(self.summary())

    def make(self):
        print('Creating Model...')
        # NOTE: Thas not been implemented or tested. Serves to remind of future functionality
        # This inherits from Sequential.
        super().__init__()
        self.add(Activation('tanh', input_shape=self.NN_input_shape))
        self.add(TimeDistributed(Conv2D(12, kernel_size=(1, self.NN_input_shape[0]), activation='relu')))
        self.add(TimeDistributed(MaxPooling2D(pool_size=(1, self.NN_input_shape[0]))))
        self.add(TimeDistributed(Flatten()))
        self.add(LSTM(units=8, return_sequences = True, kernel_regularizer=regularizers.l2(0.01)))
        self.add(LSTM(units=8, kernel_regularizer=regularizers.l2(0.01)))
        self.add(Dropout(0.4))
        self.add(Dense(self.action_space, activation="softmax"))
        self.compile(loss="categorical_crossentropy", optimizer=Adam(lr=0.001))

    def my_save(self, directory):
        '''Given a valid directory in scope, say resources (no slash) this method will
        save the model level h5 (as opposed to the weight level h5 for a given architecture)
        and append the filename with the timestamp.
        Parameters: directory
        Returns: None
        '''
        if isdir(directory):
            if directory[-1] != '/':
                self.save_weights(directory + '/bot_LSTM_{}.h5'.format(strftime("%Y-%m-%d{%H:%M}", localtime())))
            else:
                self.save_weights(directory + 'bot_LSTM_{}.h5'.format(strftime("%Y-%m-%d{%H:%M}", localtime())))
        else:
            print('not a directory')
    
    def remember(self, memory):
        '''Typically in the form:
            (state, action, reward, new_state)
        '''
        self.memory.append(memory)
    
    def replay(self, batch_size):
        '''Given a long enough memory, this will return a random sample from it.
        Parameters: batch_size, the number of items to return
        Returns: List of len(batch_size) full of memories
        '''
        return random.sample(self.memory, batch_size)
'''End Bot Class - Usage: bot = Bot_CNN_LSTM( ??? ) < Throws error "Rank 4"'''
