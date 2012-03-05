#  A group of useful functions that don't belong to anything in particular

import os
import subprocess as SP
import numpy as N
import inspect 
import copy

class UndefinedError(Exception): pass
    
def save_mat_text(mat, filename, delimiter=' '):
    """Writes a 1D or 2D array or matrix to a text file
    
    delimeter separates the elements
    Complex data is saved in the following format (as floats)::
    
      real00 imag00 real01 imag01 ...
      real10 imag10 real11 imag11 ...
      ...
  
    It can easily be read in Matlab (provided .m files?). Brandt has written
    these matlab functions.
    """
    # Must cast mat into an array, makes it memory C-contiguous.
    mat_save = N.array(mat)
    
    # If one-dimensional arry, then make a vector of many rows, 1 column
    if mat_save.ndim == 1:
        mat_save = mat_save.reshape((-1,1))
    elif mat_save.ndim > 2:
        raise RuntimeError('Cannot save a matrix with >2 dimensions')

    N.savetxt(filename, mat_save.view(float), delimiter=delimiter)
    
    
def load_mat_text(filename, delimiter=' ', is_complex=False):
    """ Reads a matrix written by write_mat_text, returns an *array*
    
    If the data saved is complex, then is_complex must be set to True.
    If this is not done, the array returned will be real with 2x the 
    correct number of columns.
    """
    # Check the version of numpy, requires version >= 1.6 for ndmin option
    numpy_version = int(N.version.version[2])
    if numpy_version < 6:
        print 'Warning: load_mat_text requires numpy version >= 1.6 '+\
            'but you are running version %d'%numpy_version
    
    if is_complex:
        dtype = complex
    else:
        dtype = float
    mat = N.loadtxt(filename, delimiter=delimiter, ndmin=2)
    if is_complex and mat.shape[1]%2 != 0:
        raise ValueError(('Cannot load complex data, file %s '%filename)+\
            'has an odd number of columns. Maybe it has real data.')
            
    # Cast as an array, copies to make it C-contiguous memory
    return N.array(mat.view(dtype))


def inner_product(field1, field2):
    """ A default inner product for n-dimensional numpy arrays """
    return (field1*field2.conj()).sum()

    
def svd(mat, tol = 1e-13):
    """An SVD that better meets our needs.
    
    Returns U,E,V where U.E.V* = mat. It truncates the matrices such that
    there are no ~0 singular values. U and V are numpy.matrix's, E is
    a 1D numpy.array.
    """
    
    import copy
    mat_copied = N.mat(copy.deepcopy(mat))
    
    U, E, V_comp_conj = N.linalg.svd(mat_copied, full_matrices=0)
    V = N.mat(V_comp_conj).H
    U = N.mat(U)
    
    # Only return sing vals above the tolerance
    num_nonzeros = (abs(E) > tol).sum()
    if num_nonzeros > 0:
        U=U[:,:num_nonzeros]
        V=V[:,:num_nonzeros]
        E=E[:num_nonzeros]
    
    return U,E,V


def get_file_list(directory, file_extension=None):
    """Returns list of files in directory with file_extension"""
    files = os.listdir(directory)
    if file_extension is not None:
        if len(file_extension) == 0:
            print 'Warning: gave an empty file extension'
        filtered_files = []
        for f in files:
            if f[-len(file_extension):] == file_extension:
                filtered_files.append(f)
        return filtered_files
    else:
        return files
        

def get_data_members(obj):
    """ Returns a dictionary containing data members of an object"""
    pr = {}
    for name in dir(obj):
        value = getattr(obj, name)
        if not name.startswith('__') and not inspect.ismethod(value):
            pr[name] = value
    return pr


def sum_arrays(arr1,arr2):
    """Used for allreduce command, may not be necessary"""
    return arr1+arr2

    
def sum_lists(list1,list2):
    """Sum the elements of each list, return a new list.
    
    This function is used in MPI reduce commands, but could be used
    elsewhere too"""
    assert len(list1)==len(list2)
    return [list1[i]+list2[i] for i in xrange(len(list1))]


def solve_Lyapunov(A, Q):
    """Solves equation of form AXA' - X + Q = 0 for X given A and Q
    
    See http://en.wikipedia.org/wiki/Lyapunov_equation
    """
    A = N.array(A)
    Q = N.array(Q)
    if A.shape != Q.shape:
        raise ValueError('A and Q dont have same shape')
    A_flat = A.flatten()
    Q_flat = Q.flatten()
    kron_AA = N.kron(A, A)
    X_flat = N.linalg.solve(N.identity(kron_AA.shape[0]) - kron_AA, Q_flat)
    X = X_flat.reshape((A.shape))
    return X


def drss(num_states, num_inputs, num_outputs):
    #Generates a discrete random state space system
    eig_vals = N.linspace(.9, .95, num_states) 
    eig_vecs = N.random.normal(0, 2., (num_states,num_states))
    A = N.mat(N.real(N.dot(N.dot(N.linalg.inv(eig_vecs), N.diag(eig_vals)), eig_vecs)))
    B = N.mat(N.random.normal(0, 1., (num_states, num_inputs)))
    C = N.mat(N.random.normal(0, 1., (num_outputs, num_states)))
    return A, B, C

def rss(num_states, num_inputs, num_outputs):
    # Create a stable matrix A with specificed e-vals, continuous time
    e_vals = -N.random.random(num_states)
    transformation = N.random.random((num_states, num_states))
    A = N.dot(N.dot(N.linalg.inv(transformation), N.diag(e_vals)), transformation)
    B = N.random.random((num_states, num_inputs))
    C = N.random.random((num_outputs, num_states))
    return A,B,C
        
        
def lsim(A, B, C, D, inputs):
    """
    Simulates a discrete time system with arbitrary inputs. 
    
    inputs: [num_time_steps, num_inputs]
    Returns the outputs, [num_time_steps, num_outputs].
    """
    
    if inputs.ndim == 1:
        inputs = inputs.reshape((len(inputs),1))
    num_steps, num_inputs = inputs.shape
    num_outputs = C.shape[0]
    num_states = A.shape[0]
    #print 'num_states is',num_states,'num inputs',num_inputs,'B shape',B.shape
    if B.shape != (num_states, num_inputs):
        raise ValueError('B has the wrong shape ', B.shape)
    if A.shape != (num_states, num_states):
        raise ValueError('A has the wrong shape ', A.shape)
    if C.shape != (num_outputs, num_states):
        raise ValueError('C has the wrong shape ', C.shape)
    if D == 0:
        D = N.zeros((num_outputs, num_inputs))
    if D.shape != (num_outputs, num_inputs):
        raise ValueError('D has the wrong shape, D=', D)
    
    outputs = [] 
    state = N.mat(N.zeros((num_states,1)))
    
    for time,input in enumerate(inputs):
        #print 'assigning',N.dot(C, state).shape,'into',outputs[time].shape
        input_reshape = input.reshape((num_inputs,1))
        outputs.append((C*state ).squeeze())
        #print 'shape of D*input',N.dot(D,input_reshape).shape
        #Astate = A*state
        #print 'shape of B is',B.shape,'and shape of input is',input.reshape((num_inputs,1)).shape
        state = A*state + B*input_reshape
    
    outputs_array = N.zeros((num_steps, num_outputs))
    for t,out in enumerate(outputs):
        #print 'assigning out.shape',out.shape,'into',outputs_array[t].shape
        #print 'num_outputs',num_outputs
        outputs_array[t] = out

    return outputs_array

    
def impulse(A, B, C, time_step=None, time_steps=None):
    """Generates impulse response outputs for a discrete system, A, B, C.
    
    sample_interval is the interval of time steps between samples,
    Uses format [CB CAB CA**PB CA**(P+1)B ...].
    By default, will find impulse until outputs are below a tolerance.
    time_steps specifies time intervals, must be 1D array of integers.
    No D is included, but can simply be prepended to the output if it is
    non-zero. 
    """
    num_states = A.shape[0]
    num_inputs = B.shape[1]
    num_outputs = C.shape[0]
    if time_steps is None:
        if time_step is None:
            print 'Warning: setting time_step to 1 by default'
            time_step = 1
        tol = 1e-6
        max_time_steps = 1000
        Markovs = [C*B]
        time_steps = [0]
        while (N.amax(abs(Markovs[-1])) > tol or len(Markovs) < 20) and \
            len(Markovs) < max_time_steps:
            time_steps.append(time_steps[-1] + time_step)
            Markovs.append(C * (A**time_steps[-1]) * B)
    else:
        Markovs = []
        for tv in time_steps:
            Markovs.append(C*(A**tv)*B)

    outputs = N.zeros((len(Markovs), num_outputs, num_inputs))
    for time_step,Markov in enumerate(Markovs):
        outputs[time_step] = Markov
    time_steps = N.array(time_steps)
    
    return time_steps, outputs


def load_impulse_outputs(output_paths):
    """Loads impulse outputs with format [t out1 out2 ...]. Used by ERA."""
    num_inputs = len(output_paths)
    # Read the first file to get parameters
    raw_data = load_mat_text(output_paths[0])
    num_outputs = raw_data.shape[1]-1
    if num_outputs == 0:
        raise ValueError('Impulse output data must have at least two columns')
    time_values = raw_data[:, 0]
    num_time_values = len(time_values)
    
    # Now allocate array and read all of the output data
    outputs = N.zeros((num_time_values, num_outputs, num_inputs))
    
    # Load all of the outputs, make sure time_values match for each input impulse file
    for input_num,output_path in enumerate(output_paths):
        raw_data = load_mat_text(output_path)
        time_values_read = raw_data[:,0]
        if not N.allclose(time_values_read, time_values):
            raise ValueError('Time values in %s are inconsistent with other files'%output_path)   
        outputs[:,:,input_num] = raw_data[:,1:]

    return time_values, outputs


#def drss(states, inputs, outputs): return _rss_generate(states, inputs, outputs, 'd')
    
def _rss_generate(states, inputs, outputs, type):
    """Generate a random state space. -stolen from python-control
    
    This does the actual random state space generation expected from rss and
    drss.  type is 'c' for continuous systems and 'd' for discrete systems.
    
    """
    from numpy import all, angle, any, array, concatenate, cos, delete, dot, \
    empty, exp, eye, matrix, ones, pi, poly, poly1d, roots, shape, sin, zeros
    from numpy.random import rand, randn
    from numpy.linalg import inv, det, solve
    from numpy.linalg.linalg import LinAlgError
    #from scipy.signal import lti
    #from slycot import td04ad
    #from lti import Lti
    #import xferfcn
 
    # Probability of repeating a previous root.
    pRepeat = 0.05
    # Probability of choosing a real root.  Note that when choosing a complex
    # root, the conjugate gets chosen as well.  So the expected proportion of
    # real roots is pReal / (pReal + 2 * (1 - pReal)).
    pReal = 0.6
    # Probability that an element in B or C will not be masked out.
    pBCmask = 0.8
    # Probability that an element in D will not be masked out.
    pDmask = 0.3
    # Probability that D = 0.
    pDzero = 0.5

    # Check for valid input arguments.
    if states < 1 or states % 1:
        raise ValueError(("states must be a positive integer.  states = %g." % 
            states))
    if inputs < 1 or inputs % 1:
        raise ValueError(("inputs must be a positive integer.  inputs = %g." %
            inputs))
    if outputs < 1 or outputs % 1:
        raise ValueError(("outputs must be a positive integer.  outputs = %g." %
            outputs))

    # Make some poles for A.  Preallocate a complex array.
    poles = zeros(states) + zeros(states) * 0.j
    i = 0

    while i < states:
        if rand() < pRepeat and i != 0 and i != states - 1:
            # Small chance of copying poles, if we're not at the first or last
            # element.
            if poles[i-1].imag == 0:
                # Copy previous real pole.
                poles[i] = poles[i-1]
                i += 1
            else:
                # Copy previous complex conjugate pair of poles.
                poles[i:i+2] = poles[i-2:i]
                i += 2
        elif rand() < pReal or i == states - 1:
            # No-oscillation pole.
            if type == 'c':
                poles[i] = -exp(randn()) + 0.j
            elif type == 'd':
                poles[i] = 2. * rand() - 1.
            i += 1
        else:
            # Complex conjugate pair of oscillating poles.
            if type == 'c':
                poles[i] = complex(-exp(randn()), 3. * exp(randn()))
            elif type == 'd':
                mag = rand()
                phase = 2. * pi * rand()
                poles[i] = complex(mag * cos(phase), 
                    mag * sin(phase))
            poles[i+1] = complex(poles[i].real, -poles[i].imag)
            i += 2

    # Now put the poles in A as real blocks on the diagonal.
    A = zeros((states, states))
    i = 0
    while i < states:
        if poles[i].imag == 0:
            A[i, i] = poles[i].real
            i += 1
        else:
            A[i, i] = A[i+1, i+1] = poles[i].real
            A[i, i+1] = poles[i].imag
            A[i+1, i] = -poles[i].imag
            i += 2
    # Finally, apply a transformation so that A is not block-diagonal.
    while True:
        T = randn(states, states)
        try:
            A = dot(solve(T, A), T) # A = T \ A * T
            break
        except LinAlgError:
            # In the unlikely event that T is rank-deficient, iterate again.
            pass

    # Make the remaining matrices.
    B = randn(states, inputs)
    C = randn(outputs, states)
    D = randn(outputs, inputs)

    # Make masks to zero out some of the elements.
    while True:
        Bmask = rand(states, inputs) < pBCmask 
        if any(Bmask): # Retry if we get all zeros.
            break
    while True:
        Cmask = rand(outputs, states) < pBCmask
        if any(Cmask): # Retry if we get all zeros.
            break
    if rand() < pDzero:
        Dmask = zeros((outputs, inputs))
    else:
        Dmask = rand(outputs, inputs) < pDmask

    # Apply masks.
    B = B * Bmask
    C = C * Cmask
    D = D * Dmask

    return N.mat(A), N.mat(B), N.mat(C)




