package htm;

import java.util.ArrayList;
import java.util.List;

/**
 * Column.cpp
 *
 *  Created on: Sep 22, 2011
 *      Author: barry
 *
 * Represents a single column of cells within an HTM Region.
 */
public class Column {
  
  private final Region _region; //parent region
  private Cell[] _cells;    //Sequence cells
  private boolean _isActive;  //whether or not this Column is currently active.

  //The list of potential synapses and their permanence values.
  private final Segment _proximalSegment;

  //The boost value for column c as computed during learning.
  //used to increase the overlap value for inactive columns.
  private float _boost;

  //A sliding average representing how often column c has been active
  //after inhibition (e.g. over the last 1000 iterations).
  private float _activeDutyCycle;

  //A sliding average representing how often column c has had
  //significant overlap (i.e. greater than minOverlap) with its inputs
  //(e.g. over the last 1000 iterations).
  private float _overlapDutyCycle;

  private int _overlap; //the last computed input overlap for the Column.
  private final int _ix,_iy;  //'input' row and col
  private final int _cx,_cy;  //'column grid' row and col

  public final float EMA_ALPHA = 0.005f;//Exponential Moving Average alpha value
  
  public static class CellAndSegment {
    public final Cell cell;
    public final Segment segment;
    public CellAndSegment(Cell cell, Segment segment) {
      this.cell = cell;
      this.segment = segment;
    }
  }

  /**
   *  Construct a new Column for the given parent region at source row/column
   *  position srcPos and column grid position pos.
   *  @param region the parent Region this Column belongs to.
   *  @param srcPos (srcX,srcY) of this Column's 'center' position
   *               in terms of the proximal-synapse input space.
   *  @param pos (x,y) of this Column's position within the
   *             Region's column grid.
   */
  Column(Region region, int srcPosX, int srcPosY, int posX, int posY) {
    _region = region;
    int numCells = region.getCellsPerCol();
    _cells = new Cell[numCells];
    for(int i=0; i<numCells; ++i)
      _cells[i] = new Cell(this, i); //context cells
    _isActive = false; //whether or not this Column is currently active.

    //The list of potential synapses and their permanence values.
    _proximalSegment = new Segment(region.getSegActiveThreshold());

    //The boost value for column c as computed during learning.
    //used to increase the overlap value for inactive columns.
    _boost = 1.0f;

    //A sliding average representing how often column c has been active
    //after inhibition (e.g. over the last 1000 iterations).
    _activeDutyCycle = 1.0f;

    //A sliding average representing how often column c has had
    //significant overlap (i.e. greater than minOverlap) with its inputs
    //(e.g. over the last 1000 iterations).
    _overlapDutyCycle = 1.0f;

    _overlap = 0; //the last computed input overlap for the Column.
    _ix = srcPosX; //'input' row and col
    _iy = srcPosY;
    _cx = posX; //'column grid' row and col
    _cy = posY;
  }

  public int ix() { return _ix; }
  public int iy() { return _iy; }
  public int cx() { return _cx; }
  public int cy() { return _cy; }
  public boolean isActive() { return _isActive; }
  void setActive(boolean isActive) { _isActive = isActive; }
  public int getOverlap() { return _overlap; }
  public int numCells() { return _cells.length; }
  public Cell getCell(int i) { return _cells[i]; }
  public Region getRegion() { return _region; }

  /**
   * Increment all cells in this column to the next time step.
   */
  void nextTimeStep() {
    for(int i=0; i<_cells.length; ++i)
      _cells[i].nextTimeStep();
  }

  /**
   *  Return the (last computed) input overlap for this Column in terms of the
   *  percentage of active synapses out of total existing synapses.
   */
  public float getOverlapPercentage() {
    int numSyns = _proximalSegment.numSynapses();
    if(numSyns==0)
      numSyns = 1;
    return (float)_overlap / (float)numSyns;
  }

  /**
   *  Return the list of all currently connected proximal synapses for this Column.
   */
  void getConnectedSynapses(List<Synapse> syns) {
    _proximalSegment.getConnectedSynapses(syns);
  }

  /**
   *  For this column, return the cell with the best matching segment (at time t-1 if
   *  prevous=True else at time t). Only consider sequence segments if isSequence
   *  is True, otherwise only consider non-sequence segments. If no cell has a
   *  matching segment, then return the cell with the fewest number of segments.
   *  @return a list containing the best cell and its best segment (may be None).
   */
  CellAndSegment getBestMatchingCell(boolean isSequence, boolean previous) {
    Cell bestCell = null;
    Segment bestSeg = null;
    int bestCount = 0;
    for(int i=0; i<_cells.length; ++i) {
      Segment seg = _cells[i].getBestMatchingSegment(isSequence, previous);
      if(seg!=null) {
        int synCount = 0;
        if(previous)
          synCount = seg.getPrevActiveSynapseCount(false);
        else
          synCount = seg.getActiveSynapseCount(false);

        if(synCount > bestCount) {
          bestCell = _cells[i];
          bestSeg = seg;
          bestCount = synCount;
        }
      }
    }

    if(bestCell==null) {
      bestCell = _cells[0];
      int fewestCount = bestCell.numSegments();
      for(int i=1; i<_cells.length; ++i) {
        if(_cells[i].numSegments() < fewestCount) {
          fewestCount = _cells[i].numSegments();
          bestCell = _cells[i];
        }
      }
    }

    return new CellAndSegment(bestCell, bestSeg);
  }

  /**
   *  The spatial pooler overlap of this column with a particular input pattern.
   *  The overlap for each column is simply the number of connected synapses with active
   *  inputs, multiplied by its boost. If this value is below minOverlap, we set the
   *  overlap score to zero.
   */
  void computeOverlap() {
    int overlap = _proximalSegment.getActiveSynapseCount();

    if(overlap < _region.getMinOverlap())
      overlap = 0;
    else
      overlap = (int)(((float)overlap)*_boost);
    _overlap = overlap;
  }

  /**
   *  Update the permanence value of every synapse in this column based on whether active.
   *  This is the main learning rule (for the column's proximal dentrite).
   *  For winning columns, if a synapse is active, its permanence value is incremented,
   *  otherwise it is decremented. Permanence values are constrained to be between 0 and 1.
   */
  void updatePermanences() {
    _proximalSegment.adaptPermanences();
  }

  /**
   *  There are two separate boosting mechanisms
   *  in place to help a column learn connections. If a column does not win often
   *  enough (as measured by activeDutyCycle), its overall boost value is
   *  increased (line 30-32). Alternatively, if a column's connected synapses
   *  do not overlap well with any inputs often enough (as measured by
   *  overlapDutyCycle), its permanence values are boosted (line 34-36).
   *  Note: once learning is turned off, boost(c) is frozen.
   */
  void performBoosting() {
    List<Column> neighborCols = new ArrayList<Column>();
    _region.neighbors(neighborCols, this);

    //minDutyCycle(c) A variable representing the minimum desired firing rate
    //for a cell. If a cell's firing rate falls below this value, it will be
    //boosted. This value is calculated as 1% of the maximum firing rate of
    //its neighbors.
    float minDutyCycle = 0.01f * maxDutyCycle(neighborCols);
    updateActiveDutyCycle();
    _boost = boostFunction(minDutyCycle);

    updateOverlapDutyCycle();
    if(_overlapDutyCycle < minDutyCycle)
      increasePermanences(0.1f*Synapse.CONNECTED_PERM);
  }

  /**
   *  Returns the maximum active duty cycle of the columns in the given list
   *  of columns.
   */
  float maxDutyCycle(List<Column> cols) {
    float maxd = 0.0f;
    for(Column col : cols) {
      if(col._activeDutyCycle > maxd)
        maxd = col._activeDutyCycle;
    }
    return maxd;
  }

  /**
   *  Increase the permanence value of every synapse in this column by a scale factor.
   */
  void increasePermanences(float scale) {
    _proximalSegment.updatePermanences(true);
  }

  /**
   *  Computes a moving average of how often this column has been active
   *  after inhibition.
   */
  void updateActiveDutyCycle() {
    float newCycle = (1.0f - EMA_ALPHA) * _activeDutyCycle;
    if(_isActive)
      newCycle += EMA_ALPHA;
    _activeDutyCycle = newCycle;
  }

  /**
   *  Computes a moving average of how often this column has overlap greater
   *  than minOverlap.
   *  Exponential moving average (EMA):
   *  St = a * Yt + (1-a)*St-1
   */
  void updateOverlapDutyCycle() {
    float newCycle = (1.0f - EMA_ALPHA) * _overlapDutyCycle;
    if(_overlap > _region.getMinOverlap())
      newCycle += EMA_ALPHA;
    _overlapDutyCycle = newCycle;
  }

  /**
   *  Returns the boost value of this column. The boost value is a scalar >= 1.
   *  If activeDutyCyle(c) is above minDutyCycle(c), the boost value is 1.
   *  The boost increases linearly once the column's activeDutyCycle starts
   *  falling below its minDutyCycle.
   */
  float boostFunction(float minDutyCycle) {
    if(_activeDutyCycle > minDutyCycle)
      return 1.0f;
    else if(_activeDutyCycle==0.0)
      return _boost * 1.05f; //if 0 activeDuty, fix at +5%
    return minDutyCycle / _activeDutyCycle;
  }

  /**
   * Add a new synapse to the proximal segment for this Column.
   * @param icell the input cell to connect form the synapse to.
   * @param initPerm the initial permanence value for the synapse.
   */
  void addProximalSynapse(AbstractCell icell, float initPerm) {
    _proximalSegment.createSynapse(icell, initPerm);
  }

}
