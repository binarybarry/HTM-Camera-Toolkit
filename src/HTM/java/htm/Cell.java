package htm;

import java.util.ArrayList;
import java.util.HashSet;
import java.util.LinkedList;
import java.util.List;
import java.util.Set;

/**
 * Represents an HTM sequence cell that belongs to a given Column.
 */
public class Cell extends AbstractCell {
  
  private final Column _column;
  private final int _index;
  private final int _id;
  private boolean _isActive;
  private boolean _wasActive;
  private boolean _isPredicting;
  private boolean _wasPredicted;
  private int _predictionSteps = 0;
  private boolean _isLearning;
  private boolean _wasLearning;
  private List<Segment> _segments = new ArrayList<Segment>(5);

  private List<SegmentUpdateInfo> _segmentUpdates = 
    new LinkedList<SegmentUpdateInfo>();

  int MIN_SYNAPSES_PER_SEGMENT_THRESHOLD = 1;

  /**
   *  Create a new Cell belonging to the specified Column. The index is an
   *  integer id to distinguish this Cell from others in the Column.
   */
  Cell(Column column, int index) { 
    _column = column; 
    _index = index;
    _isActive = false;
    _wasActive = false;
    _isPredicting = false;
    _wasPredicted = false;
    _isLearning = false;
    _wasLearning = false;
    int cpc = _column.getRegion().getCellsPerCol();
    _id = (_column.cx()*cpc + _index) + 
          (_column.cy()*cpc*_column.getRegion().getWidth());
  }
  
  @Override
  public int hashCode() {
    return _id;
  }
  
  @Override
  public boolean equals(Object obj) {
    if(obj instanceof Cell) {
      Cell cell = (Cell)obj;
      if(cell.getRegion()==getRegion())
        return cell._id==_id;
    }
    return false;
  }

  public Region getRegion() {
    return _column.getRegion();
  }
  
  @Override
  public boolean isActive() {
    return _isActive;
  }

  @Override
  public boolean wasActive() {
    return _wasActive;
  }

  @Override
  public boolean wasLearning() {
    return _wasLearning;
  }
  
  @Override
  public int ix() {
    return _column.cx();
  }
  
  @Override
  public int iy() {
    return _column.cy();
  }
  
  @Override
  public int gridIndex() {
    return _column.gridIndex();
  }
  
  public int getId() {
    return _id;
  }
  
  /** Return the Cell's index position within its Column. */
  public int getIndex() { return _index; }
  @Override
  public boolean isDistal() { return true; }

  public boolean isLearning() { return _isLearning; }
  public boolean isPredicting() { return _isPredicting; }

  public boolean wasPredicted() { return _wasPredicted; }
  
  /**
   * Return the fewest number of time steps until this Cell
   * believes it will becomes active. The last prediction steps value 
   * represents the fewest number of time steps this Cell believes it will 
   * becomes active in.  This value will often be a count down that approaches 
   * zero as time steps move forward and the Cell gets closer to becoming 
   * activated.  If the Cell is not currently in a predicting state this value 
   * should be ignored.
   * @return the fewest number of time steps until this Cell believes it will
   * becomes active.
   */
  public int getPredictionSteps() { 
    return _predictionSteps; 
  }

  void setActive(boolean active) { _isActive = active; }
  void setLearning(boolean learning) { _isLearning = learning; }
  
  /**
   * Toggle whether this Cell is currenty in the predicting state or not.
   * If the Cell enters the predicting state it will also cache the value of
   * the prediction steps for the active segment causing this Cell to predict.
   * If there are more than 1 such segment, we cache the value of the least
   * number of time steps until an activation occurs.  The cache value will
   * only reset each time the Cell enters a new predicting state.
   * @param predicting true if the Cell is now predicting, false if it no
   * longer is.
   */
  void setPredicting(boolean predicting) { 
    _isPredicting = predicting;
    if(_isPredicting) {
      _predictionSteps = Segment.MAX_TIME_STEPS;
      for(Segment seg : _segments) {
        if(seg.isActive() && seg.numPredictionSteps()<_predictionSteps)
          _predictionSteps = seg.numPredictionSteps();
      }
    }
  }
  
  public int numSegments() { return _segments.size(); }
  public int numSegmentUpdates() { return _segmentUpdates.size(); }
  public Segment getSegment(int i) { return _segments.get(i); }
  public Column getColumn() { return _column; }
  
  /**
   * Return the number of segments in this cell of the specified type.
   * Type is either 0=All, 1=sequence, 2=non-sequence.
   */
  public int numSegments(int type) {
    int c=0;
    for(Segment seg : _segments) {
      if(type==0)
        c++;
      else if(type==1 && seg.isSequence())
        c++;
      else if(type==2 && !seg.isSequence())
        c++;
    }
    return c;
  }
  
  /**
   * Return the number of segments in this cell that match the number of
   * predictionSteps. If pass in zero, return count of total segments regardless
   * of predictionSteps.
   */
  int numCellSegments(int predictionSteps) {
    int c=0;
    for(Segment seg : _segments) {
      if(seg.numPredictionSteps()==predictionSteps || predictionSteps==0)
        c++;
    }
    return c;
  }

  /**
   *  Advance this cell to the next time step. The current state of this cell
   *  (active, learning, predicting) will be set as the previous state and the current
   *  state will be reset to no cell activity by default until it can be determined.
   */
  void nextTimeStep() {
    _wasActive = _isActive;
    _wasPredicted = _isPredicting;
    _wasLearning = _isLearning;
    _isActive = false;
    _isPredicting = false;
    _isLearning = false;
    for(Segment seg : _segments)
      seg.nextTimeStep();
  }

  /**
   *  Create a new segment for this Cell. The new segment will initially connect to
   *  at most newSynapseCount synapses randomly selected from the set of cells that
   *  were in the learning state at t-1 (specified by the learningCells parameter).
   *  @param learningCells: the set of available learning cells to add to the segment.
   *  @return the segment that was just created.
   */
  Segment createSegment(Set<Cell> learningCells) {
    Set<Synapse> added = new HashSet<Synapse>();
    Segment newSegment = new Segment(getRegion().getSegActiveThreshold());
    newSegment.createSynapsesToLearningCells(learningCells, added);
    _segments.add(newSegment);
    return newSegment;
  }

  /**
   *  For this cell, return a segment that was active in the previous time
   *  step. If multiple segments were active, sequence segments are given preference.
   *  Otherwise, segments with most activity are given preference.
   */
  Segment getPreviousActiveSegment() {
    List<Segment> activeSegs = new ArrayList<Segment>();
    for(Segment seg : _segments) {
      if(seg.wasActive())
        activeSegs.add(seg);
    }

    if(activeSegs.size()==1) //if only 1 active segment, return it
      return activeSegs.get(0);

    if(activeSegs.size() > 1) {
      //if >1 active segments, sequence segments given priority
      List<Segment> sequenceSegs = new ArrayList<Segment>();
      for(Segment seg : activeSegs) {
        if(seg.isSequence()) {
          sequenceSegs.add(seg);
        }
      }

      if(sequenceSegs.size()==1)
        return sequenceSegs.get(0);
      else if(sequenceSegs.size() > 1) {
        activeSegs.clear();
        for(Segment seg : sequenceSegs)
          activeSegs.add(seg);
      }

      //if multiple possible segments, return segment with most activity
      Segment bestSegment = activeSegs.get(0);
      int mostActiveSyns = bestSegment.getPrevActiveSynapseCount();
      for(Segment seg : activeSegs) {
        int activeSyns = seg.getPrevActiveSynapseCount();
        if(activeSyns > mostActiveSyns) {
          mostActiveSyns = activeSyns;
          bestSegment = seg;
        }
      }
      return bestSegment;
    }

    return null;
  }
  
  /**
   *  Return a SegmentUpdateInfo object containing proposed changes to the specified
   *  segment.  If the segment is None, then a new segment is to be added, otherwise
   *  the specified segment is updated.  If the segment exists, find all active
   *  synapses for the segment (either at t or t-1 based on the 'previous' parameter)
   *  and mark them as needing to be updated.  No new synsapses are added.
   *
   *  These segment updates are only applied when the applySegmentUpdates
   *  method is later called on this Cell.
   */
  SegmentUpdateInfo updateSegmentActiveSynapses(boolean previous, Segment segment) {
    return updateSegmentActiveSynapses(previous, segment, false);
  }

  /**
   *  Return a SegmentUpdateInfo object containing proposed changes to the specified
   *  segment.  If the segment is None, then a new segment is to be added, otherwise
   *  the specified segment is updated.  If the segment exists, find all active
   *  synapses for the segment (either at t or t-1 based on the 'previous' parameter)
   *  and mark them as needing to be updated.  If newSynapses is true, then
   *  Region.newSynapseCount - len(activeSynapses) new synapses are added to the
   *  segment to be updated.  The (new) synapses are randomly chosen from the set
   *  of current learning cells (within Region.localityRadius if set).
   *
   *  These segment updates are only applied when the applySegmentUpdates
   *  method is later called on this Cell.
   */
  SegmentUpdateInfo updateSegmentActiveSynapses(boolean previous, 
      Segment segment, boolean newSynapses) {
    Set<Synapse> activeSyns = new HashSet<Synapse>();
    if(segment!=null) {
      activeSyns = previous ? segment.getPrevActiveSynapses() : 
        segment.getActiveSynapses();
    }

    SegmentUpdateInfo segmentUpdate =
        new SegmentUpdateInfo(this, segment, activeSyns, newSynapses);
    _segmentUpdates.add(segmentUpdate);
    return segmentUpdate;
  }

  /**
   *  This function reinforces each segment in this Cell's SegmentUpdateInfo.
   *  Using the segmentUpdateInfo, the following changes are
   *  performed. If positiveReinforcement is true then synapses on the active
   *  list get their permanence counts incremented by permanenceInc. All other
   *  synapses get their permanence counts decremented by permanenceDec. If
   *  positiveReinforcement is false, then synapses on the active list get
   *  their permanence counts decremented by permanenceDec. After this step,
   *  any synapses in segmentUpdate that do yet exist get added with a permanence
   *  count of initialPerm. These new synapses are randomly chosen from the
   *  set of all cells that have learnState output = 1 at time step t.
   */
  void applySegmentUpdates(boolean positiveReinforcement) {
    for(SegmentUpdateInfo segInfo : _segmentUpdates) {
      Segment segment = segInfo.getSegment();

      if(segment!=null) {
        if(positiveReinforcement)
          segment.updatePermanences(segInfo.getActiveSynapses());
        else
          segment.decreasePermanences(segInfo.getActiveSynapses());
      }

      //add new synapses (and new segment if necessary)
      if(segInfo.getAddNewSynapses() && positiveReinforcement) {
        if(segment==null) {
          if(segInfo.numLearningCells() > 0)//only add if learning cells available
            segment = segInfo.createCellSegment();
        }
        else if(segInfo.numLearningCells() > 0) {
          //add new synapses to existing segment
          segInfo.createSynapsesToLearningCells();
        }
      }
    }

    //delete segment update instances after they are applied
    _segmentUpdates.clear();
  }
  
  /**
   *  For this cell in the previous time step (t-1) find the segment with the 
   *  largest number of active synapses.<p>
   *  However only consider segments that predict activation in the number of 
   *  time steps of the active segment of this cell with the least number of 
   *  steps until activation + 1.  For example if right now this cell is being 
   *  predicted to occur in t+2 at the earliest, then we want to find the best 
   *  segment from last time step that would predict for t+3.<p>
   *  This routine is aggressive in finding the best match. The permanence
   *  value of synapses is allowed to be below connectedPerm.
   *  The number of active synapses is allowed to be below activationThreshold,
   *  but must be above minThreshold. The routine returns that segment.
   *  If no segments are found, then null is returned.
   *  @return the best matching previous segment, or null if none found.
   */
  Segment getBestMatchingPreviousSegment() {
    return getBestMatchingSegment(_predictionSteps+1, true);
  }

  /**
   *  For this cell (at t-1 if previous=True else at t), find the segment (only
   *  consider segments that predict activation in exactly 
   *  <code>numPredictionSteps</code> number of time steps) with the largest 
   *  number of active synapses.<p>
   *  This routine is aggressive in finding the best match. The permanence
   *  value of synapses is allowed to be below connectedPerm.
   *  The number of active synapses is allowed to be below activationThreshold,
   *  but must be above minThreshold. The routine returns that segment.
   *  If no segments are found, then null is returned.
   *  @param numPredictionSteps only consider segments that are predicting
   *  cell activation to occur in exactly this many time steps from now.
   *  @param previous if true only consider active segments from t-1 else 
   *  consider active segments right now.
   */
  Segment getBestMatchingSegment(int numPredictionSteps, boolean previous) {
    Segment bestSegment = null;
    int bestSynapseCount = MIN_SYNAPSES_PER_SEGMENT_THRESHOLD;
    for(Segment seg : _segments) {
      if(seg.numPredictionSteps()==numPredictionSteps) {
        int synCount = 0;
        if(previous)
          synCount = seg.getPrevActiveSynapseCount(false);
        else
          synCount = seg.getActiveSynapseCount(false);

        if(synCount > bestSynapseCount) {
          bestSynapseCount = synCount;
          bestSegment = seg;
        }
      }
    }
    return bestSegment;
  }

  /**
   *  Return true if this cell has a currently active sequence segment.
   */
  public boolean hasActiveSequenceSegment() {
    for(Segment seg : _segments) {
      if(seg.isActive() && seg.isSequence())
        return true;
    }
    return false;
  }

}
