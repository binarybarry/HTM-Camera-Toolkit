/*
 * Main file containing a set of tests related to the HTM code.
 * A few tests are standard unit tests for functionality of the
 * HTM Region and its components.  Few others are performance
 * tests for HTM.  Finally there are some miscellaneous tests
 * related to lower C level code used within the HTM implementation.
 *
 * The tests currently simply print to standard out any failures that
 * are encountered.
 */

#include <stdio.h>
#include <stdlib.h>
#include <time.h>
#include "Region.h"

#define MAX_FILE_SIZE (0x100000)
#define DEBUG 1

typedef struct ObjType {
  int a;
  int b;
} Obj;

void testRandomSubset(int* out, int k, int n, int iter) {
  int i;
  int count;
  for(i=0; i<k; ++i)
    out[i] = i;

  for(i=0, count=k; i<n; ++i, ++count) {
    int index = rand() % (count+1);
    if(iter==5)
      printf("\ni=%i, index=%i, count=%i", i, index, count);
    if(index < k)
      out[index] = i;
  }
  printf("\niter=%i:  ", iter);
  for(i=0; i<k; ++i)
    printf(" %i", out[i]);
}

/**
 * Tests for a few standard C memory allocations and manipulations.
 * Included is also a test for the random subset function.
 */
void testLanguage() {
  /*test of array access of structs is by byte or by struct-size*/
  Obj* obj = malloc(10 * sizeof(Obj));
  printf("\nSize of Obj type: %d", (int)sizeof(Obj));
  printf("\nSize of obj array 10: %d", (int)sizeof(obj));

  int i;
  for(i=0; i<10; ++i) {
    obj[i].a = i;
    obj[i].b = i*2;
  }

  for(i=0; i<10; ++i)
    printf("\na,b = %i,%i", obj[i].a, obj[i].b);

  Obj* obj2x = malloc(20 * sizeof(Obj));
  for(i=0; i<10; ++i)
    obj2x[i] = obj[i];

  free(obj);
  obj = 0;

  for(i=0; i<20; ++i)
    printf("\n2x: a,b = %i,%i", obj2x[i].a, obj2x[i].b);

  printf("\n");
  int test[5];
  for(i=0; i<5; ++i)
    test[i] = i;
  for(i=0; i<5; ++i)
    printf(" %i", test[i]);

  int out[3];
  for(i=0; i<10; ++i)
    testRandomSubset(out, 3, 10, i);
}

void testOpenMP() {
  printf("testOpenMP()...\n");
  int i,j,k;
  float a = 2.2f;
  int N = 100000;
  unsigned long time = clock();
  for(i = 0; i < N; i++) {
    /*#pragma omp parallel for*/
    for(j = 0; j < N; j++) {
      a *= 1.01;
      a -= 1.09;
    }
  }
  unsigned long elapse = clock() - time;
  printf("a=%f  time %lu\n", a,elapse/1000);
  printf("OK\n");
}

/**
 * Test the Synapse structure used within the HTM Region.
 */
void testSynapse() {
  printf("testSynpase()...\n");

  Cell cell;
  cell.isActive = true;
  cell.wasActive = false;
  cell.isLearning = true;
  cell.wasLearning = false;

  Synapse* syn = malloc(sizeof(Synapse));
  initSynapse(syn, &cell, 2000);
  syn->isConnected = (syn->permanence >= CONNECTED_PERM);

  bool ia = isSynapseActive(syn, true);
  bool wa = wasSynapseActive(syn, true);
  bool wal = wasSynapseActiveFromLearning(syn);

  if(!ia) printf("Failed: isSynapseActive1 expected true, got false.\n");
  if(wa) printf("Failed: wasSynapseActive expected false, got true.\n");
  if(wal) printf("Failed: wasSynapseActiveFromLearning expected false, got true.\n");

  decreaseSynapsePermanence(syn, 0);
  syn->isConnected = (syn->permanence >= CONNECTED_PERM);

  ia = isSynapseActive(syn, true);
  bool ian = isSynapseActive(syn, false);

  if(ia) printf("Failed: isSynapseActive2 expected false, got true.\n");
  if(!ian) printf("Failed: isSynapseActive3 expected true, got false.\n");

  free(syn);

  printf("OK\n");
}

/**
 * Test the Segment structure used within the HTM Region.
 */
void testSegment() {
  printf("testSegment()...\n");

  Cell cell1;
  cell1.isActive = true;
  cell1.wasActive = false;
  cell1.isLearning = false;
  cell1.wasLearning = false;

  Cell cell2;
  cell2.isActive = true;
  cell2.wasActive = false;
  cell2.isLearning = false;
  cell2.wasLearning = false;

  Segment* seg = malloc(sizeof(Segment));
  initSegment(seg, 2);

  float conPerm = CONNECTED_PERM;
  float conInc = PERMANENCE_INC;
  /*float conDec = PERMANENCE_DEC;*/

  createSynapse(seg, &cell1, conPerm);
  createSynapse(seg, &cell2, conPerm-conInc);

  processSegment(seg);

  /*Test that simple processSegment counts synapses and sets isActive*/
  if(seg->numActiveConnectedSyns != 1) {
    printf("Failed: processSegment1 expected 1 active connected synapse, got %i\n",
        seg->numActiveConnectedSyns);
  }
  if(seg->numActiveAllSyns != 2) {
    printf("Failed: processSegment1 expected 2 active total synapses, got %i\n",
        seg->numActiveAllSyns);
  }
  if(seg->isActive) {
    printf("Failed: processSegment1 expected isActive to be false, got true\n");
  }

  /*increase perms, now segment should be active */
  updateSegmentPermanences(seg, true);
  nextSegmentTimeStep(seg);
  processSegment(seg);

  if(seg->numPrevActiveConnectedSyns != 1) {
    printf("Failed: processSegment2 expected 1 prevActive connected synapse, got %i\n",
        seg->numPrevActiveConnectedSyns);
  }
  if(seg->numActiveConnectedSyns != 2) {
    printf("Failed: processSegment2 expected 2 active connected synapses, got %i\n",
        seg->numActiveConnectedSyns);
  }
  if(seg->numActiveAllSyns != 2) {
    printf("Failed: processSegment2 expected 2 active total synapses, got %i\n",
        seg->numActiveAllSyns);
  }
  if(!seg->isActive) {
    printf("Failed: processSegment2 expected isActive to be true, got false\n");
  }
  if(seg->wasActive) {
    printf("Failed: processSegment2 expected wasActive to be false, got true\n");
  }

  /*wasSynapseActive && wasLearning*/
  nextSegmentTimeStep(seg);
  cell1.wasActive = true;
  cell2.wasActive = true;
  cell2.wasLearning = true;

  bool wal = wasSegmentActiveFromLearning(seg);
  if(wal) {
    printf("Failed: wasSegmentActiveFromLearning1 expected false, got true\n");
  }

  cell1.wasLearning = true;
  wal = wasSegmentActiveFromLearning(seg);
  if(!wal) {
    printf("Failed: wasSegmentActiveFromLearning2 expected true, got false\n");
  }

  deleteSegment(seg);
  free(seg);

  printf("OK\n");
}

/**
 * Very simple test of the HTM Region for correctness.  This test
 * creates a very small region (2 columns) to test very basic
 * connection functionality within the Region.
 */
void testRegion1() {
  printf("testRegion1()...\n");

  char* data = malloc(2 * sizeof(char));
  data[0] = 1;
  data[1] = 0;

  Region* region = newRegionHardcoded(2,1, 0, 1, 1,1, data);
  Cell* cell0 = &region->columns[0].cells[0];
  Cell* cell1 = &region->columns[1].cells[0];

  performSpatialPooling(region);

  /*at this point we expect column0 to be active and col1 to be inactive*/
  if(!region->columns[0].isActive)
    printf("Failed: spatialPooling1 expect col0 to be active, got inactive.\n");
  if(region->columns[1].isActive)
    printf("Failed: spatialPooling1 expect col1 to be inactive, got active.\n");

  performTemporalPooling(region);

  /*at this point we expect cell0 to be active+learning, cell1 to be inactive*/
  if(!cell0->isActive)
    printf("Failed: temporalPooling1 expect cell0 to be active, got inactive.\n");
  if(!cell0->isLearning)
    printf("Failed: temporalPooling1 expect cell0 to be learning, got false.\n");
  if(cell1->isActive)
    printf("Failed: temporalPooling1 expect cell1 to be inactive, got active.\n");

  /*we expect cell1 to have a new segment with a synapse to cell0*/
  data[0] = 0;
  data[1] = 1;
  runOnce(region);


  if(cell1->numSegments!=1) {
    printf("Failed: runOnce2 expect cell1.numSegments to be 1, got %i\n",
        cell1->numSegments);
  }
  else {
    int nsyn = cell1->segments[0].numSynapses;
    if(nsyn!=1)
      printf("Failed: runOnce2 expect cell0.seg0.numSyn to be 1, got %i.\n", nsyn);
    else {
      Synapse* syn = &(cell1->segments[0].synapses[0]);
      if(syn->inputSource != cell0)
        printf("Failed: runOnce2 expect cell1.seg0.syn0 to connect to cell0.\n");
    }
  }

  deleteRegion(region);
  free(region);
  free(data);

  printf("OK\n");
}

/**
 * This test creates a hardcoded Region of size 250x1 and feeds in data that
 * has 10% (25) elements active.  We then repeat the same sequence 10 times to
 * try to teach the region to learn the full sequence.
 */
void testRegion2() {
  printf("testRegion2()...\n");

  float acc[2];
  char* data = malloc(250 * sizeof(char));
  Region* region = newRegionHardcoded(250,1, 0, 1, 3, 4, data);

  /*create a sequence of length 10.  repeat it 10 times and check region accuracy. */
  int i,j,k;
  for(k=0; k<10; ++k) {
    for(i=0; i<10; ++i) {
      for(j=0; j<250; ++j) /*reset all data to 0*/
        data[j] = 0;
      for(j=0; j<25; ++j) /*assign next set of 25 to 1's*/
        data[(i*25)+j] = 1;

      runOnce(region);

      getLastAccuracy(region, acc);

      if(k>1 || (k==1 && i>=1)) {
        /*after 1 full sequence presented, we expect 100% accuracy*/
        if(acc[0]!=1.0f && acc[1]!=1.0f) {
          printf("Failed: testRegion2 expect 100%% acc (%i %i), got %f, %f\n",
              k, i, acc[0],acc[1]);
        }/*printf("k%i i%i:  aAcc=%f  pAcc=%f\n", k, i, acc[0], acc[1]);*/
      }
      else {
        /*before that we expect 0% accuracy*/
        if(acc[0]!=0.0f && acc[1]!=0.0f) {
          printf("Failed: testRegion2 expect 0%% acc (%i %i), got %f, %f\n",
              k, i, acc[0],acc[1]);
        }
      }
    }
  }

  deleteRegion(region);
  free(region);
  free(data);

  printf("OK\n");
}

/**
 * This test creates a Region of size 32x32 columsn that accepts a larger
 * input of size 128x128.  Each input has a 128x128 sparse bit representation with about
 * 5% of the bits active.  This example is much closer to a Region that works on
 * real world sized data.  It tests the ability of the spatial pooler to produce a
 * sparse represenation in a 32x32 column grid from a much larger 128x128 input array.
 */
void testRegion3() {
  printf("testRegion3()...\n");

  int i,j,k;
  int iters = 0;
  int dataSize = 16384;

  float acc[2];
  char* data = malloc(dataSize * sizeof(char));

  int inputSizeX = 128; /*input data is size 10x10*/
  int inputSizeY = 128;
  int colGridSizeX = 32;/*region's column grid is size 5x5*/
  int colGridSizeY = 32;
  float pctInputPerCol = 0.01; /*each column connects to 1% random input bits*/
  float pctMinOverlap = 0.07;  /*8% (13) of column bits at minimum to be active*/
  int localityRadius = 0;      /*columns can connect anywhere within input*/
  float pctLocalActivity = 0.5;/*half of columns within radius inhibited*/
  int cellsPerCol = 4;
  int segActiveThreshold = 10;
  int newSynapseCount = 10;

  char* outData = malloc(colGridSizeX * colGridSizeY);

  Region* region = newRegion(inputSizeX, inputSizeY, colGridSizeX, colGridSizeY,
        pctInputPerCol, pctMinOverlap, localityRadius, pctLocalActivity, cellsPerCol,
        segActiveThreshold, newSynapseCount, data);
  region->temporalLearning = true;

  for(k=0; k<10; ++k) {
    for(i=0; i<10; ++i) {
      iters++;
      /*data will contain a 128x128 bit representation*/
      for(j=0; j<dataSize; ++j) /*reset all data to 0*/
        data[j] = 0;
      for(j=0; j<dataSize/10; ++j) /*assign next 10% set to 1's*/
        data[(i*(dataSize/10))+j] = 1;

      runOnce(region);

      getLastAccuracy(region, acc);
      if(DEBUG)
        printf("\niter%i  Acc: %f  %f", iters, acc[0], acc[1]);

      int nc = numRegionActiveColumns(region);
      if(DEBUG)
        printf(" nc:%d", nc);

      /*Get the current column predictions.  outData is size 32x32 to match the
       * column grid.  each value represents whether the column is predicted to
       * happen soon.  a value of 1 indicates the column is predicted to be active
       * in t+1, value of 2 for t+2, etc.  value of 0 indicates column is not
       * being predicted any time soon. */
      getColumnPredictions(region, outData);
      int p,n1=0, n2=0, n3=0;
      for(p=0; p<region->numCols; ++p) {
        n1 += outData[p]==1 ? 1 : 0;
        n2 += outData[p]==2 ? 1 : 0;
        n3 += outData[p]==3 ? 1 : 0;
      }
      if(DEBUG)
        printf(" np:%i %i %i", n1, n2, n3);
    }
    if(DEBUG)
      printf("\n");
  }
  if(DEBUG)
    printf("total iters = %i\n", iters);

  deleteRegion(region);
  free(region);
  free(data);
  free(outData);

  printf("OK\n");
}

/**
 * This test creates a small Region of size 5x5 that is connected to an
 * input of size 10x10.  The input has 10% (10) elements active per time
 * step.
 */
void testRegionSpatialPooling1() {
  printf("testRegionSpatialPooling1()...\n");

  int inputSizeX = 10; /*input data is size 10x10*/
  int inputSizeY = 10;
  int colGridSizeX = 5;/*region's column grid is size 5x5*/
  int colGridSizeY = 5;
  float pctInputPerCol = 0.05; /*each column connects to 5 random input bits*/
  float pctMinOverlap = 0.2;   /*20% (1) of column bits at minimum to be active*/
  int localityRadius = 0;      /*columns can connect anywhere within input*/
  float pctLocalActivity = 1;  /*half of columns within radius inhibited*/
  int cellsPerCol = 1; /*last 3 params only relevant when temporal learning enabled*/
  int segActiveThreshold = 1;
  int newSynapseCount = 1;

  float acc[2];
  char* data = malloc(100 * sizeof(char));

  Region* region = newRegion(inputSizeX, inputSizeY, colGridSizeX, colGridSizeY,
      pctInputPerCol, pctMinOverlap, localityRadius, pctLocalActivity, cellsPerCol,
      segActiveThreshold, newSynapseCount, data);
  region->temporalLearning = false;

  /*create a sequence of length 10.  repeat it 10 times and check region accuracy. */
  int i,j,k;
  for(k=0; k<10; ++k) {
    for(i=0; i<10; ++i) {
      for(j=0; j<100; ++j) /*reset all data to 0*/
        data[j] = 0;
      for(j=0; j<10; ++j) /*assign next set of 10 to 1's*/
        data[(i*10)+j] = 1;

      runOnce(region);

      int nc = numRegionActiveColumns(region);
      if(DEBUG)
        printf(" %d", nc);
    }
    if(DEBUG)
      printf("   rad=%f\n", region->inhibitionRadius);
  }

  deleteRegion(region);
  free(region);

  printf("OK\n");
}

/**
 * This test creates a hardcoded Region of size 25x25 (625) and runs
 * 10,000 iterations of the Region using randomly generated data
 * (40 active columns out of 625).  The nunique parameter defines
 * how many unique data configurations to randomly choose from between
 * iterations.  If zero passed in use true random data configurations
 * (no unique limit).  The performance stats are printed to standard
 * out every 1000 iterations.
 */
void testRegionPerformance(unsigned int nunique) {
  printf("testRegionPerformance(%i)...\n", nunique);

  int nx = 25;
  int ny = 25;
  int localityRadius = 0;
  int cellsPerCol = 4;
  int segActiveThreshold = 3;
  int newSynapseCount = 5;

  float acc[2];
  char* data = malloc(nx*ny * sizeof(char));
  Region* region = newRegionHardcoded(nx,ny, localityRadius, cellsPerCol,
      segActiveThreshold, newSynapseCount, data);

  /*create a sequence of length 10.  repeat it 10 times and check region accuracy. */
  int niters = 10000;
  int nactive = 40;
  int ncol = nx*ny;
  unsigned long si = 1;
  srand(42);

  unsigned long time = clock();
  double otime = 0;/*omp_get_wtime();*/

  int i,j,r;
  for(i=0; i<=niters; ++i) {
    /*select a random 40 data positions*/
    /*choose nact random column indicies to represent word*/
    for(j=0; j<ncol; ++j)
      data[j] = 0;

    /*if non-zero, reseed the rand using one of nunique seed values.*/
    if(nunique > 0) {
      srand(si*4101);
      si *= 5303;
      srand(rand() % nunique);
    }

    r=0;
    while(r < nactive) {
      int d = rand() % ncol;
      if(data[d]==0) {
        data[d] = 1;
        r++;
      }
    }

    runOnce(region);

    if(i % 1000 == 0) {
      unsigned long elapse = clock() - time;
      double oelapse = 1;/*omp_get_wtime() - otime;*/
      printf("iters %i: time %f (%lu)\n", i, oelapse, elapse/1000);

      /*print how many segments of particular counts that exist*/
      int sn;
      for(sn=0; sn<12; ++sn) {
        int scn = numRegionSegments(region, sn);
        printf("%i(%i)  ", sn, scn);
      }
      printf("\n");

      /*getLastAccuracy(region, acc);
      printf("acc  %f   %f\n", acc[0], acc[1]);*/

      time = clock();
      /*otime = omp_get_wtime();*/
    }
  }

  unsigned long elapse = clock() - time;
  printf("iters %i: time: %lu\n", niters, elapse/1000);

  deleteRegion(region);
  free(region);
  free(data);

  printf("OK\n");
}

/**
 * This test creates a hardcoded Region of size 25x25 (625) and runs
 * 10,000 iterations of the Region using data generated from reading
 * words in Charles Dickens Tale of Two Cities novel.  The words are
 * used to generate hash values that are then used as seeds for a
 * random value generator that then populates 40 active columns out of
 * the 625.  The performance stats are printed to standard out every
 * 1000 iterations.
 */
void testRegionPerformanceDickens() {
  printf("testRegionPerformanceDickens()...\n");

  int nx = 25;
  int ny = 25;
  int localityRadius = 0;
  int cellsPerCol = 4;
  int segActiveThreshold = 3;
  int newSynapseCount = 5;

  /*float acc[2];*/
  char* data = malloc(nx*ny * sizeof(char));
  Region* region = newRegionHardcoded(nx,ny, localityRadius, cellsPerCol,
      segActiveThreshold, newSynapseCount, data);

  /*create a sequence of length 10.  repeat it 10 times and check region accuracy. */
  int a,i,j,r, iters=0;
  int niters = 10000;
  int nactive = 40;
  int ncol = nx*ny;
  srand(42);

  /*read the file Tale of Two Cities*/
  FILE *fp;
  char fileName[] = "/Users/barry/Documents/A Tale of Two Cities (Charles Dickens).txt";
  char *source_str;
  size_t source_size;

  fp = fopen(fileName, "r");
  if (!fp) {
    fprintf(stderr, "Failed to load text file.\n");
    exit(1);
  }
  source_str = (char*) malloc(MAX_FILE_SIZE);
  source_size = fread(source_str, 1, MAX_FILE_SIZE, fp);
  fclose(fp);

  int wi = 0;
  bool lastWasLetter = false;
  unsigned int hash = 0;
  bool runIter = false;
  char* word = malloc(128);
  char endPunc[] = "!\"().;?[]{}";

  unsigned long time = clock();

  for(i=0; i<source_size; ++i) {
    /* one letter at a time.  stop when whitespace or punc.
     * when continuing, ignore whitespace or punc until letters again.*/
    char c = source_str[i];
    if((c >= 'a' && c <= 'z') || (c >= 'A' && c <= 'Z')) {
      word[wi++] = c;
      lastWasLetter = true;
    }
    else {
      if(wi > 0) {
        /*current word is built, run region with it and start next word*/
        word[wi++] = '\0';
        hash = 0;
        for(a = 0; a < wi; a++)
          hash = 31*hash + word[a];
        /*printf("%s\n", word);*/
        srand(hash);
        runIter = true;
        wi = 0;
      }
      else if(lastWasLetter) {
        /*starting a new word:
         * if endPunc, issue a blank data for the region
         * else just ignore*/
        for(a=0; a<11; ++a) {
          if(c == endPunc[a]) {
            /*found endPunc */
            srand(0);
            runIter = true;
            break;
          }
        }
      }
      lastWasLetter = false;
    }

    if(runIter) {
      for(j=0; j<ncol; ++j)
        data[j] = 0;

      r=0;
      while(r < nactive) {
        int d = rand() % ncol;
        if(data[d]==0) {
          data[d] = 1;
          r++;
        }
      }

      runOnce(region);

      /*getLastAccuracy(region, acc);*/

      if(iters % 1000 == 0) {
        unsigned long elapse = clock() - time;
        printf("iters %i: time %lu\n", iters, elapse/1000);

        /*print how many segments of particular counts that exist*/
        int sn;
        for(sn=0; sn<10; ++sn) {
          int scn = numRegionSegments(region, sn);
          printf("%i(%i)  ", sn, scn);
        }
        printf("\n");

        time = clock();
      }
      runIter = false;
      iters++;

      if(iters >= niters) break;
    }
  }

  unsigned long elapse = clock() - time;
  printf("iters %i: time: %lu\n", iters, elapse/1000);

  deleteRegion(region);
  free(region);
  free(data);

  printf("OK\n");
}

int main(void) {
  /* Run selected tests for HTM below */
  /*testOpenMP();*/
  testSynapse();
  testSegment();
  testRegion1();
  testRegion2();
  testRegionSpatialPooling1();
  /*testRegionPerformance(10);*/
  /*testRegionPerformance(0);*/
  /*testRegionPerformanceDickens();*/
  testRegion3();

	return EXIT_SUCCESS;
}
