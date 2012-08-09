/*
 * Column.h
 *
 *  Created on: Jul 21, 2012
 *      Author: barry
 */

#ifndef COLUMN_H_
#define COLUMN_H_

#include <stdbool.h>
#include "Cell.h"

typedef struct ColumnType {
  struct RegionType* region; /*parent region*/
  Cell* cells;    /*Sequence cells*/
  int numCells;
  bool isActive;  /*whether or not this Column is currently active.*/

  /*The list of potential synapses and their permanence values.*/
  Segment* proximalSegment;

  /*The boost value for column c as computed during learning.
    used to increase the overlap value for inactive columns.*/
  float boost;

  /*A sliding average representing how often column c has been active
    after inhibition (e.g. over the last 1000 iterations).*/
  float activeDutyCycle;

  /*A sliding average representing how often column c has had
    significant overlap (i.e. greater than minOverlap) with its inputs
    (e.g. over the last 1000 iterations).*/
  float overlapDutyCycle;

  int overlap; /*the last computed input overlap for the Column.*/
  int ix,iy;  /*'input' row and col*/
  int cx,cy;  /*'column grid' row and col*/
} Column;

void initColumn(Column* col, struct RegionType* region,
                int srcPosX, int srcPosY,
                int posX, int posY);
void deleteColumn(Column* col);
void nextColumnTimeStep(Column* col);
Cell* getBestMatchingCell(Column* col, Segment** bestSegPtr, int* segmentID,
                          int numPredictionSteps, bool previous);
void computeOverlap(Column* col);
void updateColumnPermanences(Column* col);
void performBoosting(Column* col);

#endif /* COLUMN_H_ */
