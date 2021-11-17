import pickle
import numpy as np
import pandas as pd

import torch
from torch import nn
from torch.utils.data import TensorDataset, DataLoader

from sklearn.model_selection import train_test_split
from sklearn import preprocessing
from sklearn.metrics import mean_squared_error
from sklearn.metrics import mean_absolute_error
from sklearn.model_selection import GridSearchCV,RandomizedSearchCV

# Define model
class NeuralNetwork(nn.Module):
    def __init__(self, input_size, output_size, hidden_layers, neurons, dropout):
        super(NeuralNetwork, self).__init__()

        # Single linear layer with relu activation and dropout
        linear_relu_block = nn.Sequential(
            nn.Linear(neurons, neurons),
            nn.ReLU(),
            nn.Dropout(dropout)
        )

        # Stack linear layer blocks as hidden layers
        linear_relu_stack = nn.Sequential()
        for _ in range(hidden_layers):
            linear_relu_stack = nn.Sequential(*(list(linear_relu_stack)+list(linear_relu_block)))

        # Add hidden layers to input and output layers
        self.main = nn.Sequential(
            nn.Linear(input_size, neurons),
            nn.ReLU(),
            linear_relu_stack,
            nn.Linear(neurons, output_size)
        )

    def forward(self, x):
        return self.main(x)


class Regressor():

    def __init__(self, x, nb_epoch=100, learning_rate=0.01, hidden_layers=5, neurons=30, dropout=0.25):
        # You can add any input parameters you need
        # Remember to set them with a default value for LabTS tests
        """ 
        Initialise the model.
          
        Arguments:
            - x {pd.DataFrame} -- Raw input data of shape 
                (batch_size, input_size), used to compute the size 
                of the network.
            - nb_epoch {int} -- number of epoch to train the network.

        """

        #######################################################################
        #                       ** START OF YOUR CODE **
        #######################################################################
        # TODO: Why are these class attributes?
        self.nb_epoch = nb_epoch
        self.x=x
        self.learning_rate=learning_rate
        self.hidden_layers=hidden_layers
        self.neurons=neurons

        # Preprocess dataset to build network
        X, _ = self._preprocessor(x, training = True)

        # Define model, optimizer, and criterion
        self.model = NeuralNetwork(input_size=X.shape[1],
                                   output_size=1, 
                                   hidden_layers=self.hidden_layers, 
                                   neurons=self.neurons,
                                   dropout=dropout)
        self.optimizer = torch.optim.Adam(self.model.parameters(), lr=learning_rate)
        self.criterion = torch.nn.MSELoss()


        #######################################################################
        #                       ** END OF YOUR CODE **
        #######################################################################

    def _preprocessor(self, x, y = None, training = False, norm_method = 'min_max'):
        """ 
        Preprocess input of the network.
          
        Arguments:
            - x {pd.DataFrame} -- Raw input array of shape 
                (batch_size, input_size).
            - y {pd.DataFrame} -- Raw target array of shape (batch_size, 1).
            - training {boolean} -- Boolean indicating if we are training or 
                testing the model.

        Returns:
            - {torch.tensor} or {numpy.ndarray} -- Preprocessed input array of
              size (batch_size, input_size).
            - {torch.tensor} or {numpy.ndarray} -- Preprocessed target array of
              size (batch_size, 1).

        """

        x = x.fillna(-1) # replace all NaNs with -1

        if training == True: 
            # one-hot encoding
            self.one_hot = preprocessing.LabelBinarizer().fit(x['ocean_proximity'])
            x['ocean_proximity'] = np.argmax(self.one_hot.transform(x['ocean_proximity']), axis=1) 

            # save x columnwise normalisation constants
            self.norm_x_min = x.min() 
            self.norm_x_max = x.max() 
            self.norm_x_mean = x.mean() 
            self.norm_x_std = x.std() 
        else:
            # perform one-hot tranform 
            x['ocean_proximity'] = np.argmax(self.one_hot.transform(x['ocean_proximity']), axis=1)     

        if norm_method == 'standard':
            # calculate using saved normalisation constants from training
            x = (x-self.norm_x_mean)/self.norm_x_std

        if norm_method == 'min_max':
            # calculate using saved normalisation constants from training
            x = (x-self.norm_x_min)/(self.norm_x_max-self.norm_x_min) 

        # only convert y to numpy if it was passed
        if isinstance(y, pd.DataFrame):
            y = y.to_numpy()

        return x.to_numpy(), y

        #######################################################################
        #                       ** END OF YOUR CODE **
        #######################################################################


    def fit(self, x, y, mini_batch_size=50, shuffle=True, x_val=None, y_val=None, early_stop_n=5):
        """
        Regressor training function

        Arguments:
            - x {pd.DataFrame} -- Raw input array of shape 
                (batch_size, input_size).
            - y {pd.DataFrame} -- Raw output array of shape (batch_size, 1).

        Returns:
            self {Regressor} -- Trained model.

        """

        #######################################################################
        #                       ** START OF YOUR CODE **
        #######################################################################

        # Preprocess dataset
        X, Y = self._preprocessor(x, y = y, training = True)

        # transform np to torch tensor
        tensor_x = torch.Tensor(X)
        tensor_y = torch.Tensor(Y)

        # load tensors into a dataloader object
        dataset = TensorDataset(tensor_x, tensor_y)
        dataloader = DataLoader(dataset, shuffle=shuffle, batch_size=mini_batch_size)

        # keep track of loss on val set and a streak of subsequent increases in val loss
        val_score, val_streak, model_backup = float("inf"), 0, None

        for _ in range(self.nb_epoch):

            for x, y in dataloader:
                
                # Reset gradients
                self.optimizer.zero_grad()

                pred = self.model(x)
                loss = self.criterion(pred, y)

                loss.backward()
                self.optimizer.step()

            # Early stopping after each epoch
            if isinstance(x_val, pd.DataFrame) and isinstance(y_val, pd.DataFrame):
                new_val_score = self.score(x_val, y_val)
                if new_val_score > val_score:
                    val_streak += 1
                else:
                    val_streak = 0
                    model_backup = self.model.state_dict()
                val_score = new_val_score

                if val_streak > early_stop_n:
                    self.model.load_state_dict(model_backup)
                    return self.model

            # TODO regularization

        return self.model

        #######################################################################
        #                       ** END OF YOUR CODE **
        #######################################################################

            
    def predict(self, x, pre_proc=True):
        """
        Ouput the value corresponding to an input x.

        Arguments:
            x {pd.DataFrame} -- Raw input array of shape 
                (batch_size, input_size).

        Returns:
            {np.darray} -- Predicted value for the given input (batch_size, 1).

        """

        #######################################################################
        #                       ** START OF YOUR CODE **
        #######################################################################

        # Only preprocess input if specified to allow proprocessed data to also be passed
        if pre_proc:
            x, _ = self._preprocessor(x, training = False)
        tensor_x = torch.Tensor(x)

        return self.model(tensor_x).detach().numpy()


        #######################################################################
        #                       ** END OF YOUR CODE **
        #######################################################################

    def score(self, x, y, mse=True):
        """
        Function to evaluate the model accuracy on a validation dataset.

        Arguments:
            - x {pd.DataFrame} -- Raw input array of shape 
                (batch_size, input_size).
            - y {pd.DataFrame} -- Raw ouput array of shape (batch_size, 1).

        Returns:
            {float} -- Quantification of the efficiency of the model.

        """

        #######################################################################
        #                       ** START OF YOUR CODE **
        #######################################################################

        X, Y = self._preprocessor(x, y, training = False)
        preds = self.predict(X, pre_proc=False)

        if mse:
            return mean_squared_error(Y, preds)
        else:
            return mean_absolute_error(Y, preds)

        #######################################################################
        #                       ** END OF YOUR CODE **
        #######################################################################
        

    def get_params(self,deep=True):
        return  { 'x':self.x,'hidden_layers':self.hidden_layers,'neurons':self.neurons,'learning_rate':self.learning_rate}


    def set_params(self, **parameters):
        for parameter, value in parameters.items():
            setattr(self, parameter, value)

        return self


def save_regressor(trained_model): 
    """ 
    Utility function to save the trained regressor model in part2_model.pickle.
    """
    # If you alter this, make sure it works in tandem with load_regressor
    with open('part2_model.pickle', 'wb') as target:
        pickle.dump(trained_model, target)
    print("\nSaved model in part2_model.pickle\n")


def load_regressor(): 
    """ 
    Utility function to load the trained regressor model in part2_model.pickle.
    """
    # If you alter this, make sure it works in tandem with save_regressor
    with open('part2_model.pickle', 'rb') as target:
        trained_model = pickle.load(target)
    print("\nLoaded model in part2_model.pickle\n")
    return trained_model



def RegressorHyperParameterSearch(x,y,method='exhaustive'):
 
    # Ensure to add whatever inputs you deem necessary to this function
    """
    Performs a hyper-parameter for fine-tuning the regressor implemented 
    in the Regressor class.

    Arguments:
        Add whatever inputs you need.
        
    Returns:
        The function should return your optimised hyper-parameters. 

    """

    #######################################################################
    #                       ** START OF YOUR CODE **
    #######################################################################

    # learning rate (0.000001 - 10 (*10))
    # neurons (5, 30 (+3))
    # hidden layers (1, 5 (+1))
    # early stop n
    
    # maunual exprimentation:
        # mini_batch size
        # max_epochs
        # dropout rate

    hidden_layers_array=np.array([1,2,3,4,5])
    neurons_array=np.array([5,10,15,20,25,30])
    learning_rate_array=np.array([0.0001,0.001,0.01,0.1,1,10])

    parameters = {'hidden_layers':hidden_layers_array,'neurons':neurons_array,'learning_rate':learning_rate_array}

    if method=='exhaustive':
        cv=GridSearchCV(Regressor(x=x),parameters,scoring='neg_mean_squared_error')

    elif method=='random':
        cv=RandomizedSearchCV(Regressor(x=x),parameters,scoring='neg_mean_squared_error',n_iter=30)

    cv.fit(x,y)
    best_params=cv.best_params_


    return best_params['hidden_layers'],best_params['neurons'],best_params['learning_rate'] # Return the chosen hyper parameters

    #######################################################################
    #                       ** END OF YOUR CODE **
    #######################################################################


def example_main():

    # Seed for reproducability
    torch.manual_seed(0)
    np.random.seed(0)

    output_label = "median_house_value"

    data = pd.read_csv("housing.csv") 

    train, test = train_test_split(data, test_size=0.2, shuffle=True)
    test, val = train_test_split(test, test_size=0.5)

    # Spliting input and output
    x_train = train.loc[:, data.columns != output_label]
    y_train = train.loc[:, [output_label]]
    x_val = val.loc[:, data.columns != output_label]
    y_val = val.loc[:, [output_label]]
    x_test = test.loc[:, data.columns != output_label]
    y_test = test.loc[:, [output_label]]

    regressor = Regressor(x_train, nb_epoch = 10)
    regressor.fit(x_train, y_train)

    # Error
    error = regressor.score(x_test, y_test)
    print("\nRegressor error: {}\n".format(error))

    print("\nPerforming Hyper Parameter Tuning")
    best_hidden_layers,best_neurons,best_learning_rate=RegressorHyperParameterSearch(x_train,y_train)
    print('\nBest Params:')
    print('Hidden Layers: ',best_hidden_layers)
    print('Neurons: ',best_neurons)
    print('Learning Rate', best_learning_rate)

    print("\nTraining With Best Params")
    best_regressor=Regressor(x_train,hidden_layers=best_hidden_layers,neurons=best_neurons,learning_rate=best_learning_rate)

    best_regressor.fit(x_train, y_train)
    best_error = best_regressor.score(x_test, y_test)

    print("\nBest Regressor error: {}\n".format(best_error))
    save_regressor(best_regressor)



if __name__ == "__main__":
    example_main()

