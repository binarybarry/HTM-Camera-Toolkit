/*
 * Cell.h
 *
 *  Created on: Jul 21, 2012
 *      Author: barry
 */

#ifndef CELL_H_
#define CELL_H_

#include "Segment.h"
#include "SegmentUpdateInfo.h"

typedef struct CellType {
  struct ColumnType* column;
  int index;
  int id;

  /**
   * The predictionSteps is the fewest number of time steps until this Cell
   * believes it will becomes active. The last prediction steps value
   * represents the fewest number of time steps this Cell believes it will
   * becomes active in.  This value will often be a count down that approaches
   * zero as time steps move forward and the Cell gets closer to becoming
   * activated.  If the Cell is not currently in a predicting state this value
   * should be ignored.
   */
  int predictionSteps;

  bool isActive;
  bool wasActive;
  bool isPredicting;
  bool wasPredicted;
  bool isLearning;
  bool wasLearning;

  Segment* segments;
  int numSegments;
  int allocatedSegments;

  SegmentUpdateInfo* segmentUpdates;
  int numSegUpdates;
  int allocatedSegUpdates;

} Cell;

void initCell(Cell* cell, struct ColumnType* column, int index);
void deleteCell(Cell* cell);
void setCellPredicting(Cell* cell, bool predicting);
int numCellSegments(Cell* cell, int predictionSteps);
void nextCellTimeStep(Cell* cell);
Segment* createCellSegment(Cell* cell);
Segment* getPreviousActiveSegment(Cell* cell);
SegmentUpdateInfo* updateSegmentActiveSynapses(Cell* cell, bool previous,
    int segmentID, bool newSynapses);
void applyCellSegmentUpdates(Cell* cell, bool positiveReinforcement);
Segment* getBestMatchingPreviousSegment(Cell* cell, int* segmentID);
Segment* getBestMatchingSegment(Cell* cell, int numPredictionSteps,
    bool previous, int* segmentID);

#endif /* CELL_H_ */
