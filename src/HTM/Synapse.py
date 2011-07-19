'''
Created on Jan 20, 2011

@author: Barry Maturkanich
'''

class Synapse(object):
  """ 
  A data structure representing a synapse. Contains a permanence value and the 
  source input index.  Also contains a 'location' in the input space that this synapse
  roughly represents.
  """
  
  #Static parameters that apply to all Region instances
  CONNECTED_PERM = 0.2  #Synapses with permanences above this value are connected.
  PERMANENCE_INC = 0.05 #Amount permanences of synapses are incremented in learning.
  PERMANENCE_DEC = 0.04 #Amount permanences of synapses are decremented in learning.
  INITIAL_PERMANENCE = CONNECTED_PERM #initial permanence for distal synapses
  
  @staticmethod
  def setConnectedPerm(connectedPerm):
    Synapse.CONNECTED_PERM = connectedPerm
    
  def __init__(self, inputSource, permanence=INITIAL_PERMANENCE):
    """
    @param inputSource: object providing source of the input to this synapse (either
    a Column's Cell or a special InputCell.
    @param permanence: the synapses's initial permanence value (0.0-1.0).
    """
    self.inputSource = inputSource
    self.permanence = min(1.0, permanence) #clamp permanence to 1.0
    
  @property
  def isConnected(self):
    return self.permanence >= Synapse.CONNECTED_PERM
  
  def isActive(self, connectedOnly=True):
    """ 
    Return true if this Synapse is active due to the current input. 
    @param connectedOnly: only consider if active if this synapse is connected.
    """
    return self.inputSource.isActive and (self.isConnected or not connectedOnly)
  
  def wasActive(self, connectedOnly=True):
    """ 
    Return true if this Synapse was active due to the previous input at t-1. 
    @param connectedOnly: only consider if active if this synapse is connected.
    """
    return self.inputSource.wasActive and (self.isConnected or not connectedOnly)
  
  def wasActiveFromLearning(self):
    """ 
    Return true if this Synapse was active due to the input previously being
    in a learning state. 
    """
    return self.wasActive() and self.inputSource.wasLearning
  
  def increasePermanence(self, amount=PERMANENCE_INC):
    """ Increases the permanence of this synapse. """
    self.permanence = min(1.0, self.permanence+amount)
    
  def decreasePermanence(self, amount=PERMANENCE_DEC):
    """ Decreases the permanence of this synapse. """
    self.permanence = max(0.0, self.permanence-amount)
