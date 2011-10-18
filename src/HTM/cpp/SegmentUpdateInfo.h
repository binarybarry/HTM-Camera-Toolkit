/*
 * SegmentUpdateInfo.h
 *
 *  Created on: Sep 26, 2011
 *      Author: barry
 *
 * class SegmentUpdateInfo(object):
 *  """
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
 *  """
 */

#ifndef SEGMENTUPDATEINFO_H_
#define SEGMENTUPDATEINFO_H_

class Cell;

class SegmentUpdateInfo {
public:
  SegmentUpdateInfo(Cell* cell, Segment* segment,
      std::set<Synapse*> activeSynapses, bool addNewSynapses=false);

  inline bool getAddNewSynapses() { return _addNewSynapses; }
  inline void setSequence(bool sequence) { _isSequence = sequence; }
  inline Segment* getSegment() { return _segment; }
  inline std::set<Synapse*>& getActiveSynapses() { return _activeSynapses; }
  int numLearningCells() { return (int)_learningCells.size(); }

  Segment* createCellSegment();
  void createSynapsesToLearningCells();

private:
  Cell* _cell;
  Segment* _segment;
  std::set<Synapse*> _activeSynapses;
  std::set<Cell*> _learningCells;
  bool _addNewSynapses;
  bool _isSequence;
  std::set<Synapse*> _addedSynapses; //once synapses added, store here to visualize later
};

#endif /* SEGMENTUPDATEINFO_H_ */
