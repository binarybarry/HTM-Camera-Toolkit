/*
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

#include <stdio.h>
#include <stdlib.h>
#include <set>
#include "Region.h"

/**
 * def __init__(self, cell, segment, activeSynapses, addNewSynapses=False):
    self.cell = cell
    self.segment = segment
    self.activeSynapses = activeSynapses
    self.addNewSynapses = addNewSynapses
    self.isSequence = False
    self.addedSynapses = [] #once synapses added, store here to visualize later

    learningCells = set({}) #capture learning cells at this time step

    #do not add >1 synapse to the same cell on a given segment
    region = self.cell.column.region
    if addNewSynapses:
      segCells = set({})
      if self.segment:
        for syn in self.segment.synapses:
          segCells.add(syn.inputSource)
      #only allow connecting to Columns within locality radius
      cellCol = cell.column

      #if localityRadius is 0, it means 'no restriction'
      if region.localityRadius > 0:
        minY = max(0, cellCol.cy-region.localityRadius)
        maxY = min(region.height-1, cellCol.cy+region.localityRadius)
        minX = max(0, cellCol.cx-region.localityRadius)
        maxX = min(region.width-1, cellCol.cx+region.localityRadius)
      else:
        minY = 0
        maxY = region.height-1
        minX = 0
        maxX = region.width-1

      for y in xrange(minY,maxY+1):
        for x in xrange(minX,maxX+1):
          col = region.columnGrid[x][y]
          for cell in col.cells:
            if cell.wasLearning and cell not in segCells:
              learningCells.add(cell)

    synCount = region.newSynapseCount
    if self.segment:
      synCount = max(0, synCount-len(self.activeSynapses))
    synCount = min(len(learningCells), synCount) #clamp at # of learn cells

    self.learningCells = []
    if len(learningCells) > 0 and synCount > 0:
      self.learningCells = random.sample(learningCells, synCount)
 */
SegmentUpdateInfo::SegmentUpdateInfo(Cell* cell, Segment* segment,
    std::set<Synapse*> activeSynapses, bool addNewSynapses) {
  _cell = cell;
  _segment = segment;
  for(std::set<Synapse*>::iterator iter = activeSynapses.begin();
      iter!=activeSynapses.end(); ++iter) {
    _activeSynapses.insert((*iter));
  }
  _addNewSynapses = addNewSynapses;
  _isSequence = false;

  Region* region = cell->getRegion();
  Column* ownColumn = cell->getColumn();
  std::set<Cell*> learningCells;

  if(_addNewSynapses) {
    std::set<Cell*> segCells;
    if(_segment!=NULL)
      _segment->getSynapseCells(segCells);

    int minY = 0;
    int maxY = region->getHeight()-1;
    int minX = 0;
    int maxX = region->getWidth()-1;
    if(region->getLocalityRadius() > 0) {
      //TODO implement locality radius
    }

    //do not add >1 synapse to the same cell on a given segment
    for(int x=minX; x<=maxX; ++x) {
      for(int y=minY; y<=maxY; ++y) {
        Column* col = region->getColumn(x,y);
        if(col==ownColumn) {
          //printf("\nskip own column (%d,%d)\n", x,y);
          continue;
        }
        for(int i=0; i<col->numCells(); ++i) {
          Cell* cell = col->getCell(i);
          if(cell->wasLearning() && segCells.count(cell)==0) {
            //printf("learningCell added (%d,%d) %d\n", x, y, i);
            learningCells.insert(cell);
          }
        }
      }
    }
  }

  int synCount = region->getNewSynapseCount();
  if(_segment!=NULL)
    synCount = region->max(0, synCount-activeSynapses.size());
  synCount = region->min(learningCells.size(), synCount);//clamp at # of learn cells
  //printf("synCount = %d\n", synCount);

  //randomly choose synCount learning cells to add connections to
  if(learningCells.size() > 0 && synCount > 0) {
    for(int i=0; i<synCount; ++i) {
      int ri = rand() % learningCells.size();
      //printf("learningCell.size = %d  ", learningCells.size());

      std::set<Cell*>::iterator iter = learningCells.begin();
      for(int ci=0; ci<ri; ++ci)
        ++iter;

      Cell* riCell = (*iter);
      _learningCells.insert(riCell);
      if(learningCells.erase(riCell)==0)
        printf("Missing learning cell to erase? ri=%d, address=%d\n", ri, riCell);
      //else
      //  printf("ok learning cell.  ri=%d, address=%d\n", ri, riCell);
    }
  }
}

/**
 * Create a new segment on the update cell using connections from
 * the set of learning cells for the update info.
 */
Segment* SegmentUpdateInfo::createCellSegment() {
  Segment* segment = _cell->createSegment(_learningCells);
  segment->getSynapses(_addedSynapses);
  segment->setSequence(_isSequence);
  return segment;
}

/**
 * Create new synapse connections to the segment to be updated using
 * the set of learning cells in this update info.
 */
void SegmentUpdateInfo::createSynapsesToLearningCells() {
  std::set<Synapse*> added;
  _segment->createSynapsesToLearningCells(_learningCells, added);
  for(std::set<Synapse*>::iterator iter = added.begin();
      iter != added.end(); ++iter) {
    _addedSynapses.insert((*iter));
  }
}


