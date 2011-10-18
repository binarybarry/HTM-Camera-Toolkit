/*
 * Segment.cpp
 *
 *  Created on: Sep 22, 2011
 *      Author: barry
 *
 * Represent a single dendrite segment that forms synapses (connections) to
 * other cells. Each segment also maintains a boolean flag, sequenceSegment,
 * indicating whether the segment predicts feed-forward input on the next
 * time step. Segments can be either proximal or distal (for spatial pooling
 * or temporal pooling respectively) however the class object itself does not
 * need to know which it ultimately is as they behave identically.  Segments
 * are considered 'active' if enough of its existing synapses are connected
 * and individually active.
 */

#include <set>
#include <vector>
#include "Region.h"

/**
 * Initialize a new Segment with the specified segment activation threshold.
 */
Segment::Segment(int segActiveThreshold) {
  _isSequence = false;
  _segActiveThreshold = segActiveThreshold;
}

Segment::~Segment() {
  for(unsigned int i=0; i<_synapses.size(); ++i)
    delete _synapses[i];
  _synapses.clear();
}

/**
 *  Create a new synapse for this segment attached to the specified input source.
 *  @param inputSource: the input source of the synapse to create.
 *  @return the newly created synapse.
 */
Synapse* Segment::createSynapse(AbstractCell* inputSource, float initPerm) {
  Synapse* newSyn = new Synapse(inputSource, initPerm);
  _synapses.push_back(newSyn);
  return newSyn;
}

/**
 *  Create numSynapses new synapses for this segment attached to the specified
 *  set of learning cells.
 *  @param cells: set of available learning cells to form synapses to.
 *  @param added set will be populated with synapses that were successfully added.
 */
void Segment::createSynapsesToLearningCells(std::set<Cell*>& cells,
    std::set<Synapse*>& added) {
  //assume that cells were previously checked to prevent adding
  //synapses to same cell more than once per segment
  for(std::set<Cell*>::iterator iter = cells.begin(); iter!=cells.end(); ++iter)
    added.insert(createSynapse((*iter)));
}

/**
 *  Populate the vector with all the synapses that are currently connected
 *  (those with a permanence value above the threshold).
 */
void Segment::getConnectedSynapses(std::vector<Synapse*>& syns) {
  for(unsigned int i=0; i<_synapses.size(); ++i) {
    if(_synapses[i]->isConnected())
      syns.push_back(_synapses[i]);
  }
}

/**
 * Populate the set parameter with the current set of synapses for this segment.
 */
void Segment::getSynapses(std::set<Synapse*>& syns) {
  for(unsigned int i=0; i<_synapses.size(); ++i) {
    syns.insert(_synapses[i]);
  }
}

/**
 * Populate the set reference with all Cells that this segment's synapses
 * are connected (or potentially connected) to.
 */
void Segment::getSynapseCells(std::set<Cell*>& cells) {
  for(unsigned int i=0; i<_synapses.size(); ++i) {
    cells.insert(_synapses[i]->getCell());
  }
}

/**
 *  Populate the set with all the currently active (firing) synapses on
 *  this segment.
 *  @param connectedOnly: only consider if active if a synapse is connected.
 */
void Segment::getActiveSynapses(std::set<Synapse*>& syns) {
  for(unsigned int i=0; i<_synapses.size(); ++i) {
    if(_synapses[i]->isActive())
      syns.insert(_synapses[i]);
  }
}

/**
 * Return a count of how many synapses on this segment are active
 * in the current time step.  If connectedOnly is true only consider
 * synapses which are currently connected.
 */
int Segment::getActiveSynapseCount(bool connectedOnly) {
  int c=0;
  for(unsigned int i=0; i<_synapses.size(); ++i) {
    if(_synapses[i]->isActive(connectedOnly))
      ++c;
  }
  return c;
}

/**
 *  Populate the set with all the previously active (firing) synapses on
 *  this segment.
 *  @param connectedOnly: only consider if active if a synapse is connected.
 */
void Segment::getPrevActiveSynapses(std::set<Synapse*>& syns) {
  for(unsigned int i=0; i<_synapses.size(); ++i) {
    if(_synapses[i]->wasActive())
      syns.insert(_synapses[i]);
  }
}

/**
 * Return a count of how many synapses on this segment were active
 * in the previous time step.  If connectedOnly is true only consider
 * synapses which are currently connected.
 */
int Segment::getPrevActiveSynapseCount(bool connectedOnly) {
  int c=0;
  for(unsigned int i=0; i<_synapses.size(); ++i) {
    if(_synapses[i]->wasActive(connectedOnly))
      ++c;
  }
  return c;
}

/**
 * Update all permanence values of each synapse based on current activity.
 * If a synapse is active, increase its permanence, else decrease it.
 */
void Segment::adaptPermanences() {
  for(unsigned int i=0; i<_synapses.size(); ++i) {
    if(_synapses[i]->isActive())
      _synapses[i]->increasePermanence();
    else
      _synapses[i]->decreasePermanence();
  }
}

/**
 * Update (increase or decrease) all permanence values of each synapse on
 * this segment.
 */
void Segment::updatePermanences(bool increase) {
  for(unsigned int i=0; i<_synapses.size(); ++i) {
    if(increase)
      _synapses[i]->increasePermanence();
    else
      _synapses[i]->decreasePermanence();
  }
}

/**
 * Update (increase or decrease based on whether the synapse is active)
 * all permanence values of each of the synapses in the specified set.
 */
void Segment::updatePermanences(std::set<Synapse*> activeSynapses) {
  for(unsigned int i=0; i<_synapses.size(); ++i) {
    if(activeSynapses.count(_synapses[i]) > 0)
      _synapses[i]->increasePermanence();
    else
      _synapses[i]->decreasePermanence();
  }
}

/**
 * Decrease the permanences of each of the synapses in the set of
 * active synapses that happen to be on this segment.
 */
void Segment::decreasePermanences(std::set<Synapse*> activeSynapses) {
  for(unsigned int i=0; i<_synapses.size(); ++i) {
    if(activeSynapses.count(_synapses[i]) > 0)
      _synapses[i]->decreasePermanence();
  }
}

/**
 *  This routine returns true if the number of connected synapses on this segment
 *  that are active due to active states at time t is greater than activationThreshold.
 */
bool Segment::isActive() {
  int c=0;
  for(unsigned int i=0; i<_synapses.size(); ++i) {
    if(_synapses[i]->isActive())
      ++c;
  }
  return c >= _segActiveThreshold;
}

/**
 *  This routine returns true if the number of connected synapses on this segment
 *  that were active due to active states at time t-1 is greater than activationThreshold.
 */
bool Segment::wasActive() {
  return getPrevActiveSynapseCount() >= _segActiveThreshold;
}

/**
 *  This routine returns true if the number of connected synapses on this segment
 *  that were active due to learning states at time t-1 is greater than activationThreshold.
 */
bool Segment::wasActiveFromLearning() {
  int c=0;
  for(unsigned int i=0; i<_synapses.size(); ++i) {
    if(_synapses[i]->wasActiveFromLearning())
      ++c;
  }
  return c >= _segActiveThreshold;
}

