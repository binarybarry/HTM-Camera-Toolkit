/*
 * Synapse.c
 *
 * A data structure representing a synapse. Contains a permanence value and the
 *  source input index.  Also contains a 'location' in the input space that this
 *  synapse roughly represents.
 *
 *  Created on: Jul 19, 2012
 *      Author: barry
 */

#include <stdlib.h>
#include <stdbool.h>
#include <math.h>
#include "Cell.h"

/**
 * @param inputSource: object providing source of the input to this synapse
 * (either a Column's Cell or a special InputCell.
 * @param permanence: the synapses's initial permanence value (0.0-1.0).
 */
void initSynapse(Synapse* syn, Cell* inputSource, float permanence) {
  syn->permanence = permanence;
  syn->inputSource = inputSource;
  syn->isConnected = false;
  syn->wasConnected = false;
}

/**
 * Return true if this Synapse is active due to the current input.
 * @param connectedOnly: only consider if active if this synapse is connected.
 */
bool isSynapseActive(Synapse* syn, bool connectedOnly) {
  return syn->inputSource->isActive && (syn->isConnected || !connectedOnly);
}

/**
 * Return true if this Synapse was active due to the previous input at t-1.
 * @param connectedOnly: only consider if active if this synapse is connected.
 */
bool wasSynapseActive(Synapse* syn, bool connectedOnly) {
  return syn->inputSource->wasActive && (syn->wasConnected || !connectedOnly);
}

/**
 * Return true if this Synapse was active due to the input previously being
 * in a learning state.
 */
bool wasSynapseActiveFromLearning(Synapse* syn) {
  return wasSynapseActive(syn,true) && syn->inputSource->wasLearning;
}

/**
 * Increases the permanence of this synapse.
 */
void increaseSynapsePermanence(Synapse* syn, float amount) {
  if(amount==0.0f)
    amount = PERMANENCE_INC;
  syn->permanence = fminf(1.0f, syn->permanence+amount);
}

/**
 * Decreases the permanence of this synapse.
 */
void decreaseSynapsePermanence(Synapse* syn, float amount) {
  if(amount==0.0f)
    amount = PERMANENCE_DEC;
  syn->permanence = fmaxf(0.0f, syn->permanence-amount);
}
