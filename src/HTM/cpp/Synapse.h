/*
 * Synapse.h
 *
 *  Created on: Sep 22, 2011
 *      Author: barry
 *
 *  A data structure representing a synapse. Contains a permanence value and the
 *  source input index.  Also contains a 'location' in the input space that this
 *  synapse roughly represents.
 */

#ifndef SYNAPSE_H_
#define SYNAPSE_H_

extern float CONNECTED_PERM;//Synapses with permanences above this value are connected.

class Cell;

class Synapse {
public:
  Synapse(AbstractCell* inputSource, float permanence=0.0);
  ~Synapse();

  inline bool isConnected() { return _permanence >= CONNECTED_PERM; }
  bool isActive(bool connectedOnly=true);
  bool wasActive(bool connectedOnly=true);
  bool wasActiveFromLearning();

  void increasePermanence(float amount=0.0);
  void decreasePermanence(float amount=0.0);

  Cell* getCell();

private:
  AbstractCell* _inputSource;
  float _permanence;
};

#endif /* SYNAPSE_H_ */

