from fieldoperations import FieldOperations
import util
import numpy as N
import util 

class POD(object):
    """
    Proper Orthogonal Decomposition
    
    Generate orthonormal modes from simulation snapshots.
    
    """
        
    def __init__(self, load_field=None, save_field=None, save_mat=\
        util.save_mat_text, inner_product=None, maxFieldsPerNode=None, 
        numNodes=1, load_mat=util.load_mat_text, verbose=True):
        """
        POD constructor
        
        """
        self.fieldOperations = FieldOperations(load_field=load_field, 
            save_field=save_field,
            save_mat=save_mat, inner_product=inner_product, maxFieldsPerNode=\
            maxFieldsPerNode, numNodes=numNodes, verbose=verbose)
        
        self.mpi = util.MPIInstance
        self.save_mat = save_mat
        self.load_mat = load_mat
        self.verbose = verbose
     
     
     
    def load_decomp(self, singVecsPath, singValsPath):
        """
        Loads the decomposition matrices from file. 
        """
        if self.load_mat is None:
            raise UndefinedError('Must specify a load_mat function')
        if self.mpi.isRankZero():
            self.singVecs = self.load_mat(singVecsPath)
            self.singVals = N.squeeze(N.array(self.load_mat(singValsPath)))
        else:
            self.singVecs = None
            self.singVals = None
        if self.mpi.parallel:
            self.singVecs = self.mpi.comm.bcast(self.singVecs, root=0)
            self.singVals = self.mpi.comm.bcast(self.singVals, root=0)
 
    def save_correlation_mat(self, correlationMatPath):
        if self.save_mat is None and self.mpi.isRankZero():
            raise util.UndefinedError('save_mat is undefined, cant save')
        if self.mpi.isRankZero():
            self.save_mat(self.correlationMat, correlationMatPath)
        
    def save_decomp(self, singVecsPath, singValsPath):
        """Save the decomposition matrices to file."""
        if self.save_mat is None and self.mpi.isRankZero():
            raise util.UndefinedError('save_mat is undefined, cant save')
            
        if self.mpi.isRankZero():
            self.save_mat(self.singVecs, singVecsPath)
            self.save_mat(self.singVals, singValsPath)


    def compute_decomp(self, correlationMatPath=None, singVecsPath=None, 
        singValsPath=None, snapPaths=None):
        """
        Compute POD decomposition
        """
        if correlationMatPath is not None:
            if self.load_mat is None:
                raise util.UndefinedError('load_mat is undefined')
            elif self.mpi.isRankZero():
                self.correlationMat = self.load_mat(correlationMatPath)
        elif snapPaths is not None:
            self.snapPaths = snapPaths
            self.correlationMat = self.fieldOperations.compute_symmetric_inner_product_mat(
                self.snapPaths)
        else:
            raise util.UndefinedError('Must provide either snap paths or '+\
                'correlation matrix path to pod.compute_decomp')
                
        if self.mpi.isRankZero():
            self.singVecs, self.singVals, dummy = util.svd(self.correlationMat)
            del dummy
        else:
            self.singVecs = None
            self.singVals = None
        if self.mpi.isParallel():
            self.singVecs = self.mpi.comm.bcast(self.singVecs, root=0)
            self.singVals = self.mpi.comm.bcast(self.singVals, root=0)
            
            
    def compute_modes(self, modeNumList, modePath, indexFrom=1, snapPaths=None):
        """
        Computes the POD modes and saves them to file.
        
        modeNumList
          Mode numbers to compute on this processor. This 
          includes the indexFrom, so if indexFrom=1, examples are:
          [1,2,3,4,5] or [3,1,6,8]. The mode numbers need not be sorted,
          and sorting does not increase efficiency. 
          Repeated mode numbers is not guaranteed to work. 

        modePath
          Full path to mode location, e.g /home/user/mode_%d.txt.

        indexFrom
          Choose to index modes starting from 0, 1, or other.

        self.RSingVecs, self.singVals must exist or an UndefinedError.

        """
        if self.singVecs is None:
            raise util.UndefinedError('Must define self.singVecs')
        if self.singVals is None:
            raise util.UndefinedError('Must define self.singVals')
        if snapPaths is not None:
            self.snapPaths = snapPaths

        buildCoeffMat = N.mat(self.singVecs) * N.mat(N.diag(self.singVals **\
            -0.5))

        self.fieldOperations._compute_modes(modeNumList, modePath, self.snapPaths, 
            buildCoeffMat, indexFrom=indexFrom)
    



