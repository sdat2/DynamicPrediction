#!/usr/bin/env python
# coding: utf-8

# Script to train various Networks to learn Lorenz model dynamics for various different loss functions
# Script taken from D&B paper supplematary info and modified

import numpy as np
import matplotlib.pyplot as plt
import torch
import torch.nn as nn
import pickle
from torch.utils import data
from torch.utils.data import Dataset, DataLoader
import torch.optim as optim

device = 'cuda' if torch.cuda.is_available() else 'cpu'
print('Using device:', device)
print()

K = 8
t_int = 0.005
n_run=169000
n_run=10

#################################################

## Read in input-output training pairs 
file_train = 'Lorenz_full_save.txt'

data_list_tm1 = []
data_list_t = []
data_list_tp10 = []
data_list_tp100 = []

file = open(file_train, 'r')
for i in range(n_run):
    a_str = file.readline() ;  data_list_tm1.append(a_str.split())
    a_str = file.readline() ;  data_list_t.append(a_str.split())
    for j in range(8):  # skip 8 lines
       a_str = file.readline()
    a_str = file.readline() ;  data_list_tp10.append(a_str.split())
    for j in range(89):  # skip 89 lines
       a_str = file.readline()
    a_str = file.readline() ;  data_list_tp100.append(a_str.split())
    for j in range(200-4-89-8):  # Take samples 200 steps apart to give some independence
       a_str = file.readline()
    
file.close()

x_tm1_data   = np.array(data_list_tm1)
x_t_data     = np.array(data_list_t)
x_tp10_data  = np.array(data_list_tp10)
x_tp100_data = np.array(data_list_tp100)

del(data_list_tm1)
del(data_list_t)
del(data_list_tp10)
del(data_list_tp100)

tm1_train_all = np.zeros((K*n_run,8))
x_tm1_train   = np.zeros((K*n_run,4))
x_t_train     = np.zeros((K*n_run,1))
x_tp10_train  = np.zeros((K*n_run,1))
x_tp100_train = np.zeros((K*n_run,1))
K_val         = np.zeros((K*n_run,1))


print(x_tm1_train.shape)
print(x_tm1_data.shape)

n_count = -1
for i in range(n_run):
    for j in range(8):
        n_count = n_count+1
        n1=(j-2)%8
        x_tm1_train[n_count,0] = x_tm1_data[i,n1]  
        n2=(j-1)%8
        x_tm1_train[n_count,1] = x_tm1_data[i,n2]        
        # i,j point itself
        x_tm1_train[n_count,2] = x_tm1_data[i,j]   
        n3=(j+1)%8
        x_tm1_train[n_count,3] = x_tm1_data[i,n3]
 
        x_t_train[n_count,0] = x_t_data[i,j]    
        x_tp10_train[n_count,0]  = x_tp10_data[i,j]    
        x_tp100_train[n_count,0] = x_tp100_data[i,j]    

        tm1_train_all[n_count,:]=x_tm1_data[i,:]
        K_val[n_count,0] = int(j)

del(x_tm1_data)
del(x_t_data)
del(x_tp10_data)
del(x_tp100_data)

#Taken from D&B script...I presume this is a kind of 'normalisation'
max_train = 30.0
min_train = -20.0

tm1_train_all = torch.FloatTensor(2.0*(tm1_train_all-min_train)/(max_train-min_train)-1.0)
x_tm1_train   = torch.FloatTensor(2.0*(  x_tm1_train-min_train)/(max_train-min_train)-1.0)
x_t_train     = torch.FloatTensor(2.0*(    x_t_train-min_train)/(max_train-min_train)-1.0)
x_tp10_train  = torch.FloatTensor(2.0*( x_tp10_train-min_train)/(max_train-min_train)-1.0)
x_tp100_train = torch.FloatTensor(2.0*(x_tp100_train-min_train)/(max_train-min_train)-1.0)

print(tm1_train_all.shape)
print(x_t_train.shape)
no_samples=x_t_train.shape[0]
print('no samples ; ',+no_samples)
#################################################

# Store data as Dataset
class LorenzTrainingsDataset(data.Dataset):
    """Lorenz Training dataset."""

    def __init__(self, tm1_train_all, x_tm1_train, x_t_train, x_tp10_train, x_tp100_train, K_val):
        self.tm1_train_all = tm1_train_all
        self.x_tm1_train   = x_tm1_train
        self.x_t_train     = x_t_train
        self.x_tp10_train  = x_tp10_train
        self.x_tp100_train = x_tp100_train
        self.K_val       = K_val

    def __getitem__(self, index):
	
        sample_tm1_all = tm1_train_all[index,:]
        sample_x_tm1   = x_tm1_train[index,:]
        sample_x_t     = x_t_train[index,:]
        sample_x_tp10  = x_tp10_train[index,:]
        sample_x_tp100 = x_tp100_train[index,:]
        sample_K_val   = K_val[index,:]

        return (sample_tm1_all, sample_x_tm1, sample_x_t, sample_x_tp10, sample_x_tp100, sample_K_val)

    def __len__(self):
        return x_t_train.shape[0]


# instantiate the dataset
train_dataset = LorenzTrainingsDataset(tm1_train_all, x_tm1_train, x_t_train, x_tp10_train, x_tp100_train, K_val)

trainloader = torch.utils.data.DataLoader(train_dataset, batch_size=128, shuffle=True, num_workers=4)


# ### Set up NN's

# Define matching sequential NNs

h_1ts = nn.Sequential(nn.Linear( 4, 20), nn.Tanh(), 
                   nn.Linear(20, 20), nn.Tanh(), 
                   nn.Linear(20, 20), nn.Tanh(), 
                   nn.Linear(20, 1))
h_10ts  = pickle.loads(pickle.dumps(h_1ts))
h_100ts = pickle.loads(pickle.dumps(h_1ts))

h_1ts   = h_1ts.to(device)
h_10ts  = h_10ts.to(device)
h_100ts = h_100ts.to(device)

no_epochs=200   # in D&B paper the NN's were trained for at least 200 epochs

########################################
#Print('Train to first order objective')
#
#Opt_1ts = torch.optim.Adam(h_1ts.parameters(), lr=0.001) # Use adam optimiser for now, as simple to set up for first run
#
#Train_loss = []
#For epoch in range(no_epochs):
#   for tm1_all, tm1, t, tp10, tp100, K in trainloader:
#      tm1_all = tm1_all.to(device).float()
#      tm1     = tm1.to(device).float()
#      t       = t.to(device).float()
#      h_1ts.train()
#      opt_1ts.zero_grad()
#      estimate = tm1[2] + h_1ts(tm1[:])
#      loss = (estimate - t[0]).abs().mean()  # mean absolute error
#      loss.backward()
#      train_loss.append(loss.item())
#      opt_1ts.step()
#
#Plt.figure()
#Plt.plot(train_loss)
#Plt.savefig('/data/hpcdata/users/racfur/DynamicPrediction/LorenzOutputs/trainloss_1ts_'+str(n_run)+'.png')
#
#Torch.save({'h_1ts_state_dict': h_1ts.state_dict(),
#            'opt_1ts_state_dict': opt_1ts.state_dict(),
#	   }, '/data/hpcdata/users/racfur/DynamicPrediction/LorenzOutputs/1ts_model_'+str(n_run)+'.pt')
#
########################################
#Define loss function which trains based on various lead times. Need to use an iterator - stick with AB1 for now.

def AB_1st_order_integrator(ref_state, h, n_steps):
    # write iterator to output state at some future time (note does not store whole state)
    out0 = torch.tensor(np.zeros((8)))
    state_in = torch.tensor(np.zeros((8,4)))
    state = ref_state[:]
    for j in range(n_steps):
        for k in range(8):
            n1=(k-2)%8
            print('n1: '+str(n1))
            print('k ; '+str(k))
            print(state)
            print(state[n1])
            state_in[k,0] = state[n1]
            n2=(k-1)%8
            state_in[k,1] = state[n2]
            state_in[k,2] = state[k]
            n3=(k+1)%8
            state_in[k,3] = state[n3]
        out0 = h(torch.FloatTensor(state_in))
        for k in range(8):
            state[k] = state[k] + out0[k]
    return(state)

########################################

print('Train NN to match 1 and 10 time steps ahead')
opt_10ts = torch.optim.Adam(h_10ts.parameters(), lr=0.001) # Use adam optimiser for now, as simple to set up for first run

alpha=1  # balance between optimising for 1 time step ahead, vs 10 time steps ahead.

train_loss = []
for epoch in range(no_epochs):
   for tm1_all, tm1, t, tp10, tp100, K in trainloader:
      tm1_all = tm1_all.to(device).float()
      tm1     = tm1.to(device).float()
      t       = t.to(device).float()
      tp10    = tp10.to(device).float()
      tp100   = tp100.to(device).float()
      K = K.to(device).int()
      h_10ts.train()
      opt_10ts.zero_grad()
      estimate1 = tm1[2] + h_10ts(tm1[:])
      #print(K)
      #k = int(['K_value'][0])
      estimate10  = AB_1st_order_integrator(tm1_all[:], h_10ts, 10)[K]
      loss = ( (estimate1 - t[0]) + alpha*(estimate10 - tp10[0]) ).abs().mean()
      loss.backward()
      train_loss.append(loss.item())
      opt_10ts.step()

plt.figure()
plt.plot(train_loss)
plt.savefig('/data/hpcdata/users/racfur/DynamicPrediction/LorenzOutputs/trainloss_10ts_'+str(n_run)+'.png')

torch.save({'h_10ts_state_dict': h_10ts.state_dict(),
            'opt_10ts_state_dict': opt_10ts.state_dict(),
	    }, '/data/hpcdata/users/racfur/DynamicPrediction/LorenzOutputs/10ts_model_'+str(n_run)+'.pt')

########################################

print('Train NN to match 1, 10 and 100 time steps ahead')
opt_100ts = torch.optim.Adam(h_100ts.parameters(), lr=0.001) # Use adam optimiser for now, as simple to set up for first run

alpha=1  # balance between optimising for 1 time step ahead, vs 10 time steps ahead.
beta =1  # balance between optimising for 1 time step ahead, vs 100 time steps ahead.

train_loss = []
for epoch in range(no_epochs):
   for tm1_all, tm1, t, tp10, tp100, K in trainloader:
      tm1_all = tm1_all.to(device).float()
      tm1     = tm1.to(device).float()
      t       = t.to(device).float()
      tp10    = tp10.to(device).float()
      tp100   = tp100.to(device).float()
      K       = K.to(device).int()
      h_100ts.train()
      opt_100ts.zero_grad()
      estimate1 = tm1[2] + h_10ts(tm1[:])
      k = int(K)
      print(k)
      estimate10  = AB_1st_order_integrator(tm1_all[:], h_100ts, 10)[K]
      estimate100 = AB_1st_order_integrator(tm1_all[:], h_100ts, 100)[k]
      loss = ( (estimate1 - t[0]) + alpha*(estimate10 - tp10[0]) + beta*(estimate100 - tp100[0]) ).abs().mean()
      loss.backward()
      train_loss.append(loss.item())
      opt_100ts.step()

plt.figure()
plt.plot(train_loss)
plt.savefig('/data/hpcdata/users/racfur/DynamicPrediction/LorenzOutputs/trainloss_100ts_'+str(n_run)+'.png')

torch.save({'h_100ts_state_dict': h_100ts.state_dict(),
            'opt_100ts_state_dict': opt_100ts.state_dict(),
	    }, '/data/hpcdata/users/racfur/DynamicPrediction/LorenzOutputs/100ts_model_'+str(n_run)+'.pt')

########################################