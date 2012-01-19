package htm;

import java.util.ArrayList;
import java.util.List;
import java.util.Set;

/**
 * Represent a single dendrite segment that forms synapses (connections) to
 * other cells. Each segment also maintains a boolean flag, sequenceSegment,
 * indicating whether the segment predicts feed-forward input on the next
 * time step. Segments can be either proximal or distal (for spatial pooling
 * or temporal pooling respectively) however the class object itself does not
 * need to know which it ultimately is as they behave identically.  Segments
 * are considered 'active' if enough of its existing synapses are connected
 * and individually active.
 */
public class Segment {
  
  private final List<Synapse> _synapses;
  private boolean _isSequence;
  private float _segActiveThreshold;

  /**
   * Initialize a new Segment with the specified segment activation threshold.
   */
  Segment(int segActiveThreshold) {
    _synapses = new ArrayList<Synapse>();
    _isSequence = false;
    _segActiveThreshold = segActiveThreshold;
  }
  
  /**
   * Set whether or not this segment is a sequence segment.  A sequence segment
   * is defined as having synapses on cells that happened exactly 1 time step
   * in the past (thus the segment indicates a direct sequence).  While a 
   * non-sequence segment indicates a connection further apart in time
   * (something that will eventually happen).
   * @param sequence true to make the segment a sequence segment, false not.
   */
  public void setSequence(boolean sequence) { 
    _isSequence = sequence; 
  }
  
  /**
   * Return whether this segment is a sequence segment.
   * @return true if segment is a sequence segment.
   */
  public boolean isSequence() { 
    return _isSequence; 
  }
  
  /**
   * Return the current number of synapses (cell connections) on this segment.
   * @return the number of synapse connections on this segment.
   */
  public int numSynapses() { 
    return _synapses.size(); 
  }

  /**
   *  Create a new synapse for this segment attached to the specified input source.
   *  @param inputSource: the input source of the synapse to create.
   *  @return the newly created synapse.
   */
  public Synapse createSynapse(AbstractCell inputSource, float initPerm) {
    Synapse newSyn = new Synapse(inputSource, initPerm);
    _synapses.add(newSyn);
    return newSyn;
  }

  /**
   *  Create numSynapses new synapses for this segment attached to the specified
   *  set of learning cells.
   *  @param cells: set of available learning cells to form synapses to.
   *  @param added set will be populated with synapses that were successfully added.
   */
  public void createSynapsesToLearningCells(Set<Cell> cells, 
      Set<Synapse> added) {
    //assume that cells were previously checked to prevent adding
    //synapses to same cell more than once per segment
    for(Cell cell : cells)
      added.add(createSynapse(cell, 0.0f));
  }

  /**
   *  Populate the vector with all the synapses that are currently connected
   *  (those with a permanence value above the threshold).
   */
  public void getConnectedSynapses(List<Synapse> syns) {
    for(Synapse syn : _synapses) {
      if(syn.isConnected())
        syns.add(syn);
    }
  }

  /**
   * Populate the set parameter with the current set of synapses for this segment.
   */
  public void getSynapses(Set<Synapse> syns) {
    syns.addAll(_synapses);
  }

  /**
   * Populate the set reference with all Cells that this segment's synapses
   * are connected (or potentially connected) to.
   */
  public void getSynapseCells(Set<Cell> cells) {
    for(Synapse syn : _synapses) {
      cells.add(syn.getCell());
    }
  }

  /**
   *  Populate the set with all the currently active (firing) synapses on
   *  this segment.
   *  @param connectedOnly: only consider if active if a synapse is connected.
   */
  public void getActiveSynapses(Set<Synapse> syns) {
    for(Synapse syn : _synapses) {
      if(syn.isActive())
        syns.add(syn);
    }
  }
  
  /**
   * Return a count of how many synapses on this segment are active
   * in the current time step.  Only consider synapses which are currently 
   * connected.
   */
  public int getActiveSynapseCount() {
    return getActiveSynapseCount(true);
  }

  /**
   * Return a count of how many synapses on this segment are active
   * in the current time step.  If connectedOnly is true only consider
   * synapses which are currently connected.
   */
  public int getActiveSynapseCount(boolean connectedOnly) {
    int c=0;
    for(Synapse syn : _synapses) {
      if(syn.isActive(connectedOnly))
        ++c;
    }
    return c;
  }

  /**
   *  Populate the set with all the previously active (firing) synapses on
   *  this segment.
   *  @param connectedOnly: only consider if active if a synapse is connected.
   */
  public void getPrevActiveSynapses(Set<Synapse> syns) {
    for(Synapse syn : _synapses) {
      if(syn.wasActive())
        syns.add(syn);
    }
  }

  /**
   * Return a count of how many synapses on this segment were active
   * in the previous time step.  Only consider synapses which are 
   * currently connected.
   */
  public int getPrevActiveSynapseCount() {
    return getPrevActiveSynapseCount(true);
  }
  
  /**
   * Return a count of how many synapses on this segment were active
   * in the previous time step.  If connectedOnly is true only consider
   * synapses which are currently connected.
   */
  public int getPrevActiveSynapseCount(boolean connectedOnly) {
    int c=0;
    for(Synapse syn : _synapses) {
      if(syn.wasActive(connectedOnly))
        ++c;
    }
    return c;
  }

  /**
   * Update all permanence values of each synapse based on current activity.
   * If a synapse is active, increase its permanence, else decrease it.
   */
  public void adaptPermanences() {
    for(Synapse syn : _synapses) {
      if(syn.isActive())
        syn.increasePermanence();
      else
        syn.decreasePermanence();
    }
  }

  /**
   * Update (increase or decrease) all permanence values of each synapse on
   * this segment.
   */
  public void updatePermanences(boolean increase) {
    for(Synapse syn : _synapses) {
      if(increase)
        syn.increasePermanence();
      else
        syn.decreasePermanence();
    }
  }

  /**
   * Update (increase or decrease based on whether the synapse is active)
   * all permanence values of each of the synapses in the specified set.
   */
  public void updatePermanences(Set<Synapse> activeSynapses) {
    for(Synapse syn : _synapses) {
      if(activeSynapses.contains(syn))
        syn.increasePermanence();
      else
        syn.decreasePermanence();
    }
  }

  /**
   * Decrease the permanences of each of the synapses in the set of
   * active synapses that happen to be on this segment.
   */
  public void decreasePermanences(Set<Synapse> activeSynapses) {
    for(Synapse syn : _synapses) {
      if(activeSynapses.contains(syn))
        syn.decreasePermanence();
    }
  }

  /**
   *  This routine returns true if the number of connected synapses on this segment
   *  that are active due to active states at time t is greater than activationThreshold.
   */
  public boolean isActive() {
    int c=0;
    for(Synapse syn : _synapses) {
      if(syn.isActive())
        ++c;
    }
    return c >= _segActiveThreshold;
  }

  /**
   *  This routine returns true if the number of connected synapses on this segment
   *  that were active due to active states at time t-1 is greater than activationThreshold.
   */
  public boolean wasActive() {
    return getPrevActiveSynapseCount() >= _segActiveThreshold;
  }

  /**
   *  This routine returns true if the number of connected synapses on this segment
   *  that were active due to learning states at time t-1 is greater than activationThreshold.
   */
  public boolean wasActiveFromLearning() {
    int c=0;
    for(Synapse syn : _synapses) {
      if(syn.wasActiveFromLearning())
        ++c;
    }
    return c >= _segActiveThreshold;
  }


}
