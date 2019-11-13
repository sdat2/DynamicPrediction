#!/usr/bin/env python
# coding: utf-8

import numpy as np
import matplotlib.pyplot as plt
from scipy.integrate import solve_ivp
from scipy.integrate import odeint
from scipy.integrate import RK45

# # Set up three layer Lorenz 95 model as in D&B paper

# code based on version from https://en.wikipedia.org/wiki/Lorenz_96_model
# and ammended to match D&B paper - not sure how to initialise, paper doesn't say, so have gone 
# with forcing values for x variables and random for y and z variables.

I = 8
J = 8
K = 8

F = 20.  # forcing

h = 1.
c = 10.
b = 10.
e = 10.
d = 10.

gz = 1.

x0 = np.zeros((K)) # ??
x0[:]=F
y0 = np.random.rand(J,K) # Random??
z0 = np.random.rand(I,J,K) # Random??
state0  = np.concatenate((x0,y0.reshape(J*K,),z0.reshape(I*J*K,)))

t_int = 0.005

# Define Lorenz model 
def Lorenz96(t, state):
    # unpack input array
    x=state[0:K]
    y=state[K:J*K+K]
    z=state[J*K+K:I*J*K+J*K+K]
    y=y.reshape(J,K)
    z=z.reshape(I,J,K)
    
    # compute state derivatives
    dx = np.zeros((K))
    dy = np.zeros((J,K))
    dz = np.zeros((I,J,K))
    # Do the X variable
    # first the 3 edge cases: i=1,2,K-1
    dx[0]   = x[K-1] * (x[1] - x[K-2]) - x[0]   + F - h*c/b * sum(y[:,0])
    dx[1]   =   x[0] * (x[2] - x[K-1]) - x[1]   + F - h*c/b * sum(y[:,1])  
    dx[K-1] = x[K-2] * (x[0] - x[K-3]) - x[K-1] + F - h*c/b * sum(y[:,K-1])  
    # then the general case
    for k in range(2, K-1):
        dx[k] = x[k-1] * (x[k+1] - x[k-2]) - x[k] + F - h*c/b * sum(y[:,k])

    # Do the Y variable
    # first the 3 edge cases: i=1,2,K-1
    for k in range(0,K):
        dy[0,k]   = - c*b * y[1,k]   * ( y[2,k] - y[J-1,k] ) - c * y[0,k]    + h*c/b * x[k] - h*e/d * sum(z[:,0,k])
        dy[J-2,k] = - c*b * y[J-1,k] * ( y[0,k] - y[J-3,k] ) - c * y[J-2,k]  + h*c/b * x[k] - h*e/d * sum(z[:,J-2,k])
        dy[J-1,k] = - c*b * y[0,k]   * ( y[1,k] - y[J-2,k] ) - c * y[J-1,k]  + h*c/b * x[k] - h*e/d * sum(z[:,J-1,k])
        # then the general case
        for j in range(1, J-2):
            dy[j,k] = - c*b * y[j+1,k] * ( y[j+2,k] - y[j-1,k] ) - c * y[j,k]  + h*c/b * x[k] - h*e/d * sum(z[:,j,k])

    # Do the Z variable
    # first the 3 edge cases: i=1,2,K-1
    for k in range(0,K):
        for j in range (0,J):
            dz[0,j,k]   = e*d * z[I-1,j,k] * ( z[1,j,k] - z[I-2,j,k] ) - gz*e * z[0,j,k]   + h*e/d * y[j,k]
            dz[1,j,k]   = e*d * z[0,j,k]   * ( z[2,j,k] - z[I-1,j,k] ) - gz*e * z[1,j,k]   + h*e/d * y[j,k]
            dz[I-1,j,k] = e*d * z[I-2,j,k] * ( z[0,j,k] - z[I-3,j,k] ) - gz*e * z[I-1,j,k] + h*e/d * y[j,k]
            # then the general case
            for i in range(2,I-1):
                dz[i,j,k] = e*d * z[i-1,j,k] * ( z[i+1,j,k] - z[i-2,j,k] ) - gz*e * z[i,j,k] + h*e/d * y[j,k]

    # return the state derivatives
    # reshape and cat into single array
    d_state = np.concatenate((dx,dy.reshape(J*K,),dz.reshape(I*J*K,)))
    
    return d_state


######################
# Run outputting every time step (t_int) for first 16 MTUs to use as truth for validation/comparison.

state0  = np.concatenate((x0,y0.reshape(J*K,),z0.reshape(I*J*K,)))

filename='Lorenz_truth.txt'
file = open(filename, 'w')

t_span  = np.arange(0, 16., t_int)
state   = odeint(Lorenz96, state0, t_span, tfirst=True)
for t in range(len(t_span)):
   [file.write(str(state[t,k])+' ') for k in range(K)]
   file.write('\n')

file.close()

## Run Lorenz integrator and write data to file
## Output every MTU, rather than every t_int, so we have 'independant'(ish) samples
#MTUs = 2000000 
##MTUs = 4 #small set for testing!
#
#filename='Lorenz_training_set.txt'
## ensure file is empty
#file = open(filename, 'w')
#file.close()
#
#f_step=0
#for step in range(MTUs):
#   # run Lorenz integrator for 1MTU
#   t_start = f_step
#   t_end   = f_step+1
#   t_span  = np.arange(t_start, t_end+t_int, t_int)
#   state   = odeint(Lorenz96, state0, t_span, tfirst=True)
#   # write to the file the 1st, 2nd, 3rd t_int outputs
#   file = open(filename, 'a')
#   [file.write(str(state[0,k])+' ') for k in range(K)]
#   file.write('\n')
#   [file.write(str(state[1,k])+' ') for k in range(K)]
#   file.write('\n')
#   [file.write(str(state[2,k])+' ') for k in range(K)]
#   file.write('\n')
#   file.close()
#   # take last t_int values and save for input for next MTU
#   state0  = state[-1,:]
#   f_step = f_step+1
