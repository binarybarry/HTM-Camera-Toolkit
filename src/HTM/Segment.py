'''
Created on Jan 20, 2011

@author: Barry Maturkanich
'''

from HTM.Synapse import Synapse

class Segment(object):
  """
  Represent a single dendrite segment that forms synapses (connections) to other cells.
  Each segment also maintains a boolean flag, sequenceSegment, indicating 
  whether the segment predicts feed-forward input on the next time step.
  Segments can be either proximal or distal (for spatial pooling or temporal pooling
  respectively) however the class object itself does not need to know which
  it ultimately is as they behave identically.  Segments are considered 'active' 
  if enough of its existing synapses are connected and individually active.
  """
  
  def __init__(self, segActiveThreshold):
    self.synapses = []
    self.isSequence = False
    self.segActiveThreshold = segActiveThreshold
  
  def addSynapse(self, synapse):
    """ Add the specified synapse object to this segment. """
    self.synapses.append(synapse)
  
  def createSynapse(self, inputSource):
    """ 
    Create a new synapse for this segment attached to the specified input source. 
    @param inputSource: the input source of the synapse to create.
    @return the newly created synapse.
    """
    newSyn = Synapse(inputSource)
    self.synapses.append(newSyn)
    return newSyn
    
  def createSynapsesToLearningCells(self, synapseCells):
    """
    Create numSynapses new synapses for this segment attached to the specified
    learning cells.
    @param synapseCells: list of available learning cells to form synapses to.
    @return the list of synapses that were successfully added.
    """
    #assume that synapseCells were previously checked to prevent adding   
    #synapses to same cell more than once per segment
    newSyns = []
    for cell in synapseCells:
      newSyns.append(self.createSynapse(cell))
    return newSyns
  
  def getConnectedSynapses(self):
    """
    Return a list of all the synapses that are currently connected (those with a
    permanence value above the threshold).
    """
    return [syn for syn in self.synapses if syn.isConnected]
  
  def getActiveSynapses(self, connectedOnly=True):
    """
    Return a list of all the currently active (firing) synapses on this segment.
    @param connectedOnly: only consider if active if a synapse is connected.
    """
    return [syn for syn in self.synapses if syn.isActive(connectedOnly)]
  
  def getPrevActiveSynapses(self, connectedOnly=True):
    """
    Return a list of all the previously active (firing) synapses on this segment.
    @param connectedOnly: only consider if active if a synapse is connected.
    """
    return [syn for syn in self.synapses if syn.wasActive(connectedOnly)]
  
  def isActive(self):
    """
    This routine returns true if the number of connected synapses on this segment 
    that are active due to active states at time t is greater than activationThreshold. 
    """
    return len(self.getActiveSynapses()) >= self.segActiveThreshold
  
  def wasActive(self):
    """
    This routine returns true if the number of connected synapses on this segment 
    that were active due to active states at time t-1 is greater than activationThreshold. 
    """
    return len(self.getPrevActiveSynapses()) >= self.segActiveThreshold
  
  def wasActiveFromLearning(self):
    """
    This routine returns true if the number of connected synapses on this segment 
    that were active due to learning states at time t-1 is greater than activationThreshold. 
    """
    learningSyns = [syn for syn in self.getPrevActiveSynapses() if syn.wasActiveFromLearning()]
    return len(learningSyns) >= self.segActiveThreshold
  