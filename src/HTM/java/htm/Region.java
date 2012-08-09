package htm;

import htm.Column.CellAndSegment;

import java.awt.Point;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.HashSet;
import java.util.List;
import java.util.Random;
import java.util.Set;
import java.util.TreeSet;
import java.util.concurrent.ForkJoinPool;
import java.util.concurrent.RecursiveAction;

/**
 * Region.java
 *
 *  Author: Barry Maturkanich
 *
 *  Code to represent an entire Hierarchical Temporal Memory (HTM) Region of
 *  Columns that implement Numenta's new Cortical Learning Algorithms (CLA).
 *
 *  The Region is defined by a matrix of columns, each of which contains several
 *  cells.  The main idea is that given a matrix of input bits, the Region will
 *  first sparsify the input such that only a few Columns will become 'active'.
 *  As the input matrix changes over time, different sets of Columns will
 *  become active in sequence.  The Cells inside the Columns will attempt
 *  to learn these temporal transitions and eventually the Region will be
 *  able to make predictions about what may happen next given what has happened
 *  in the past.
 *
 *  For (much) more information, visit www.numenta.com.
 *
 *  SpatialPooling snippet from the Numenta docs:
 *
 *  The code computes activeColumns(t) = the list of columns that win due to
 *  the bottom-up input at time t. This list is then sent as input to the
 *  temporal pooler routine.
 *
 *  Phase 1: compute the overlap with the current input for each column
 *  Phase 2: compute the winning columns after inhibition
 *  Phase 3: update synapse permanence and internal variables
 *
 *  1) Start with an input consisting of a fixed number of bits. These bits might represent
 *     sensory data or they might come from another region lower in the hierarchy.
 *  2) Assign a fixed number of columns to the region receiving this input. Each column has
 *     an associated dendrite segment. Each dendrite segment has a set of potential synapses
 *     representing a subset of the input bits. Each potential synapse has a permanence value.
 *     Based on their permanence values, some of the potential synapses will be valid.
 *  3) For any given input, determine how many valid synapses on each column are
 *     connected to active input bits.
 *  4) The number of active synapses is multiplied by a 'boosting' factor which is
 *     dynamically determined by how often a column is active relative to its neighbors.
 *  5) The columns with the highest activations after boosting disable all but a fixed
 *     percentage of the columns within an inhibition radius. The inhibition radius is
 *     itself dynamically determined by the spread (or 'fan-out') of input bits. There is
 *     now a sparse set of active columns.
 *  6) For each of the active columns, we adjust the permanence values of all the potential
 *     synapses. The permanence values of synapses aligned with active input bits are
 *     increased. The permanence values of synapses aligned with inactive input bits are
 *     decreased. The changes made to permanence values may change some synapses from being
 *     valid to not valid, and vice-versa.
 */
public class Region {
  
  private final int _inputWidth, _inputHeight;
  private final int _localityRadius;
  private final int _cellsPerCol;
  private final int _segActiveThreshold;
  private final int _newSynapseCount;

  private final float _pctInputPerCol;
  private final float _pctMinOverlap;
  private final float _pctLocalActivity;

  private boolean _spatialLearning = false;
  private boolean _temporalLearning = false;
  private boolean _hardcodedSpatial = false;

  private final int _width, _height;
  private final double _xSpace, _ySpace;

  private final Column[] _columns;

  private final float _minOverlap;
  private float _inhibitionRadius;
  private final int _desiredLocalActivity;

  private final byte[] _inputData; //TODO: optimize for space with BitSet?
  private int _iters;
  
  private final ForkJoinPool _forkJoinPool = new ForkJoinPool();

  public static final float RAD_BIAS_PEAK = 0.8f; //input-bit radius bias peak for default proximal perms
  public static final float RAD_BIAS_STD_DEV = 0.25f; //input-bit radius standard deviation bias
  public static final boolean DEBUG = true;
  /** 
   * If true, default all proximal synapses to full permanence (=1.0)
   * otherwise use Numenta doc method of guassian centered on threshold.
   */
  public static boolean FULL_DEFAULT_SPATIAL_PERMANENCE = false;
  
  /**
   *  Region initialization using hard-coded spatial pooler.  Hard-coded means
   *  that input bits are mapped directly to columns.  In other words the normal
   *  spatial pooler is disabled and we instead assume the input sparsification
   *  has already been decided by some preprocessing code outside the Region.
   *  It is then assumed (though not checked) that the input array will have
   *  only a sparse number of "1" values that represent the active columns
   *  for each time step.<p>
   *  
   *  With hardcoded the Region will create a matching number of Columns to
   *  mirror the size of the input array.  Locality radius may still be
   *  defined as it is still used by the temporal pooler.  If non-zero it will
   *  restrict temporal segments from connecting further than r number of
   *  columns away.
   *
   *  @param inputSizeX size of input data matrix from the external source.
   *  @param inputSizeY size of input data matrix from the external source.
   *  @param localityRadius Furthest number of columns away to allow distal synapses.
   *  @param cellsPerCol Number of (temporal context) cells to use for each Column.
   *  @param segActiveThreshold Number of active synapses to activate a segment.
   *  @param newSynapseCount number of new distal synapses added if none activated during
   *  learning.
   *  @param inputData the array to be used for input data bits.  The contents
   *  of this array must be externally updated between time steps (between
   *  calls to Region.runOnce()).
   */
  public Region(int inputSizeX, int inputSizeY, int localityRadius,
      int cellsPerCol, int segActiveThreshold, int newSynapseCount, 
      byte[] inputData) {
    _inputWidth = inputSizeX;
    _inputHeight = inputSizeY;
    _iters = 0;
    _inputData = inputData;

    _localityRadius = localityRadius;
    _cellsPerCol = cellsPerCol;
    _segActiveThreshold = segActiveThreshold;
    _newSynapseCount = newSynapseCount;

    _width = inputSizeX;
    _height = inputSizeY;
    _xSpace = 1.0;
    _ySpace = 1.0;

    //Create the columns based on the size of the input data to connect to.
    _columns = new Column[_width*_height];
    for(int cx=0; cx<_width; ++cx) {
      for(int cy=0; cy<_height; ++cy) {
        _columns[(cy*_width)+cx] = new Column(this, cx, cy, cx, cy);
      }
    }
    
    _pctInputPerCol = 1.0f / _columns.length;
    _pctMinOverlap = 1.0f;
    _pctLocalActivity = 1.0f;
    _minOverlap = 1.0f;
    _desiredLocalActivity = 1;
    
    setSpatialHardcoded(true);
    setSpatialLearning(false);
  }

  /**
   *  Region Initialization (from Numenta docs):
   *  Prior to receiving any inputs, the region is initialized by computing a list of initial
   *  potential synapses for each column. This consists of a random set of inputs selected
   *  from the input space. Each input is represented by a synapse and assigned a random
   *  permanence value. The random permanence values are chosen with two criteria.
   *  First, the values are chosen to be in a small range around connectedPerm (the minimum
   *  permanence value at which a synapse is considered "connected"). This enables potential
   *  synapses to become connected (or disconnected) after a small number of training
   *  iterations. Second, each column has a natural center over the input region, and the
   *  permanence values have a bias towards this center (they have higher values near
   *  the center).
   *
   *  In addition to this I have added a concept of Locality Radius, which is an
   *  additional parameter to control how far away synapse connections can be made
   *  instead of allowing connections anywhere.  The reason for this is that in the
   *  case of video images I wanted to experiment with forcing each Column to only
   *  learn on a small section of the total input to more effectively learn lines or
   *  corners in a small section without being 'distracted' by learning larger patterns
   *  in the overall input space (which hopefully higher hierarchical Regions would
   *  handle more successfully).  Passing in 0 for locality radius will mean no restriction
   *  which will more closely follow the Numenta doc if desired.
   *
   *  @param inputSize (x,y) size of input data matrix from the external source.
   *  @param colGridSize (x,y) number of Columns to create to represent this Region.
   *  @param pctInputPerCol Percent of input bits each Column has potential synapses for.
   *  @param pctMinOverlap Minimum percent of column's synapses for column to be considered.
   *  @param localityRadius Furthest number of columns away to allow distal synapses.
   *  @param pctLocalActivity Approximate percent of Columns within locality radius to be
   *  winners after inhibition.
   *  @param cellsPerCol Number of (temporal context) cells to use for each Column.
   *  @param segActiveThreshold Number of active synapses to activate a segment.
   *  @param newSynapseCount number of new distal synapses added if none activated during
   *  learning.
   *  @param inputData the array to be used for input data bits.  The contents
   *  of this array must be externally updated between time steps (between
   *  calls to Region.runOnce()).
   */
  public Region(int inputSizeX, int inputSizeY, int colGridSizeX, int colGridSizeY,
      float pctInputPerCol, float pctMinOverlap, int localityRadius,
      float pctLocalActivity, int cellsPerCol, int segActiveThreshold,
      int newSynapseCount, byte[] inputData) {
    if(DEBUG)
      System.out.println("Constructing Region...");

    _inputWidth = inputSizeX;
    _inputHeight = inputSizeY;
    _iters = 0;
    _inputData = inputData;

    _localityRadius = localityRadius;
    _cellsPerCol = cellsPerCol;
    _segActiveThreshold = segActiveThreshold;
    _newSynapseCount = newSynapseCount;

    _pctInputPerCol = pctInputPerCol;
    _pctMinOverlap = pctMinOverlap;
    _pctLocalActivity = pctLocalActivity;

    //Reduce the number of columns and map centers of input x,y correctly.
    //column grid will be relative to size of input grid in both dimensions
    _width = colGridSizeX;
    _height = colGridSizeY;
    _xSpace = (_inputWidth-1*1.0) / Math.max(1.0,(_width-1));
    _ySpace = (_inputHeight-1*1.0) / Math.max(1.0,(_height-1));

    //Create the columns based on the size of the input data to connect to.
    _columns = new Column[_width*_height];
    for(int cx=0; cx<_width; ++cx) {
      for(int cy=0; cy<_height; ++cy) {
        int srcPosX = (int)Math.round(cx*_xSpace);
        int srcPosY = (int)Math.round(cy*_ySpace);
        _columns[(cy*_height)+cx] = new Column(this, srcPosX, srcPosY, cx, cy);
      }
    }

//      #size the output array as double grid for 4-cell, else just pad the first
//      #array dimension for 2 or 3 cell (and same size if just 1-cell)
//      if cellsPerCol==4:
//        outShape = (len(self.columnGrid)*2, len(self.columnGrid[0])*2)
//      else:
//        outShape = (len(self.columnGrid)*cellsPerCol, len(self.columnGrid[0]))
//      self.outData = numpy.zeros(outShape, dtype=numpy.uint8)

    //how far apart are 2 Columns in terms of input space; calc radius from that
    double inputRadiusf = _localityRadius*_xSpace;

    //Now connect all potentialSynapses for the Columns
    int synapsesPerSegment = 1;
    if(_localityRadius==0) {
      synapsesPerSegment = 
        Math.round((_inputWidth*_inputHeight) * pctInputPerCol);
    }
    else {
      synapsesPerSegment = 
        (int)Math.round((inputRadiusf*inputRadiusf) * pctInputPerCol);
    }

    //The minimum number of inputs that must be active for a column to be
    //considered during the inhibition step.
    _minOverlap = synapsesPerSegment * pctMinOverlap;

    int longerSide = Math.max(_inputWidth, _inputHeight);
    Random rand = new Random(80);
    
    int inputRadius = (int)Math.round(inputRadiusf);
    int minY = 0;
    int maxY = _inputHeight-1;
    int minX = 0;
    int maxX = _inputWidth-1;
    for(Column col : _columns) {
      //restrict synapse connections if localityRadius is non-zero
      if(_localityRadius > 0) {
        minY = Math.max(0, col.iy()-inputRadius);
        maxY = Math.min(_inputHeight-1, col.iy()+inputRadius);
        minX = Math.max(0, col.ix()-inputRadius);
        maxX = Math.min(_inputWidth-1, col.ix()+inputRadius);
      }
      
      //ensure we sample unique input positions to connect synapses to
      Set<Point> allPos = new HashSet<Point>();
      for(int x=minX; x<=maxX; ++x) {
        for(int y=minY; y<=maxY; ++y)
          allPos.add(new Point(x,y));
      }
      
      Set<Point> randPos = new HashSet<Point>();
      Util.createRandomSubset(allPos, randPos, synapsesPerSegment, rand);
      for(Point pt : randPos) {
        InputCell icell = new InputCell(
            pt.x, pt.y, (pt.y*_inputHeight)+pt.x, _inputData);
        if(FULL_DEFAULT_SPATIAL_PERMANENCE)
          col.addProximalSynapse(icell, 1.0f);
        else {
          double permanence = Synapse.CONNECTED_PERM + 
                             (Synapse.PERMANENCE_INC*rand.nextGaussian());
          permanence = Math.max(0.0, permanence);
          double dx = col.ix()-pt.x;
          double dy = col.iy()-pt.y;
          double distance = Math.sqrt((dx*dx) + (dy*dy));
          double ex = distance / (longerSide*RAD_BIAS_STD_DEV);
          double localityBias = (RAD_BIAS_PEAK/0.4) * Math.exp((ex*ex)/-2);
          col.addProximalSynapse(icell, (float)(permanence*localityBias));
        }
      }
    }

    _inhibitionRadius = averageReceptiveFieldSize();

    //desiredLocalActivity A parameter controlling the number of columns that will be
    float dla = 0;
    if(_localityRadius==0)
      dla = _inhibitionRadius * _pctLocalActivity;
    else
      dla = (_localityRadius*_localityRadius) * _pctLocalActivity;
    _desiredLocalActivity = Math.max(2, Math.round(dla));

    if(DEBUG) {
      System.out.println("Region Created (Java)");
      System.out.println("columnGrid = ("+colGridSizeX+","+colGridSizeY+")");
      System.out.println("xSpace, ySpace = "+_xSpace+" "+_ySpace);
      System.out.println("inputRadius = "+inputRadius);
      System.out.println("desiredLocalActivity = "+_desiredLocalActivity);
      System.out.println("synapsesPerProximalSegment = "+synapsesPerSegment);
      System.out.println("minOverlap = "+_minOverlap);
      System.out.println("conPerm,permInc = "+
          Synapse.CONNECTED_PERM+" "+Synapse.PERMANENCE_INC+"\n");
      //printf("outputGrid = ", outData.shape);
    }
  }
  
  /////  Accessor methods ///////////////////////////////
  public int getID() { return hashCode(); } //TODO more formal ID
  public int getWidth() { return _width; }
  public int getHeight() { return _height; }
  public int getInputWidth() { return _inputWidth; }
  public int getInputHeight() { return _inputHeight; }

  public float getPctInputPerCol() { return _pctInputPerCol; }
  public float getPctMinOverlap() { return _pctMinOverlap; }
  public float getPctLocalActivity() { return _pctLocalActivity; }

  public int getLocalityRadius() { return _localityRadius; }
  public int getNewSynapseCount() { return _newSynapseCount; }
  public int getCellsPerCol() { return _cellsPerCol; }

  public int getSegActiveThreshold() { return _segActiveThreshold; }
  public float getMinOverlap() { return _minOverlap; }
  public float getInhibitionRadius() { return _inhibitionRadius; }

  /**
   * Method to enable hardcoded spatial pooling.  When hardcoded no spatial
   * pooling is performed, instead the Region assumes that input bits equaling
   * '1' represent active columns per time step.  In this mode the input data
   * length must match the column array length.
   */
  public void setSpatialHardcoded(boolean hardcode) {
    _hardcodedSpatial = hardcode;//if true, assume inputs are the active columns
  }
  public void setSpatialLearning(boolean learn) { 
    _spatialLearning = learn; 
  }
  public void setTemporalLearning(boolean learn) {
    _temporalLearning = learn;;
  }

  /**
   * Get a reference to the Column at the specified column grid coordinate.
   * @param x the x coordinate component of the column's position.
   * @param y the y coordinate component of the column's position.
   * @return a reference to the Column at that position.
   * @throws ArrayIndexOutOfBoundsException if the position doesn't exist.
   */
  public Column getColumn(int x, int y) { 
    return _columns[(y*_height)+x]; 
  }
  
  /**
   * Get a reference to the Column at the specified column array index.
   * @param i the serial array index of the column's position.
   * @return a reference to the Column at that position.
   * @throws ArrayIndexOutOfBoundsException if the position doesn't exist.
   */
  public Column getColumn(int i) { 
    return _columns[i]; 
  }

  /**
   *  Run one time step iteration for this Region.  All cells will have their current
   *  (last run) state pushed back to be their new previous state and their new current
   *  state reset to no activity.  Then SpatialPooling following by TemporalPooling is
   *  performed for one time step.
   */
  private long _startTime;
  public void runOnce() {
    if(DEBUG && _iters==0) {
      _startTime = System.nanoTime();
    }

    for(Column col : _columns)
      col.nextTimeStep();

    //performSpatialPooling();
    performSpatialPoolingParallel();
    //performTemporalPooling(); 
    performTemporalPoolingParallel();

    ++_iters;
    if(DEBUG && _iters % 1000 == 0) {
      long taken = (System.nanoTime()-_startTime) / 1000000l;
      System.out.println("Region iters: "+_iters+" ("+taken+" ms)");
      
      //print how many segments of particular counts that exist
      int sn;
      for(sn=0; sn<12; ++sn) {
        int scn = numRegionSegments(sn);
        System.out.print(""+sn+"("+scn+")  ");
      }
      System.out.print("\n");
      
      _startTime = System.nanoTime();
    }
  }

  /**
   *  Determine the output bit-matrix of the most recently run time step
   *  for this Region.  The Region output is a byte array representing all
   *  Cells present in the Region.  Bytes are set to 1 if a Cell is active or
   *  predicting, all other bytes are 0.  The output data is a byte
   *  array of length equal to the number of cells in this Region.
   *  The method will zero-out all data in the specified byte array and then
   *  populate 1's where cells are either active or predicting.
   */
  public void getOutput(byte[] outData) {
    Arrays.fill(outData, (byte)0); //zero-out data to start
    for(Column col : _columns) {
      for(int i=0; i<col.numCells(); ++i) {
        Cell cell = col.getCell(i);
        if(cell.isActive() || cell.isPredicting()) {
          int cx = (col.cx()*_cellsPerCol) + cell.getIndex();
          outData[(col.cy()*_height)+cx] = (byte)1;
        }
      }
    }
  }
  
  /**
   * Populate the outData array with the current prediction values for each
   * column in the Region.  The value returned for a column represents the
   * fewest number of time steps the column believes an activation will occur.
   * For example a 1 value means the column is predicting it will become active
   * in the very next time step (t+1).  A value of 2 means it expects activation
   * in 2 time steps (t+2) etc.  A value of 0 means the column is not currently
   * making any prediction.
   * @param outData this array will be populated with the prediction values for
   * each column in the region based on the most recently processed time step.
   * This array must be have length equal to the number of columns in the 
   * region.
   */
  public void getColumnPredictions(byte[] outData) {
    assert outData.length==_width*_height;
    Arrays.fill(outData, (byte)0);
    for(Column col : _columns) {
      //if a column has multiple predicting cells, find the one that is making
      //the prediction that will happen the earliest and store that value
      boolean colOK = false;
      byte p = (byte)Segment.MAX_TIME_STEPS;
      for(int i=0; i<col.numCells(); i++) {
        Cell cell = col.getCell(i);
        if(cell.isPredicting() && cell.getPredictionSteps()<p) {
          p = (byte)cell.getPredictionSteps();
          colOK = true;
        }
      }
      if(colOK)
        outData[(col.cy()*_width)+col.cx()] = p;
    }
  }

  /**
   *  Calculate both the activation accuracy and the prediction accuracy for all
   *  the column cells in this region within the last processed time step.
   *  The activation accuracy is the number of correctly predicted active columns
   *  out of the total active columns.  The prediction accuracy is the number of
   *  correctly predicted active columns out of the total sequence-segment
   *  predicted columns (most recent time step).
   *  @param result a float[2] (activationAcc, predictionAcc) that will contain
   *  the float values (between 0.0-1.0) of the most recent region accuracy.
   */
  public void getLastAccuracy(float[] result) {
    //want to know % active columns that were correctly predicted
    int sumP = 0;
    int sumA = 0;
    int sumAP = 0;
    for(Column col : _columns) {
      if(col.isActive())
        ++sumA;
      for(int c=0; c<col.numCells(); ++c) {
        Cell cell = col.getCell(c);
        boolean addP = false;
        if(cell.wasPredicted()) {
          for(int s=0; s<cell.numSegments(); ++s) {
            Segment seg = cell.getSegment(s);
            if(seg.wasActive() && seg.isSequence()) {
              addP = true;
              break;
            }
          }
        }
        if(addP) {
          ++sumP;
          if(col.isActive())
            ++sumAP;
          break;
        }
      }
    }

    //compare active columns now, to predicted columns from t-1
    float pctA = 0.0f;
    float pctP = 0.0f;
    if(sumA > 0)
      pctA = (float)sumAP / (float)sumA;
    if(sumP > 0)
      pctP = (float)sumAP / (float)sumP;
    result[0] = pctA;
    result[1] = pctP;
  }
  
  /**
   * Return the total number of segments in the Region that match the number of
   * predictionSteps. If pass in zero, return count of total segments regardless
   * of predictionSteps.
   */
  int numRegionSegments(int predictionSteps) {
    int c=0, i,j;
    for(i=0; i<_columns.length; ++i) {
      Column col = _columns[i];
      for(j=0; j<col.numCells(); ++j) {
        Cell cell = col.getCell(j);
        c += cell.numCellSegments(predictionSteps);
      }
    }
    return c;
  }
  
  /**
   * Container object that holds current Region statistics.
   * The arrays for segments and synapses are length 3 and represent
   * [total, sequence, non-sequence] segments respectively.
   * The statistics will represent a snapshot of the state of the Region
   * at the time the RegionStats object is created.
   */
  public static class RegionStats {
    private final Region _region;
    
    public float predicationAccuracy = 0.0f;
    public float activationAccuracy = 0.0f;
    
    public final int[] totalSegments = new int[3];
    public final double[] meanSegments = new double[3];
    public final int[] medianSegments = new int[3];
    public final int[] mostSegments = new int[3];
    
    public int pendingSegments = 0;
    public double meanPending = 0;
    public int medianPending = 0;
    public int mostPending = 0;
    
    public final int[] totalSynapses = new int[3];
    public final double[] meanSynapses = new double[3];
    public final int[] medianSynapses = new int[3];
    public final int[] mostSynapses = new int[3];
    
    public RegionStats(Region region) {
      _region = region;
      
      float[] acc = new float[2];
      _region.getLastAccuracy(acc);
      activationAccuracy = acc[0];
      predicationAccuracy = acc[1];
      
      TreeSet<Integer> pendCounts = new TreeSet<Integer>();
      List<TreeSet<Integer>> segCounts = new ArrayList<TreeSet<Integer>>();
      segCounts.add(new TreeSet<Integer>());
      segCounts.add(new TreeSet<Integer>());
      segCounts.add(new TreeSet<Integer>());
      List<TreeSet<Integer>> synCounts = new ArrayList<TreeSet<Integer>>();
      synCounts.add(new TreeSet<Integer>());
      synCounts.add(new TreeSet<Integer>());
      synCounts.add(new TreeSet<Integer>());
      
      Column[] columns = _region._columns;
      for(int i=0; i<columns.length; ++i) {
        Column col = columns[i];
        for(int c=0; c<col.numCells(); ++c) {
          Cell cell = col.getCell(c);
          
          //examine all segments
          for(int s=0; s<3; ++s) {
            int numSeg = cell.numSegments(s);
            totalSegments[s] += numSeg;
            if(numSeg > mostSegments[s])
              mostSegments[s] = numSeg;
            segCounts.get(s).add(numSeg);
          }
          
          //examine pending segment changes
          pendingSegments += cell.numSegmentUpdates();
          if(cell.numSegmentUpdates() > mostPending)
            mostPending = cell.numSegmentUpdates();
          pendCounts.add(cell.numSegmentUpdates());
          
          //examine all synapses
          for(int s=0; s<cell.numSegments(); ++s) {
            Segment seg = cell.getSegment(s);
            
            totalSynapses[0] += seg.numSynapses();
            if(seg.numSynapses() > mostSynapses[0])
              mostSynapses[0] = seg.numSynapses();
            synCounts.get(0).add(seg.numSynapses());
            
            int si = seg.isSequence() ? 1 : 2;
            totalSynapses[si] += seg.numSynapses();
            if(seg.numSynapses() > mostSynapses[si])
              mostSynapses[si] = seg.numSynapses();
            synCounts.get(si).add(seg.numSynapses());
          }
        }
      }
      
      meanPending = 
        pendingSegments / (double)(columns.length*_region._cellsPerCol);
      medianPending = (Integer)pendCounts.toArray()[pendCounts.size()/2];
      
      for(int i=0; i<synCounts.size(); ++i) {
        meanSegments[i] = 
          totalSegments[i] / (double)(columns.length*_region._cellsPerCol);
        medianSegments[i] = 
          (Integer)segCounts.get(i).toArray()[segCounts.get(i).size()/2];
        
        meanSynapses[i] = 
          totalSynapses[i] / (double)(totalSegments[i]);
        if(synCounts.get(i).size()>0) {
          medianSynapses[i] = 
            (Integer)synCounts.get(i).toArray()[synCounts.get(i).size()/2];
        }
      }
    }
  }
  
  /**
   * Scan the current state of the Region and return back a RegionStats
   * object representing a snapshot of statistics information about the 
   * segments and synapses in the Region.
   */
  public RegionStats getStats() {
    return new RegionStats(this);
  }

  /**
   *  Perform one time step of SpatialPooling for the current input in this Region.
   *  The result will be a subset of Columns being set as active as well
   *  as (proximal) synapses in all Columns having updated permanences and
   *  boosts, and the Region will update inhibitionRadius.
   *
   *  From the Numenta Docs:
   *  Phase 1: compute the overlap with the current input for each column.
   *  Given an input vector, the first phase calculates the overlap of each
   *  column with that vector. The overlap for each column is simply the number
   *  of connected synapses with active inputs, multiplied by its boost. If
   *  this value is below minOverlap, we set the overlap score to zero.
   *
   *  Phase 2: compute the winning columns after inhibition.
   *  The second phase calculates which columns remain as winners after the
   *  inhibition step. desiredLocalActivity is a parameter that controls the
   *  number of columns that end up winning. For example, if desiredLocalActivity
   *  is 10, a column will be a winner if its overlap score is greater than the
   *  score of the 10'th highest column within its inhibition radius.
   *
   *  Phase 3: update synapse permanence and internal variables.
   *  The third phase performs learning; it updates the permanence values of all
   *  synapses as necessary, as well as the boost and inhibition radius.
   *
   *  The main learning rule is implemented in lines 20-26. For winning columns,
   *  if a synapse is active, its permanence value is incremented, otherwise it
   *  is decremented. Permanence values are constrained to be between 0 and 1.
   *
   *  Lines 28-36 implement boosting. There are two separate boosting mechanisms
   *  in place to help a column learn connections. If a column does not win often
   *  enough (as measured by activeDutyCycle), its overall boost value is
   *  increased (line 30-32). Alternatively, if a column's connected synapses
   *  do not overlap well with any inputs often enough (as measured by
   *  overlapDutyCycle), its permanence values are boosted (line 34-36).
   *  Note: once learning is turned off, boost(c) is frozen.
   *  Finally at the end of Phase 3 the inhibition radius is recomputed (line 38).
   */
  private void performSpatialPooling() {
    //If hardcoded, we assume the inputs correspond directly to active columns
    if(_hardcodedSpatial) {
      for(int i=0; i<_columns.length; ++i)
        _columns[i].setActive(_inputData[i]==1);
      return;
    }

    //Phase 1: Compute Column Input Overlaps
    for(Column col : _columns)
      col.computeOverlap();

    //Phase 2: Compute Active Columns (Winners after inhibition)
    List<Column> neighborCols = new ArrayList<Column>();
    for(Column col : _columns) {
      col.setActive(false);
      if(col.getOverlap() > 0) {
        neighbors(neighborCols, col);
        float minLocalActivity = kthScore(neighborCols, _desiredLocalActivity);
        if(col.getOverlap() >= minLocalActivity)
          col.setActive(true);
      }
    }

    //Phase 3: Synapse Boosting (Learning)
    if(_spatialLearning) {
      for(Column col : _columns) {
        if(col.isActive())
          col.updatePermanences();
      }

      for(Column col : _columns)
        col.performBoosting();

      _inhibitionRadius = averageReceptiveFieldSize();
    }
  }
  
  /**
   * Run the multi-threaded parallel version of the spatial pooler.
   * The results should be identical to the serial version above.
   */
  private void performSpatialPoolingParallel() {
    //If hardcoded, we assume the inputs correspond directly to active columns
    if(_hardcodedSpatial) {
      for(int i=0; i<_columns.length; ++i)
        _columns[i].setActive(_inputData[i]==1);
      return;
    }
    else {
      SpatialPoolerTask phase1 = 
          new SpatialPoolerTask(this, _forkJoinPool.getParallelism());
      _forkJoinPool.invoke(phase1);
    }
  }
  
  /**
   * This task executes a single time-step of the temporal pooler where each
   * phase is processing the columns in parallel.  We break the column array
   * into ntask (number of cpus) number of segments.  Due to the nature to the
   * HTM we must process all columns within a phase before we can move on to
   * the next, so there is a limit to how much we can parallelize.
   */
  private static class SpatialPoolerTask extends RecursiveAction {
    private static final long serialVersionUID = 10L;
    private final Region _region;
    private final int _ntasks;
    public SpatialPoolerTask(Region region, int ntasks) {
      _region = region;
      _ntasks = ntasks;
    }

    @Override
    protected void compute() {
      int ns = _region._columns.length / _ntasks;
      int nr = _region._columns.length % _ntasks;
      Phase1[] tasks1 = new Phase1[_ntasks];
      Phase2And3[] tasks2 = new Phase2And3[_ntasks];
      for(int i=0; i<_ntasks; ++i) {
        int r = (i==_ntasks-1) ? nr : 0;
        tasks1[i] = new Phase1(_region, ns*i, ns+r);
        tasks1[i].fork();
        tasks2[i] = new Phase2And3(_region, ns*i, ns+r);
      }
      for(Phase1 task : tasks1)
        task.join();
      
      //Phase 2/3 after all Phase1 tasks completed
      for(int i=0; i<_ntasks; ++i)
        tasks2[i].fork();
      for(Phase2And3 task : tasks2)
        task.join();
      
      if(_region._spatialLearning)
        _region._inhibitionRadius = _region.averageReceptiveFieldSize();
    }
    
    /**
     * Run phase1 of 1 time-step of the spatial pooler on only the specified
     * columns within the column array of the Region.
     */
    private static class Phase1 extends RecursiveAction {
      private static final long serialVersionUID = 1L;
      private final Region _region;
      private final int _c0, _len;
      Phase1(Region region, int c0, int len) {
        _region = region;
        _c0 = c0;
        _len = len;
      }

      @Override
      protected void compute() {
        //Phase 1: Compute Column Input Overlaps
        for(int i=_c0; i<_c0+_len; ++i) {
          _region._columns[i].computeOverlap();
        }
      }
    }
    
    /**
     * Run phase2/3 of 1 time-step of the spatial pooler on only the specified
     * columns within the column array of the Region.
     */
    private static class Phase2And3 extends RecursiveAction {
      private static final long serialVersionUID = 23L;
      private final Region _region;
      private final int _c0, _len;
      Phase2And3(Region region, int c0, int len) {
        _region = region;
        _c0 = c0;
        _len = len;
      }
      
      @Override
      protected void compute() {
        //Phase 2: Compute Active Columns (Winners after inhibition)
        List<Column> neighborCols = new ArrayList<Column>();
        for(int i=_c0; i<_c0+_len; ++i) {
          Column col = _region._columns[i];
          col.setActive(false);
          if(col.getOverlap() > 0) {
            _region.neighbors(neighborCols, col);
            float minLocalActivity = _region.kthScore(neighborCols, 
                _region._desiredLocalActivity);
            if(col.getOverlap() >= minLocalActivity)
              col.setActive(true);
          }

          //Phase 3: Synapse Boosting (Learning)
          if(_region._spatialLearning) {
            if(col.isActive())
              col.updatePermanences();
            col.performBoosting();
            //_inhibitionRadius = averageReceptiveFieldSize();
          }
        }
      }
    }
  }

  /**
   *  Repopulate the Column list reference with all columns that are
   *  within inhibitionRadius of the specified input column.
   */
  void neighbors(List<Column> cols, Column col) {
    int irad = Math.round(_inhibitionRadius);
    int x0 = Math.max(0, Math.min(col.cx()-1, col.cx()-irad));
    int y0 = Math.max(0, Math.min(col.cy()-1, col.cy()-irad));
    int x1 = Math.min(_width, Math.max(col.cx()+1, col.cx()+irad));
    int y1 = Math.min(_height, Math.max(col.cy()+1, col.cy()+irad));

    x1 = Math.min(_width, x1+1); //extra 1's for correct looping
    y1 = Math.min(_height, y1+1);

    cols.clear();
    for(int x=x0; x<x1; ++x) {
      for(int y=y0; y<y1; ++y)
        cols.add(getColumn(x,y));
    }
  }

  /**
   * Given the list of columns, return the k'th highest overlap value.
   */
  private int kthScore(List<Column> cols, int k) {
    TreeSet<Integer> overlaps = new TreeSet<Integer>();
    for(Column col : cols)
      overlaps.add(col.getOverlap());
    int i = Math.max(0, overlaps.size()-k);
    return (Integer)overlaps.toArray()[i];
  }

  /**
   * The radius of the average connected receptive field size of all the columns.
   * The connected receptive field size of a column includes only the connected
   * synapses (those with permanence values >= connectedPerm). This is used to
   * determine the extent of lateral inhibition between columns.
   * @return the average connected receptive field size (in column grid space).
   */
  private float averageReceptiveFieldSize() {
    int n = 0;
    double sum = 0.0;
    List<Synapse> syns = new ArrayList<Synapse>();
    for(Column col : _columns) {
      syns.clear();
      col.getConnectedSynapses(syns);
      for(Synapse syn : syns) {
        double dx = col.ix()-syn.getCellIX();
        double dy = col.iy()-syn.getCellIY();
        double d = Math.sqrt(dx*dx + dy*dy);
        sum += (d / _xSpace);
        n++;
      }
    }
    return (float)(sum / n);
  }

  /**
   *  Perform one time step of Temporal Pooling for this Region.
   *
   *  From the Numenta Docs:
   *  The input to this code is activeColumns(t), as computed by the spatial pooler.
   *  The code computes the active and predictive state for each cell at the
   *  current timestep, t. The boolean OR of the active and predictive states
   *  for each cell forms the output of the temporal pooler for the next level.
   *
   *  Phase 1: compute the active state, activeState(t), for each cell.
   *  The first phase calculates the activeState for each cell that is in a winning column.
   *  For those columns, the code further selects one cell per column as the
   *  learning cell (learnState). The logic is as follows: if the bottom-up
   *  input was predicted by any cell (i.e. its predictiveState output was 1 due
   *  to a sequence segment), then those cells become active (lines 23-27).
   *  If that segment became active from cells chosen with learnState on, this
   *  cell is selected as the learning cell (lines 28-30). If the bottom-up input
   *  was not predicted, then all cells in the col become active (lines 32-34).
   *  In addition, the best matching cell is chosen as the learning cell (lines 36-41)
   *  and a new segment is added to that cell.
   *
   *  Phase 2: compute the predicted state, predictiveState(t), for each cell.
   *  The second phase calculates the predictive state for each cell. A cell will turn on
   *  its predictive state output if one of its segments becomes active, i.e. if
   *  enough of its lateral inputs are currently active due to feed-forward input.
   *  In this case, the cell queues up the following changes: a) reinforcement of the
   *  currently active segment (lines 47-48), and b) reinforcement of a segment that
   *  could have predicted this activation, i.e. a segment that has a (potentially weak)
   *  match to activity during the previous time step (lines 50-53).
   *
   *  Phase 3: update synapses.
   *  The third and last phase actually carries out learning. In this phase segment
   *  updates that have been queued up are actually implemented once we get feed-forward
   *  input and the cell is chosen as a learning cell (lines 56-57). Otherwise, if the
   *  cell ever stops predicting for any reason, we negatively reinforce the segments
   *  (lines 58-60).
   */
  private void performTemporalPooling() {
    //Phase 1: Compute cell active states and segment learning updates
    //18. for c in activeColumns(t)
    //19.
    //20.   buPredicted = false
    //21.   lcChosen = false
    //22.   for i = 0 to cellsPerColumn - 1
    //23.     if predictiveState(c, i, t-1) == true then
    //24.       s = getActiveSegment(c, i, t-1, activeState)
    //25.       if s.sequenceSegment == true then
    //26.         buPredicted = true
    //27.         activeState(c, i, t) = 1
    //28.         if segmentActive(s, t-1, learnState) then
    //29.           lcChosen = true
    //30.           learnState(c, i, t) = 1
    //31.
    //32.   if buPredicted == false then
    //33.     for i = 0 to cellsPerColumn - 1
    //34.       activeState(c, i, t) = 1
    //35.
    //36.   if lcChosen == false then
    //37.     i,s = getBestMatchingCell(c, t-1)
    //38.     learnState(c, i, t) = 1
    //39.     sUpdate = getSegmentActiveSynapses (c, i, s, t-1, true)
    //40.     sUpdate.sequenceSegment = true
    //41.     segmentUpdateList.add(sUpdate)
    for(Column col : _columns) {
      if(col.isActive()) {
        boolean buPredicted = false;
        boolean learningCellChosen = false;
        for(int c=0; c<col.numCells(); ++c) {
          Cell cell = col.getCell(c);
          if(cell.wasPredicted()) {
            Segment segment = cell.getPreviousActiveSegment();

            if(segment!=null && segment.isSequence()) {
              buPredicted = true;
              cell.setActive(true);

              if(_temporalLearning && segment.wasActiveFromLearning()) {
                learningCellChosen = true;
                cell.setLearning(true);
              }
            }
          }
        }

        if(!buPredicted) {
          for(int c=0; c<col.numCells(); ++c)
            col.getCell(c).setActive(true);
        }

        if(_temporalLearning && !learningCellChosen) {
          //printf("bestSeg for (%d %d)\n", col->cx(), col->cy());
          CellAndSegment cas = col.getBestMatchingCell(1, true);
          Cell bestCell = cas.cell;
          Segment bestSeg = cas.segment;
          bestCell.setLearning(true);

          //segUpdate is added internally to Cell's update list
          SegmentUpdateInfo segmentToUpdate =
              bestCell.updateSegmentActiveSynapses(true, bestSeg, true);
          segmentToUpdate.setNumPredictionSteps(1); //isSequence = true

          //#bestSeg may be partial-sort-of match, but it could dec-perm
          //#other syns from different step if cell overlaps...
          //
          //#try better minOverlap to prevent bad boosting?
          //#try to disable learning if predictions match heavily?
          //
          //#Do we need to enforce max segments per cell?
        }
      }
    }

    //Phase2
    //42. for c, i in cells
    //43.   for s in segments(c, i)
    //44.     if segmentActive(s, t, activeState) then
    //45.       predictiveState(c, i, t) = 1
    //46.
    //47.       activeUpdate = getSegmentActiveSynapses (c, i, s, t, false)
    //48.       segmentUpdateList.add(activeUpdate)
    //49.
    //50.       predSegment = getBestMatchingSegment(c, i, t-1)
    //51.       predUpdate = getSegmentActiveSynapses(
    //52.                                   c, i, predSegment, t-1, true)
    //53.       segmentUpdateList.add(predUpdate)
    for(Column col : _columns) {
      for(int c=0; c<col.numCells(); ++c) {
        Cell cell = col.getCell(c);
        
        //process all segments on the cell to cache the activity for later
        for(int s=0; s<cell.numSegments(); ++s)
          cell.getSegment(s).processSegment();
        
        for(int s=0; s<cell.numSegments(); ++s) {
          Segment seg = cell.getSegment(s);
          if(seg.isActive()) {
            cell.setPredicting(true);

            //a) reinforcement of the currently active segment
            if(_temporalLearning) {
              //add segment update to this cell
              //printf("updateSegment (%d,%d) is ",_columns[i].cx(), _columns[i].cy());
              cell.updateSegmentActiveSynapses(false, seg);
            }
            break;
          }
        }

        //b) reinforcement of a segment that could have predicted
        //   this activation, i.e. a segment that has a (potentially weak)
        //   match to activity during the previous time step (lines 50-53).
        if(_temporalLearning && cell.isPredicting()) {
          //printf("predSegment is ");
          Segment predSegment = cell.getBestMatchingPreviousSegment();
          
          //either update existing or add new segment for this cell considering
          //only segments matching the number of prediction steps of the
          //best currently active segment for this cell
          SegmentUpdateInfo predSegUpdate =
              cell.updateSegmentActiveSynapses(true, predSegment, true);
          if(predSegment==null)
            predSegUpdate.setNumPredictionSteps(cell.getPredictionSteps()+1);
        }
      }
    }

    //Phase3
    //54. for c, i in cells
    //55.   if learnState(c, i, t) == 1 then
    //56.     adaptSegments (segmentUpdateList(c, i), true)
    //57.     segmentUpdateList(c, i).delete()
    //58.   else if predictiveState(c, i, t) == 0 and predictiveState(c, i, t-1)==1 then
    //59.     adaptSegments (segmentUpdateList(c,i), false)
    //60.     segmentUpdateList(c, i).delete()
    if(!_temporalLearning)
      return;
    for(Column col : _columns) {
      for(int c=0; c<col.numCells(); ++c) {
        Cell cell = col.getCell(c);
        if(cell.isLearning()) {
          cell.applySegmentUpdates(true);
        }
        else if(!cell.isPredicting() && cell.wasPredicted()) {
          cell.applySegmentUpdates(false);
        }
      }
    }
  }
  
  /**
   * Run the multi-threaded parallel version of th temporal pooler.
   * The results should be identical to the serial version above.
   */
  private void performTemporalPoolingParallel() {
    TemporalPoolerTask phase1 = 
        new TemporalPoolerTask(this, _forkJoinPool.getParallelism());
    _forkJoinPool.invoke(phase1);
  }
  
  /**
   * This task executes a single time-step of the temporal pooler where each
   * phase is processing the columns in parallel.  We break the column array
   * into ntask (number of cpus) number of segments.  Due to the nature to the
   * HTM we must process all columns within a phase before we can move on to
   * the next, so there is a limit to how much we can parallelize.
   */
  private static class TemporalPoolerTask extends RecursiveAction {
    private static final long serialVersionUID = 10L;
    private final Region _region;
    private final int _ntasks;
    public TemporalPoolerTask(Region region, int ntasks) {
      _region = region;
      _ntasks = ntasks;
    }

    @Override
    protected void compute() {
      int ns = _region._columns.length / _ntasks;
      int nr = _region._columns.length % _ntasks;
      Phase1[] tasks1 = new Phase1[_ntasks];
      Phase2[] tasks2 = new Phase2[_ntasks];
      for(int i=0; i<_ntasks; ++i) {
        int r = (i==_ntasks-1) ? nr : 0;
        tasks1[i] = new Phase1(_region, ns*i, ns+r);
        tasks1[i].fork();
        tasks2[i] = new Phase2(_region, ns*i, ns+r);
      }
      for(Phase1 task : tasks1)
        task.join();
      
      //Phase 2 after all Phase1 tasks completed
      for(int i=0; i<_ntasks; ++i)
        tasks2[i].fork();
      for(Phase2 task : tasks2)
        task.join();
      
      //Phase 3 after all Phase2 tasks completed
      if(_region._temporalLearning) {
        Phase3[] tasks3 = new Phase3[_ntasks];
        for(int i=0; i<_ntasks; ++i) {
          int r = (i==_ntasks-1) ? nr : 0;
          tasks3[i] = new Phase3(_region, ns*i, ns+r);
          tasks3[i].fork();
        }
        for(Phase3 task : tasks3)
          task.join();
      }
    }
    
    /**
     * Run phase1 of 1 time-step of the temporal pooler on only the specified
     * columns within the column array of the Region.
     */
    private static class Phase1 extends RecursiveAction {
      private static final long serialVersionUID = 1L;
      private final Region _region;
      private final int _c0, _len;
      Phase1(Region region, int c0, int len) {
        _region = region;
        _c0 = c0;
        _len = len;
      }

      @Override
      protected void compute() {
        boolean learning = _region._temporalLearning;
        for(int i=_c0; i<_c0+_len; ++i) {
          Column col = _region._columns[i];
          if(col.isActive()) {
            boolean buPredicted = false;
            boolean learningCellChosen = false;
            for(int c=0; c<col.numCells(); ++c) {
              Cell cell = col.getCell(c);
              if(cell.wasPredicted()) {
                Segment segment = cell.getPreviousActiveSegment();

                if(segment!=null && segment.isSequence()) {
                  buPredicted = true;
                  cell.setActive(true);

                  if(learning && segment.wasActiveFromLearning()) {
                    learningCellChosen = true;
                    cell.setLearning(true);
                  }
                }
              }
            }

            if(!buPredicted) {
              for(int c=0; c<col.numCells(); ++c)
                col.getCell(c).setActive(true);
            }

            if(learning && !learningCellChosen) {
              //printf("bestSeg for (%d %d)\n", col->cx(), col->cy());
              CellAndSegment cas = col.getBestMatchingCell(1, true);
              Cell bestCell = cas.cell;
              Segment bestSeg = cas.segment;
              bestCell.setLearning(true);

              //segUpdate is added internally to Cell's update list
              SegmentUpdateInfo segmentToUpdate =
                  bestCell.updateSegmentActiveSynapses(true, bestSeg, true);
              segmentToUpdate.setNumPredictionSteps(1); //isSequence = true
            }
          }
        }
      }
    }
    
    /**
     * Run phase2 of 1 time-step of the temporal pooler on only the specified
     * columns within the column array of the Region.
     */
    private static class Phase2 extends RecursiveAction {
      private static final long serialVersionUID = 2L;
      private final Region _region;
      private final int _c0, _len;
      Phase2(Region region, int c0, int len) {
        _region = region;
        _c0 = c0;
        _len = len;
      }
      
      @Override
      protected void compute() {
        boolean learning = _region._temporalLearning;
        for(int i=_c0; i<_c0+_len; ++i) {
          Column col = _region._columns[i];
          for(int c=0; c<col.numCells(); ++c) {
            Cell cell = col.getCell(c);
            
            //process all segments on the cell to cache the activity for later
            for(int s=0; s<cell.numSegments(); ++s)
              cell.getSegment(s).processSegment();
            
            for(int s=0; s<cell.numSegments(); ++s) {
              Segment seg = cell.getSegment(s);
              if(seg.isActive()) {
                cell.setPredicting(true);
                //a) reinforcement of the currently active segment
                if(learning) {
                  //add segment update to this cell
                  //printf("updateSegment (%d,%d) is ",_columns[i].cx(), _columns[i].cy());
                  cell.updateSegmentActiveSynapses(false, seg);
                }
                break;
              }
            }

            //b) reinforcement of a segment that could have predicted
            //   this activation, i.e. a segment that has a (potentially weak)
            //   match to activity during the previous time step (lines 50-53).
            if(learning && cell.isPredicting()) {
              Segment predSegment = cell.getBestMatchingPreviousSegment();
              
              //either update existing or add new segment for this cell considering
              //only segments matching the number of prediction steps of the
              //best currently active segment for this cell
              SegmentUpdateInfo predSegUpdate =
                  cell.updateSegmentActiveSynapses(true, predSegment, true);
              if(predSegment==null)
                predSegUpdate.setNumPredictionSteps(cell.getPredictionSteps()+1);
            }
          }
        }
      }
    }
    
    /**
     * Run phase3 of 1 time-step of the temporal pooler on only the specified
     * columns within the column array of the Region.
     */
    private static class Phase3 extends RecursiveAction {
      private static final long serialVersionUID = 3L;
      private final Region _region;
      private final int _c0, _len;
      Phase3(Region region, int c0, int len) {
        _region = region;
        _c0 = c0;
        _len = len;
      }
      
      @Override
      protected void compute() {
        for(int i=_c0; i<_c0+_len; ++i) {
          Column col = _region._columns[i];
          for(int c=0; c<col.numCells(); ++c) {
            Cell cell = col.getCell(c);
            if(cell.isLearning()) {
              cell.applySegmentUpdates(true);
            }
            else if(!cell.isPredicting() && cell.wasPredicted()) {
              cell.applySegmentUpdates(false);
            }
          }
        }
      }
    }
  }

}
