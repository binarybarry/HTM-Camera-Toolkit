/*
 * Cell.h
 *
 *  Created on: Sep 22, 2011
 *      Author: barry
 *
 * class Cell:
 *   Represents an HTM sequence cell that belongs to a given Column.
 */

#ifndef CELL_H_
#define CELL_H_

#include <list>
#include "AbstractCell.h"
#include "Segment.h"
#include "SegmentUpdateInfo.h"

class Region;
class Column;

class Cell : public AbstractCell {
public:
  Cell();
  ~Cell();
  inline void init(Column* column, int index) { _column = column; _index = index; }
  inline int getIndex() { return _index; }
  inline bool isDistal() { return true; }

  bool isActive() { return _isActive; }
  inline bool isLearning() { return _isLearning; }
  inline bool isPredicting() { return _isPredicting; }

  bool wasActive() { return _wasActive; }
  bool wasLearning() { return _wasLearning; }
  inline bool wasPredicted() { return _wasPredicted; }

  inline void setActive(bool active) { _isActive = active; }
  inline void setLearning(bool learning) { _isLearning = learning; }
  inline void setPredicting(bool predicting) { _isPredicting = predicting; }

  void nextTimeStep();
  Segment* createSegment(std::set<Cell*>& learningCells);
  Segment* getPreviousActiveSegment();
  SegmentUpdateInfo* updateSegmentActiveSynapses(bool previous=false,
      Segment* segment=0, bool newSynapses=false);
  void applySegmentUpdates(bool positiveReinforcement);
  Segment* getBestMatchingSegment(bool isSequence, bool previous=false);
  bool hasActiveSequenceSegment();

  inline int numSegments() { return _segments.size(); }
  inline Segment* getSegment(int i) { return _segments[i]; }
  Column* getColumn() { return _column; }
  Region* getRegion();

private:
  Column* _column;
  int _index;
  bool _isActive;
  bool _wasActive;
  bool _isPredicting;
  bool _wasPredicted;
  bool _isLearning;
  bool _wasLearning;
  std::vector<Segment*> _segments;

  std::list<SegmentUpdateInfo*> _segmentUpdates;

};

#endif /* CELL_H_ */

