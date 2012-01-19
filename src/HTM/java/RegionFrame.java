import htm.Region;
import htm.Region.RegionStats;

import java.awt.Color;
import java.awt.Dimension;
import java.awt.GridBagConstraints;
import java.awt.GridBagLayout;
import java.awt.event.ActionEvent;
import java.awt.event.ActionListener;
import java.awt.event.ItemEvent;
import java.awt.event.ItemListener;
import java.awt.event.KeyEvent;
import java.io.BufferedReader;
import java.io.FileNotFoundException;
import java.io.FileReader;
import java.io.IOException;
import java.text.DecimalFormat;
import java.text.NumberFormat;
import java.util.ArrayDeque;
import java.util.Arrays;
import java.util.Random;

import javax.swing.BorderFactory;
import javax.swing.JCheckBoxMenuItem;
import javax.swing.JFrame;
import javax.swing.JLabel;
import javax.swing.JMenu;
import javax.swing.JMenuBar;
import javax.swing.JMenuItem;
import javax.swing.JOptionPane;
import javax.swing.JPanel;
import javax.swing.KeyStroke;
import javax.swing.event.ChangeEvent;
import javax.swing.event.ChangeListener;

/**
 * A top-level UI window that displays a menu with options for running
 * time steps of an HTM Region.  Within the window is a RegionPanel which
 * renders a visualization of the current state of the Region.
 * Currently the Region parameters and inputs are hardcoded.
 * The input is a text file defined by the INPUT_FILE static variable.
 * The Region is defined as having 25x25 columns.  When reading from the
 * text file, each word is used to seed a random number the used to select
 * a random 40 bits (or columns directly if spatial pooling is hardcoded)
 * in a byte array to be 1's (the rest 0).
 * Finally, the UI displays a set of statistics about the Region including
 * how many segments and synapses are present over time.
 * @author Barry Maturkanich
 */
public class RegionFrame extends JPanel {

  private static final long serialVersionUID = 1L;
  
  private static final String INPUT_FILE = 
    //"C:/Apps/Numenta/input.txt";
    "C:/Apps/Numenta/classics/A Tale of Two Cities (Charles Dickens).txt";
  
  private static final String punctuation = "\"!#$%&'()*+,-./:;<=>?@[]^_`{|}~\"";
  private static final String[] PUNC = {"!","\"","(",")",".",";","?","[","]","{","}"};
  
  private ArrayDeque<String> _lastLine = null;
  private boolean _isWordBreak = false;
  private Region _region;
  private Dimension _regionShape;
  private RegionPanel _regionPanel;
  private Random _rand = new Random();
  private byte[] _inputData;
  private Thread _thread;
  private final ChangeListener _statListener;
  private BufferedReader _buffer;
  private final NumberFormat _nf;
  
  public static void main(String[] args) {
    // Schedule a job for the event-dispatching thread:
    // creating and showing this application's GUI.
    javax.swing.SwingUtilities.invokeLater(new Runnable() {
      public void run() {
        new RegionFrame();
      }
    });
  }
  
  public RegionFrame() {
    super(new GridBagLayout());
    setBorder(BorderFactory.createLineBorder(Color.black));
    _nf = DecimalFormat.getInstance();
    _nf.setMaximumFractionDigits(3);
    
    //Status labels:
    //accuracies (pred acc, active acc, last+average)
    //total segments, average per cell, most any cell
    //total segUpdates, average per cell, most any cell
    //total synapses, average per segment, most any segment
    JPanel labelArea = new JPanel(new GridBagLayout());
    
    JPanel accArea = new JPanel(new GridBagLayout());
    accArea.setBorder(BorderFactory.createTitledBorder("Region Accuracy"));
    final JLabel predAccLabel0 = new JLabel(" Prediction Acc: ");
    final JLabel predAccLabel = new JLabel("100%");
    final JLabel activeAccLabel0 = new JLabel(" Activation Acc: ");
    final JLabel activeAccLabel = new JLabel("100%");
    final JLabel predMAccLabel0 = new JLabel("  Mean Pred Acc: ");
    final JLabel predMAccLabel = new JLabel("0%");
    final JLabel activeMAccLabel0 = new JLabel("  Mean Active Acc: ");
    final JLabel activeMAccLabel = new JLabel("0%");
    accArea.add(predAccLabel0, setGrid(0,0));
    accArea.add(predAccLabel, setGrid(1,0));
    accArea.add(activeAccLabel0, setGrid(0,1));
    accArea.add(activeAccLabel, setGrid(1,1));
    accArea.add(predMAccLabel0, setGrid(0,2));
    accArea.add(predMAccLabel, setGrid(1,2));
    accArea.add(activeMAccLabel0, setGrid(0,3));
    accArea.add(activeMAccLabel, setGrid(1,3));
    
    final JLabel[] totalSegLabel = new JLabel[3];
    final JLabel[] meanSegLabel = new JLabel[3];
    final JLabel[] medSegLabel = new JLabel[3];
    final JLabel[] mostSegLabel = new JLabel[3];
    
    JPanel segArea = new JPanel(new GridBagLayout());
    segArea.setBorder(BorderFactory.createTitledBorder("Cell Segments"));
    final JLabel totalSegLabel0 = new JLabel(" Total Segments: ");
    totalSegLabel[0] = new JLabel("0");
    final JLabel meanSegLabel0 = new JLabel(" Mean Segments: ");
    meanSegLabel[0] = new JLabel("0");
    final JLabel medSegLabel0 = new JLabel(" Median Segments: ");
    medSegLabel[0] = new JLabel("0");
    final JLabel mostSegLabel0 = new JLabel(" Most Segments: ");
    mostSegLabel[0] = new JLabel("0");
    segArea.add(totalSegLabel0, setGrid(0,0));
    segArea.add(totalSegLabel[0], setGrid(1,0));
    segArea.add(meanSegLabel0, setGrid(0,1));
    segArea.add(meanSegLabel[0], setGrid(1,1));
    segArea.add(medSegLabel0, setGrid(0,2));
    segArea.add(medSegLabel[0], setGrid(1,2));
    segArea.add(mostSegLabel0, setGrid(0,3));
    segArea.add(mostSegLabel[0], setGrid(1,3));
    
    JPanel seg1Area = new JPanel(new GridBagLayout());
    seg1Area.setBorder(BorderFactory.createTitledBorder("Sequence Segments"));
    final JLabel totalSeg1Label0 = new JLabel(" Total Sequence: ");
    totalSegLabel[1] = new JLabel("0");
    final JLabel meanSeg1Label0 = new JLabel(" Mean Sequence: ");
    meanSegLabel[1] = new JLabel("0");
    final JLabel medSeg1Label0 = new JLabel(" Median Sequence: ");
    medSegLabel[1] = new JLabel("0");
    final JLabel mostSeg1Label0 = new JLabel(" Most Sequence: ");
    mostSegLabel[1] = new JLabel("0");
    seg1Area.add(totalSeg1Label0, setGrid(0,0));
    seg1Area.add(totalSegLabel[1], setGrid(1,0));
    seg1Area.add(meanSeg1Label0, setGrid(0,1));
    seg1Area.add(meanSegLabel[1], setGrid(1,1));
    seg1Area.add(medSeg1Label0, setGrid(0,2));
    seg1Area.add(medSegLabel[1], setGrid(1,2));
    seg1Area.add(mostSeg1Label0, setGrid(0,3));
    seg1Area.add(mostSegLabel[1], setGrid(1,3));
    
    JPanel seg2Area = new JPanel(new GridBagLayout());
    seg2Area.setBorder(BorderFactory.createTitledBorder("Regular Segments"));
    final JLabel totalSeg2Label0 = new JLabel(" Total Regular: ");
    totalSegLabel[2] = new JLabel("0");
    final JLabel meanSeg2Label0 = new JLabel(" Mean Regular: ");
    meanSegLabel[2] = new JLabel("0");
    final JLabel medSeg2Label0 = new JLabel(" Median Regular: ");
    medSegLabel[2] = new JLabel("0");
    final JLabel mostSeg2Label0 = new JLabel(" Most Regular: ");
    mostSegLabel[2] = new JLabel("0");
    seg2Area.add(totalSeg2Label0, setGrid(0,0));
    seg2Area.add(totalSegLabel[2], setGrid(1,0));
    seg2Area.add(meanSeg2Label0, setGrid(0,1));
    seg2Area.add(meanSegLabel[2], setGrid(1,1));
    seg2Area.add(medSeg2Label0, setGrid(0,2));
    seg2Area.add(medSegLabel[2], setGrid(1,2));
    seg2Area.add(mostSeg2Label0, setGrid(0,3));
    seg2Area.add(mostSegLabel[2], setGrid(1,3));
    
    JPanel pendArea = new JPanel(new GridBagLayout());
    pendArea.setBorder(BorderFactory.createTitledBorder("Pending Segments"));
    final JLabel totalPendLabel0 = new JLabel(" Pending Segments: ");
    final JLabel totalPendLabel = new JLabel("0");
    final JLabel meanPendLabel0 = new JLabel(" Average Pending: ");
    final JLabel meanPendLabel = new JLabel("0");
    final JLabel medPendLabel0 = new JLabel(" Median Pending: ");
    final JLabel medPendLabel = new JLabel("0");
    final JLabel mostPendLabel0 = new JLabel(" Most Pending: ");
    final JLabel mostPendLabel = new JLabel("0");
    pendArea.add(totalPendLabel0, setGrid(0,0));
    pendArea.add(totalPendLabel, setGrid(1,0));
    pendArea.add(meanPendLabel0, setGrid(0,1));
    pendArea.add(meanPendLabel, setGrid(1,1));
    pendArea.add(medPendLabel0, setGrid(0,2));
    pendArea.add(medPendLabel, setGrid(1,2));
    pendArea.add(mostPendLabel0, setGrid(0,3));
    pendArea.add(mostPendLabel, setGrid(1,3));
    
    final JLabel[] totalSynLabel = new JLabel[3];
    final JLabel[] meanSynLabel = new JLabel[3];
    final JLabel[] medSynLabel = new JLabel[3];
    final JLabel[] mostSynLabel = new JLabel[3];
    
    JPanel synArea = new JPanel(new GridBagLayout());
    synArea.setBorder(BorderFactory.createTitledBorder("Synapses"));
    final JLabel totalSynLabel0 = new JLabel(" Total Synapses: ");
    totalSynLabel[0] = new JLabel("0");
    final JLabel meanSynLabel0 = new JLabel(" Mean Synapses: ");
    meanSynLabel[0] = new JLabel("0");
    final JLabel medSynLabel0 = new JLabel(" Median Synapses: ");
    medSynLabel[0] = new JLabel("0");
    final JLabel mostSynLabel0 = new JLabel(" Most Synapses: ");
    mostSynLabel[0] = new JLabel("0");
    synArea.add(totalSynLabel0, setGrid(0,0));
    synArea.add(totalSynLabel[0], setGrid(1,0));
    synArea.add(meanSynLabel0, setGrid(0,1));
    synArea.add(meanSynLabel[0], setGrid(1,1));
    synArea.add(medSynLabel0, setGrid(0,2));
    synArea.add(medSynLabel[0], setGrid(1,2));
    synArea.add(mostSynLabel0, setGrid(0,3));
    synArea.add(mostSynLabel[0], setGrid(1,3));
    
    JPanel syn1Area = new JPanel(new GridBagLayout());
    syn1Area.setBorder(BorderFactory.createTitledBorder("Sequence Synapses"));
    final JLabel totalSyn1Label0 = new JLabel(" Total SeqSyn: ");
    totalSynLabel[1] = new JLabel("0");
    final JLabel meanSyn1Label0 = new JLabel(" Mean SeqSyn: ");
    meanSynLabel[1] = new JLabel("0");
    final JLabel medSyn1Label0 = new JLabel(" Median SeqSyn: ");
    medSynLabel[1] = new JLabel("0");
    final JLabel mostSyn1Label0 = new JLabel(" Most SeqSyn: ");
    mostSynLabel[1] = new JLabel("0");
    syn1Area.add(totalSyn1Label0, setGrid(0,0));
    syn1Area.add(totalSynLabel[1], setGrid(1,0));
    syn1Area.add(meanSyn1Label0, setGrid(0,1));
    syn1Area.add(meanSynLabel[1], setGrid(1,1));
    syn1Area.add(medSyn1Label0, setGrid(0,2));
    syn1Area.add(medSynLabel[1], setGrid(1,2));
    syn1Area.add(mostSyn1Label0, setGrid(0,3));
    syn1Area.add(mostSynLabel[1], setGrid(1,3));
    
    JPanel syn2Area = new JPanel(new GridBagLayout());
    syn2Area.setBorder(BorderFactory.createTitledBorder("Regular Synapses"));
    final JLabel totalSyn2Label0 = new JLabel(" Total RegSyn: ");
    totalSynLabel[2] = new JLabel("0");
    final JLabel meanSyn2Label0 = new JLabel(" Mean RegSyn: ");
    meanSynLabel[2] = new JLabel("0");
    final JLabel medSyn2Label0 = new JLabel(" Median RegSyn: ");
    medSynLabel[2] = new JLabel("0");
    final JLabel mostSyn2Label0 = new JLabel(" Most RegSyn: ");
    mostSynLabel[2] = new JLabel("0");
    syn2Area.add(totalSyn2Label0, setGrid(0,0));
    syn2Area.add(totalSynLabel[2], setGrid(1,0));
    syn2Area.add(meanSyn2Label0, setGrid(0,1));
    syn2Area.add(meanSynLabel[2], setGrid(1,1));
    syn2Area.add(medSyn2Label0, setGrid(0,2));
    syn2Area.add(medSynLabel[2], setGrid(1,2));
    syn2Area.add(mostSyn2Label0, setGrid(0,3));
    syn2Area.add(mostSynLabel[2], setGrid(1,3));
    
    _statListener = new ChangeListener() {
      public void stateChanged(ChangeEvent e) {
        RegionStats stats = _region.getStats();
        
        activeAccLabel.setText(_nf.format(stats.activationAccuracy*100.0)+"%");
        predAccLabel.setText(_nf.format(stats.predicationAccuracy*100.0)+"%");
        
        for(int i=0; i<3; ++i) {
          totalSegLabel[i].setText(String.valueOf(stats.totalSegments[i]));
          meanSegLabel[i].setText(_nf.format(stats.meanSegments[i]));
          medSegLabel[i].setText(String.valueOf(stats.medianSegments[i]));
          mostSegLabel[i].setText(String.valueOf(stats.mostSegments[i]));
          
          totalSynLabel[i].setText(String.valueOf(stats.totalSynapses[i]));
          meanSynLabel[i].setText(_nf.format(stats.meanSynapses[i]));
          medSynLabel[i].setText(String.valueOf(stats.medianSynapses[i]));
          mostSynLabel[i].setText(String.valueOf(stats.mostSynapses[i]));
        }
        
        totalPendLabel.setText(String.valueOf(stats.pendingSegments));
        meanPendLabel.setText(_nf.format(stats.meanPending));
        medPendLabel.setText(String.valueOf(stats.medianPending));
        mostPendLabel.setText(String.valueOf(stats.mostPending));
      }
    };
    
    labelArea.add(accArea, setGrid(0,0, GridBagConstraints.BOTH));
    labelArea.add(segArea, setGrid(1,0, GridBagConstraints.BOTH));
    labelArea.add(seg1Area, setGrid(2,0, GridBagConstraints.BOTH));
    labelArea.add(seg2Area, setGrid(3,0, GridBagConstraints.BOTH));
    labelArea.add(pendArea, setGrid(4,0, GridBagConstraints.BOTH));
    labelArea.add(synArea, setGrid(5,0, GridBagConstraints.BOTH));
    labelArea.add(syn1Area, setGrid(6,0, GridBagConstraints.BOTH));
    labelArea.add(syn2Area, setGrid(7,0, GridBagConstraints.BOTH));
    super.add(labelArea, setGrid(0,0, GridBagConstraints.HORIZONTAL));
    
    _region = createRegion();
    try {
      _buffer = new BufferedReader(new FileReader(INPUT_FILE));
    }catch(FileNotFoundException e) {
      e.printStackTrace();
    }
    
    _regionPanel = new RegionPanel(_region);
    super.add(_regionPanel, setGrid(0,1, GridBagConstraints.BOTH));
    
    JFrame f = new JFrame("Region Visualizer");
    f.setDefaultCloseOperation(JFrame.EXIT_ON_CLOSE);
    f.setJMenuBar(createJMenuBar());
    f.add(this);
    f.pack();
    f.setVisible(true);
  }
  
  private Region createRegion() {
    _regionShape = new Dimension(25,25);
    int inputSizeX = _regionShape.width;
    int inputSizeY = _regionShape.height;
    int colGridSizeX = inputSizeX;
    int colGridSizeY = inputSizeY;
    float pctInputPerCol = 0.2f;
    float pctMinOverlap = 0.08f;
    int localityRadius = 0;
    float pctLocalActivity = 0.25f; 
    int cellsPerCol = 4; 
    int segActiveThreshold = 3;
    int newSynapseCount = 5;
    
    _inputData = new byte[inputSizeX*inputSizeY];
    
    Region.FULL_DEFAULT_SPATIAL_PERMANENCE = true;
    final Region region = new Region(inputSizeX, inputSizeY, 
        colGridSizeX, colGridSizeY,
        pctInputPerCol, pctMinOverlap, localityRadius,
        pctLocalActivity, cellsPerCol, segActiveThreshold,
        newSynapseCount, _inputData);
    region.setSpatialHardcoded(true);
    region.setSpatialLearning(false);
    region.setTemporalLearning(true);
    
    return region;
  }
  
  private Thread createThread() {
    return new Thread(new Runnable() {
      public void run() {
        //hide the region graphics while running as we don't want to wait
        //for repainting each time-step.  plus since we're on a non-UI thread
        //we would need to perform repaints on the UI-thread and thus also
        //wait for thread sync each time step
        _regionPanel.setVisible(false);
        try {
          int i=0;
          String word = readWordFromFile(_buffer);
          while(word!=null && !Thread.interrupted()) {
            //System.out.println("word: "+word);
            getWordRepresentation(word);
            
            //javax.swing.SwingUtilities.invokeAndWait(runRegion);
            _region.runOnce();
            if(i % 10 == 0)//update UI stats once every 10 runs for speed
              _statListener.stateChanged(new ChangeEvent(_region));
            ++i;
            
            word = readWordFromFile(_buffer);
          }
        } catch(IOException io) {
          io.printStackTrace();//fall through and terminate thread
        } finally {
          _regionPanel.setVisible(true);
          System.out.println("thread ended");
        }
      }
    });
  }
  
  private JMenuBar createJMenuBar() {
    JMenuBar mainMenuBar = new JMenuBar();
    JMenu menu1 = new JMenu("Run");
    mainMenuBar.add(menu1);
    
    // Creating the MenuItems
    JMenuItem stepItem = new JMenuItem("Forward 1 Step", KeyEvent.VK_F);
    stepItem.setAccelerator(KeyStroke.getKeyStroke(KeyEvent.VK_F,0));
    stepItem.addActionListener(new ActionListener() {
      public void actionPerformed(ActionEvent e) {
        try {
          String word = readWordFromFile(_buffer);
          if(word==null)
            return;
          System.out.println("word: "+word);
          getWordRepresentation(word);
          _region.runOnce();
          _statListener.stateChanged(new ChangeEvent(_region));
          _regionPanel.repaint();
        }catch(IOException e1) {
          JOptionPane.showMessageDialog(
              RegionFrame.this, "Failure to read the input file.");
        }
      }
    });
    menu1.add(stepItem);
    
    final JCheckBoxMenuItem playItem = new JCheckBoxMenuItem("Play");
    playItem.setMnemonic(KeyEvent.VK_P);
    playItem.setAccelerator(KeyStroke.getKeyStroke(KeyEvent.VK_P,0));
    playItem.addItemListener(new ItemListener() {
      public void itemStateChanged(ItemEvent e) {
        if(_thread==null || !_thread.isAlive()) {
          _thread = createThread();
          _thread.start();
          System.out.println("Thread running");
        }
        else {
          _thread.interrupt();
          _regionPanel.repaint();
        }
      }
    });
    menu1.add(playItem);
    
    return mainMenuBar;
  }
  
  private GridBagConstraints setGrid(int gridx, int gridy) {
    return setGrid(gridx,gridy, GridBagConstraints.NONE);
  }
  
  private GridBagConstraints setGrid(int gridx, int gridy, int fill) {
    return setGrid(gridx, gridy, fill, GridBagConstraints.WEST);
  }
  
  private GridBagConstraints setGrid(int gridx, int gridy, int fill, int anchor) {
    GridBagConstraints gb = new GridBagConstraints();
    gb.gridx = gridx;
    gb.gridy = gridy;
    gb.fill = fill;
    gb.anchor = anchor;
    return gb;
  }
  
  //  def getWordRepresentation(self, word):
  //    """ 
  //    Calculate a (NumColumns choose ActiveColumns) bit representation of
  //    the specified word string.
  //    """
  //    nx,ny = self._regionShape
  //    ncol = nx*ny #num columns in region 0
  //    nact = 40 #num active columns to represent any input
  //    random.seed(word*2)
  //    ibits = random.sample(xrange(0,ncol), nact)
  //    #Create ncol-bit number where indicies in list are 1-bits
  //    array = numpy.array(numpy.zeros((ncol)), dtype=numpy.uint8)
  //    if word!="": #blank word means all zero input to break sequence
  //      array[ibits] = 1
  //    array = array.reshape(self._regionShape)
  //    #print "Rep: ",array #[:,0]
  //    return array
  /**
   * Calculate a (NumColumns choose ActiveColumns) bit representation of
   * the specified word string.
   */
  private void getWordRepresentation(String word) {
    int nx = _regionShape.width;
    int ny = _regionShape.height;
    int ncol = nx*ny;
    int nact = 40; //num active columns to represent any input
    _rand.setSeed(word.hashCode()*2);
    
    Arrays.fill(_inputData, (byte)0);
    if(word.equals(""))
      return; //blank word means all zero input to break sequence
    
    //choose nact random column indicies to represent word
    int r=0;
    while(r < nact) {
      int i = _rand.nextInt(ncol);
      if(_inputData[i]==0) {
        _inputData[i] = 1;
        r++;
      }
    }
  }
  
    /*def readWordFromFile(self):
      """ Read the next word from the last read line in the file. """
      if self._isWordBreak:
        self._isWordBreak = False
        return ""
      
      while self._fileLine==None or len(self._fileLine)==0:
        line = self._file.readline()
        if line=="":
          self._fileLine = None
          return None
        self._fileLine = line.split() #split on whitespace
        
      #parse line by popping next word and stripping punctuation
      wordf = self._fileLine.pop(0).lower()
      self._isWordBreak = wordf.endswith(PUNC)
      return wordf.translate(None, string.punctuation)
   */
  private String readWordFromFile(BufferedReader file) throws IOException {
    if(_isWordBreak) {
      _isWordBreak = false;
      return "";
    }
    
    while(_lastLine==null || _lastLine.size()==0) {
      String line = file.readLine();
      if(line==null) {
        _lastLine = null;
        return null;
      }
      String[] lineSplit = line.split("\\s+");
      _lastLine = new ArrayDeque<String>(lineSplit.length);
      for(int i=0; i<lineSplit.length; ++i)
        _lastLine.push(lineSplit[i]);
    }
    
    //parse line by popping next word and stripping punctuation
    String wordf = _lastLine.removeLast();
    
    _isWordBreak = false;
    for(int i=0; i<PUNC.length; ++i) {
      if(wordf.endsWith(PUNC[i])) {
        _isWordBreak = true;
        break;
      }
    }
    
    //remove all punctuation characters from the word
    StringBuilder sb = new StringBuilder();
    for(int c=0; c<wordf.length(); ++c) {
      char ch = wordf.charAt(c);
      boolean ok = true;
      for(int i=0; i<punctuation.length(); ++i) {
        if(ch==punctuation.charAt(i)) {
          ok = false;
          break;
        }
      }
      if(ok)
        sb.append(ch);
    }
    
    return sb.toString();
  }

}
