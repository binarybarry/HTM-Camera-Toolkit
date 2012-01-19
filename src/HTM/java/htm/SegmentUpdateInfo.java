package htm;

import java.util.HashSet;
import java.util.Random;
import java.util.Set;

/**
 * SegmentUpdateInfo.cpp
 *
 *  Created on: Sep 26, 2011
 *      Author: barry
 *
 *  This data structure holds three pieces of information required to update
 *  a given segment:
 *  a) segment reference (None if it's a new segment),
 *  b) a list of existing active synapses, and
 *  c) a flag indicating whether this segment should be marked as a sequence
 *     segment (defaults to false).
 *  The structure also determines which learning cells (at this time step)
 *  are available to connect (add synapses to) should the segment get updated.
 *  If there is a locality radius set on the Region, the pool of learning cells
 *  is restricted to those with the radius.
 */
public class SegmentUpdateInfo {
  
  private Cell _cell;
  private Segment _segment;
  private Set<Synapse> _activeSynapses;
  private Set<Cell> _learningCells;
  private boolean _addNewSynapses;
  private boolean _isSequence;
  private Set<Synapse> _addedSynapses; //once synapses added, store here to visualize later
  private final Random _rand = new Random(4242);

  /**
   * Create a new SegmentUpdateInfo that is to modify the state of the Region
   * either by adding a new segment to a cell, new synapses to a segemnt,
   * or updating permanences of existing synapses on some segment.
   * @param cell the cell that is to have a segment added or updated.
   * @param segment the segment that is to be updated (null here means a new
   * segment is to be created on the parent cell).
   * @param activeSynapses the set of active synapses on the segment that are
   * to have their permanences updated.
   * @param addNewSynapses set to true if new synapses are to be added to the
   * segment (or if new segment is being created) or false if no new synapses
   * should be added instead only existing permanences updated.
   */
  SegmentUpdateInfo(Cell cell, Segment segment,
      Set<Synapse> activeSynapses, boolean addNewSynapses) {
    _cell = cell;
    _segment = segment;
    _activeSynapses = new HashSet<Synapse>();
    _activeSynapses.addAll(activeSynapses);
    
    _learningCells = new HashSet<Cell>();
    _addedSynapses = new HashSet<Synapse>();    
    _addNewSynapses = addNewSynapses;
    _isSequence = false;

    Region region = cell.getRegion();
    Column ownColumn = cell.getColumn();
    Set<Cell> learningCells = new HashSet<Cell>();

    //if adding new synapses, find the current set of learning cells within
    //the Region and select a random subset of them to connect the segment to.
    if(_addNewSynapses) {
      Set<Cell> segCells = new HashSet<Cell>();
      if(_segment!=null)
        _segment.getSynapseCells(segCells);

      int minY = 0;
      int maxY = region.getHeight()-1;
      int minX = 0;
      int maxX = region.getWidth()-1;
      if(region.getLocalityRadius() > 0) {
        //TODO implement locality radius
      }

      //do not add >1 synapse to the same cell on a given segment
      for(int x=minX; x<=maxX; ++x) {
        for(int y=minY; y<=maxY; ++y) {
          Column col = region.getColumn(x,y);
          if(col==ownColumn)
            continue; //skip cells in our own column (don't connect to ourself)
          
          for(int i=0; i<col.numCells(); ++i) {
            Cell ccell = col.getCell(i);
            if(ccell.wasLearning() && !segCells.contains(ccell)) {
              //printf("learningCell added (%d,%d) %d\n", x, y, i);
              learningCells.add(ccell);
            }
          }
        }
      }
    }

    int synCount = region.getNewSynapseCount();
    if(_segment!=null)
      synCount = Math.max(0, synCount-activeSynapses.size());
    synCount = Math.min(learningCells.size(), synCount);//clamp at # of learn cells

    //randomly choose synCount learning cells to add connections to
    if(learningCells.size() > 0 && synCount > 0) {
      Util.createRandomSubset(learningCells, _learningCells, synCount, _rand);
    }
  }
  
  /**
   * Return whether this segment update is adding new synapses.
   */
  public boolean getAddNewSynapses() { 
    return _addNewSynapses; 
  }
  
  /**
   * Assign whether this segment update is creating a sequence segment or not.
   */
  public void setSequence(boolean sequence) { 
    _isSequence = sequence; 
  }
  
  /**
   * Return the existing segment that is to be modified by this update
   * (null if update is to create a new segment).
   */
  public Segment getSegment() { 
    return _segment; 
  }
  
  /**
   * Return the existing set of active synapses this segment should update.
   */
  public Set<Synapse> getActiveSynapses() { 
    return _activeSynapses; 
  }
  
  /**
   * Return the number of learning cells available in the Region that
   * could potentially be connected to by this update.
   */
  public int numLearningCells() { 
    return _learningCells.size(); 
  }

  /**
   * Create a new segment on the update cell using connections from
   * the set of learning cells for the update info.
   */
  Segment createCellSegment() {
    Segment segment = _cell.createSegment(_learningCells);
    segment.getSynapses(_addedSynapses);
    segment.setSequence(_isSequence);
    return segment;
  }

  /**
   * Create new synapse connections to the segment to be updated using
   * the set of learning cells in this update info.
   */
  void createSynapsesToLearningCells() {
    _segment.createSynapsesToLearningCells(_learningCells, _addedSynapses);
  }
}
