/*
 * Synapse.cpp
 *
 *  Created on: Sep 22, 2011
 *      Author: barry
 *
 *  A data structure representing a synapse. Contains a permanence value and the
 *  source input index.  Also contains a 'location' in the input space that this
 *  synapse roughly represents.
 */
#include "AbstractCell.h"
#include "Synapse.h"
#include <math.h>

//Global parameters that apply to all Region instances
float CONNECTED_PERM = 0.2;//Synapses with permanences above this value are connected.
float INITIAL_PERMANENCE = 0.3;//initial permanence for distal synapses
float PERMANENCE_INC = 0.015;//Amount permanences of synapses are incremented in learning.
float PERMANENCE_DEC = 0.005;//Amount permanences of synapses are decremented in learning.

/**
 * @param inputSource: object providing source of the input to this synapse
 * (either a Column's Cell or a special InputCell.
 * @param permanence: the synapses's initial permanence value (0.0-1.0).
 */
Synapse::Synapse(AbstractCell* inputSource, float permanence) {
  _inputSource = inputSource;
  _permanence = permanence==0.0 ? INITIAL_PERMANENCE : fminf(1.0,permanence);
}

Synapse::~Synapse() {
  //delete if needed
}

/**
 * Return true if this Synapse is active due to the current input.
 * @param connectedOnly: only consider if active if this synapse is connected.
 */
bool Synapse::isActive(bool connectedOnly) {
  return _inputSource->isActive() && (isConnected() || !connectedOnly);
}

/**
 * Return true if this Synapse was active due to the previous input at t-1.
 * @param connectedOnly: only consider if active if this synapse is connected.
 */
bool Synapse::wasActive(bool connectedOnly) {
  return _inputSource->wasActive() && (isConnected() || !connectedOnly);
}

/**
 *  Return true if this Synapse was active due to the input previously being
 *  in a learning state.
 */
bool Synapse::wasActiveFromLearning() {
  return wasActive() && _inputSource->wasLearning();
}

/**
 * Increases the permanence of this synapse.
 */
void Synapse::increasePermanence(float amount) {
  if(amount==0.0)
    amount = PERMANENCE_INC;
  _permanence = fminf(1.0, _permanence+amount);
}

/**
 * Decreases the permanence of this synapse.
 */
void Synapse::decreasePermanence(float amount) {
  if(amount==0.0)
    amount = PERMANENCE_DEC;
  _permanence = fmaxf(0.0, _permanence-amount);
}

/**
 * Return a pointer to this synapse's distal cell.  Important
 * that this method only be called on distal synapses.
 */
Cell* Synapse::getCell() {
  return (Cell*)_inputSource;
}

