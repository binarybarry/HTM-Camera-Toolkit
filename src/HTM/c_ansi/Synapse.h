/*
 * Synapse.h
 *
 *  Created on: Jul 19, 2012
 *      Author: barry
 */

#ifndef SYNAPSE_H_
#define SYNAPSE_H_

/* Global parameters that apply to all Region instances */
#define MAX_PERM 10000 /* Maximum/full permanence value */
#define CONNECTED_PERM 2000 /* Synapses with permanences above this value are connected. */
#define INITIAL_PERMANENCE 3000 /*initial permanence for distal synapses*/
#define PERMANENCE_INC 150 /*Amount permanences of synapses are incremented in learning*/
#define PERMANENCE_DEC 100 /*Amount permanences of synapses are decremented in learning*/

/*
 * A data structure representing a synapse. Contains a permanence value and the
 * source input index.  Also contains a 'location' in the input space that this
 * synapse roughly represents.
 */
typedef struct SynapseType {
  struct CellType* inputSource;
  int permanence;
  bool isConnected;
  bool wasConnected;
} Synapse;

void initSynapse(Synapse* syn, struct CellType* inputSource, int permanence);
/*bool isSynapseConnected(Synapse* syn);*/
bool isSynapseActive(Synapse* syn, bool connectedOnly);
bool wasSynapseActive(Synapse* syn, bool connectedOnly);
bool wasSynapseActiveFromLearning(Synapse* syn);
void increaseSynapsePermanence(Synapse* syn, int amount);
void decreaseSynapsePermanence(Synapse* syn, int amount);

#endif /* SYNAPSE_H_ */
