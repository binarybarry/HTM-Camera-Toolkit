/*
 * Segment.h
 *
 *  Created on: Sep 22, 2011
 *      Author: barry
 *
 *  Represent a single dendrite segment that forms synapses (connections) to other
 *  cells. Each segment also maintains a boolean flag, sequenceSegment, indicating
 *  whether the segment predicts feed-forward input on the next time step.
 *  Segments can be either proximal or distal (for spatial pooling or temporal pooling
 *  respectively) however the class object itself does not need to know which
 *  it ultimately is as they behave identically.  Segments are considered 'active'
 *  if enough of its existing synapses are connected and individually active.
 */

#ifndef SEGMENT_H_
#define SEGMENT_H_

#include <set>
#include <vector>
#include "Synapse.h"

class Segment {
public:
  Segment(int segActiveThreshold);
  ~Segment();

  Synapse* createSynapse(AbstractCell* inputSource, float initPerm=0.0);
  void createSynapsesToLearningCells(std::set<Cell*>& cells, std::set<Synapse*>& added);
  void getConnectedSynapses(std::vector<Synapse*>& syns);
  void getSynapses(std::set<Synapse*>& syns);
  void getSynapseCells(std::set<Cell*>& cells);

  void getActiveSynapses(std::set<Synapse*>& syns);
  void getPrevActiveSynapses(std::set<Synapse*>& syns);
  int getActiveSynapseCount(bool connectedOnly=true);
  int getPrevActiveSynapseCount(bool connectedOnly=true);

  void adaptPermanences();
  void updatePermanences(bool increase);
  void updatePermanences(std::set<Synapse*> activeSynapses);
  void decreasePermanences(std::set<Synapse*> activeSynapses);

  bool isActive();
  bool wasActive();
  bool wasActiveFromLearning();

  inline void setSequence(bool sequence) { _isSequence = sequence; }
  inline bool isSequence() { return _isSequence; }
  inline int numSynapses() { return _synapses.size(); }

private:
  std::vector<Synapse*> _synapses;
  bool _isSequence;
  float _segActiveThreshold;
};

#endif /* SEGMENT_H_ */

