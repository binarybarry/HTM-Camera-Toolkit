package htm;

import java.util.ArrayList;
import java.util.Collections;
import java.util.HashSet;
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
  
  static final int MAX_TIME_STEPS = 10; //most prediction steps to track
  
  private final List<Synapse> _synapses;
  private boolean _isSequence;
  private int _predictionSteps;
  private final float _segActiveThreshold;
  
  private boolean _isActive;
  private boolean _wasActive;
  private Set<Synapse> _activeSynapses;
  private Set<Synapse> _prevSynapses;
  
  /**
   * Initialize a new Segment with the specified segment activation threshold.
   */
  Segment(int segActiveThreshold) {
    _synapses = new ArrayList<Synapse>();
    _isSequence = false;
    _segActiveThreshold = segActiveThreshold;
    _isActive = false;
    _wasActive = false;
    _activeSynapses = new HashSet<Synapse>();
    _prevSynapses = new HashSet<Synapse>();
  }
  
  /**
   * Advance this segment to the next time step.  The current state of this
   * segment (active, number of synapes) will be set as the previous state and
   * the current state will be reset to no cell activity by default until it
   * can be determined.
   */
  void nextTimeStep() {
    _wasActive = _isActive;
    _isActive = false;
    _prevSynapses.clear();
    _prevSynapses.addAll(_activeSynapses);
    _activeSynapses.clear();
  }
  
  /**
   * Process this segment for the current time step.  Processing will determine
   * the set of active synapses on this segment for this time step.  From there
   * we will determine if this segment is active if enough active synapses
   * are present.  This information is then cached for the remainder of the
   * Region's processing for the time step.  When a new time step occurs, the
   * Region will call nextTimeStep() on all cells/segments to cache the 
   * information as what was previously active.
   */
  public void processSegment() {
    _activeSynapses.clear();
    for(Synapse syn : _synapses) {
      if(syn.isActive())
        _activeSynapses.add(syn);
    }
    _isActive = _activeSynapses.size() >= _segActiveThreshold;
  }
  
  /**
   * Set whether or not this segment is a sequence segment.  A sequence segment
   * is defined as having synapses on cells that happened exactly 1 time step
   * in the past (thus the segment indicates a direct sequence).  While a 
   * non-sequence segment indicates a connection further apart in time
   * (something that will eventually happen).
   * @param sequence true to make the segment a sequence segment, false not.
   */
  private void setSequence(boolean sequence) { 
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
   * Define the number of time steps in the future an activation will occur
   * in if this segment becomes active.  For example if the segment is intended 
   * to predict activation in the very next time step (t+1) then this value is 
   * 1. If the value is 2 this segment is said to predict its Cell will activate
   * in 2 time steps (t+2) etc.  By definition if a segment is a sequence
   * segment it has a value of 1 for prediction steps.
   * @param steps the number of steps into the future an activation will occur
   * in if this segment becomes active.
   */
  public void setNumPredictionSteps(int steps) {
    _predictionSteps = Math.min(Math.max(1, steps), MAX_TIME_STEPS);
    setSequence(_predictionSteps==1);
  }
  
  /**
   * Return the number of time steps in the future an activation will occur
   * in if this segment becomes active.  For sequence segments this value will
   * be 1 (for t+1 activation prediction).
   * @return the number of steps into the future an activation will occur
   * in if this segment becomes active.
   */
  public int numPredictionSteps() {
    return _predictionSteps;
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
   *  Return the set of all the currently active (connected and firing) 
   *  synapses on this segment.
   */
  public Set<Synapse> getActiveSynapses() {
    return Collections.unmodifiableSet(_activeSynapses);
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
    if(connectedOnly)
      return _activeSynapses.size();
    
    int c=0;
    for(Synapse syn : _synapses) {
      if(syn.isActive(connectedOnly))
        ++c;
    }
    return c;
  }

  /**
   *  Return the set of all the previously active (firing) synapses on
   *  this segment.
   */
  public Set<Synapse> getPrevActiveSynapses() {
    return Collections.unmodifiableSet(_prevSynapses);
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
    if(connectedOnly)
      return _prevSynapses.size();
    
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
    return _isActive;
  }

  /**
   *  This routine returns true if the number of connected synapses on this segment
   *  that were active due to active states at time t-1 is greater than activationThreshold.
   */
  public boolean wasActive() {
    return _wasActive;
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
  
  /**
   * Return the assigned segment activation threshold.  The threshold represents
   * how many synapses must be active on a segment for it to be active.
   */
  public float getSegmentActiveThreshold() {
    return _segActiveThreshold;
  }
}
