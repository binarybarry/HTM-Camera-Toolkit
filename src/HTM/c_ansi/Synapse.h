/*
 * Synapse.h
 *
 *  Created on: Jul 19, 2012
 *      Author: barry
 */

#ifndef SYNAPSE_H_
#define SYNAPSE_H_

/* Global parameters that apply to all Region instances */
#define CONNECTED_PERM 0.2 /* Synapses with permanences above this value are connected. */
#define INITIAL_PERMANENCE 0.3 /*initial permanence for distal synapses*/
#define PERMANENCE_INC 0.015 /*Amount permanences of synapses are incremented in learning*/
#define PERMANENCE_DEC 0.010 /*Amount permanences of synapses are decremented in learning*/

/*
 * A data structure representing a synapse. Contains a permanence value and the
 * source input index.  Also contains a 'location' in the input space that this
 * synapse roughly represents.
 */
typedef struct SynapseType {
  struct CellType* inputSource;
  float permanence;
  bool isConnected;
  bool wasConnected;
} Synapse;

void initSynapse(Synapse* syn, struct CellType* inputSource, float permanence);
/*bool isSynapseConnected(Synapse* syn);*/
bool isSynapseActive(Synapse* syn, bool connectedOnly);
bool wasSynapseActive(Synapse* syn, bool connectedOnly);
bool wasSynapseActiveFromLearning(Synapse* syn);
void increaseSynapsePermanence(Synapse* syn, float amount);
void decreaseSynapsePermanence(Synapse* syn, float amount);

#endif /* SYNAPSE_H_ */
