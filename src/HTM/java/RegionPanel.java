import htm.Cell;
import htm.Column;
import htm.Region;

import java.awt.Color;
import java.awt.Dimension;
import java.awt.Graphics;
import java.awt.Point;

import javax.swing.BorderFactory;
import javax.swing.JPanel;

/**
 * The RegionPanel is a JPanel that renders a visualization of an HTM Region.
 */
public class RegionPanel extends JPanel {
  
  private static final long serialVersionUID = 1L;
  
  private Region _region;
  private int _colRadius;
  private boolean _reInitBuffer;
  private boolean _showInput = true;
  private boolean _showInactive = true;
  private Point _mousePos = null;
  private int[][] _data = null;
  
  private static final int COLUMN_BORDER = 3;
  private static final double SQRT2 = Math.sqrt(2.0);
  
  /**
   * Construct a new RegionPanel that is to visualize the given Region.
   * @param region the Region to visualize.
   */
  public RegionPanel(Region region) {
    super();
    setBorder(BorderFactory.createLineBorder(Color.black));
    _region = region;
    _reInitBuffer = true;
  }
  
  /**
   * Initialize the bitmap used for buffering the display.
   */
  private void initBuffer() {
    Dimension size = super.getSize();
    //compute circle radius for drawing region columns:
    int numXs = _region.getWidth();
    int numYs = _region.getHeight();
    
    int bordersWidth = COLUMN_BORDER * (numXs+1);
    int bordersHeight = COLUMN_BORDER * (numYs+1);
    int maxRadWidth = (size.width - bordersWidth) / numXs;
    int maxRadHeight = (size.height - bordersHeight) / numYs;
    _colRadius = Math.min(maxRadWidth, maxRadHeight) / 2;
    
    //Now create new bitmap same size as the window
    _reInitBuffer = false;
  }

  @Override
  public Dimension getPreferredSize() {
    double ratio = _region.getWidth()*1.0 / _region.getHeight()*1.0;
    int maxWidth = Math.min(1000, 60*_region.getWidth()); //max 60pixels per col
    return new Dimension(maxWidth, Math.max(150, (int)(maxWidth/ratio)));
  }

  @Override
  public void paintComponent(Graphics g) {
    super.paintComponent(g);

    if(_reInitBuffer)
      initBuffer();
    
    // First draw circles for columns same dimensions as region's col grid
    // Thick blue circles for active column, thin black for inactive
    // Fill circles with gray-scale of last input overlap %
    int rad = _colRadius;
    int rad2 = rad/2;
    int diam = rad*2;
    int rad2sqrt = (int)(rad2*1.0/SQRT2);
    
    Dimension size = super.getSize();
    g.setColor(Color.WHITE);
    g.fillRect(0, 0, size.width, size.height);
    
    for(int cx=0; cx<_region.getWidth(); ++cx) {
      for(int cy=0; cy<_region.getHeight(); ++cy) {
        Column col = _region.getColumn(cx, cy);
        Point circle = getColumnPos(col);
        
        int gray = 255 - Math.round(col.getOverlapPercentage()*255.0f);
        if(gray<255)
          gray = gray;
        g.setColor(new Color(gray,gray,gray));
        g.fillOval(circle.x-rad, circle.y-rad, diam, diam);
        
        boolean wasDrawn = false;
        if(col.isActive()) {
          wasDrawn = true;
          g.setColor(Color.BLUE);
        }
        else
          g.setColor(new Color(192,192,192));
        
        g.drawOval(circle.x-rad, circle.y-rad, diam, diam);
        
        //Now draw individual column cells inside the column's circle
        int radCell = rad2sqrt+1;
        int rad2C = rad2-1;
        if(_region.getCellsPerCol()==1) {
          radCell = rad-(rad/3);
          rad2C = 0;
        }
        
        Point[] clocs = new Point[] { 
          new Point(circle.x-rad2C, circle.y-rad2C), 
          new Point(circle.x+rad2C, circle.y-rad2C),
          new Point(circle.x-rad2C, circle.y+rad2C), 
          new Point(circle.x+rad2C, circle.y+rad2C) 
        };
        
        for(int i=0; i<col.numCells(); ++i)
          wasDrawn |= drawCell(g, clocs[i], radCell, col.getCell(i));
        
        //Draw small black circle to indicate input bit origin locations
        if(_showInput && _data!=null && _data[col.ix()][col.iy()]==1) {
          wasDrawn = true;
          int r = Math.max(2, rad/6);
          g.setColor(new Color(128,0,128));
          g.fillOval(circle.x-r, circle.y-r, r*2, r*2);
          g.setColor(Color.BLACK);
          g.drawOval(circle.x-r, circle.y-r, r*2, r*2);
        }
        
        //if column had no activity at all, hide it completely
        if(!_showInactive && !wasDrawn) {
          g.setColor(Color.WHITE);
          g.fillRect(circle.x-rad, circle.y-rad, diam+1,diam+1);
        }
      }
    }
    
    //determine if a cell was clicked, if so draw its recentUpdateInfo
  }
    
//    def draw(self, dc=None):
//      """ Draw the entire current state of the Region to the canvas. """
//        
//      #determine if a cell was clicked, if so draw its recentUpdateInfo
//      mouseCell = self.getMouseCell()
//      if mouseCell and mouseCell in self.region.recentUpdateMap:
//        segInfoList = self.region.recentUpdateMap[mouseCell]
//        for segInfo in segInfoList:
//          #draw red borders for new synapse-cells, purple for existing active
//          dc.SetPen(wx.Pen('BLACK', 1))
//          dc.SetBrush(wx.Brush('RED'))
//          for syn in segInfo.activeSynapses:
//            center = self.getCellPos(syn.inputSource)
//            dc.DrawCircle(center[0], center[1], radCell)
//            
//          dc.SetBrush(wx.Brush('PURPLE'))
//          for syn in segInfo.addedSynapses:
//            center = self.getCellPos(syn.inputSource)
//            dc.DrawCircle(center[0], center[1], radCell)
//      
//      dc.EndDrawing()
//    
  
  /**
   * Get the pixel-position of the center of the column's circle.
   */
  private Point getColumnPos(Column col) {
    int b = COLUMN_BORDER;
    int rad = _colRadius;
    int d = rad*2;
    int x = col.cx();
    int y = col.cy();
    return new Point((b*(x+1))+(d*x)+rad, (b*(y+1)) +(d*y)+rad);
  }
  
  /**
   * Get the pixel-position of the center of the cell's circle.
   */
  private Point getCellPos(Cell cell) {
    int rad = _colRadius;
    int rad2 = rad/2;
    Point circle = getColumnPos(cell.getColumn());
    int xr = rad2;
    int yr = rad2;
    int cellIndex = cell.getIndex();
    if(cellIndex==0 || cellIndex==2)
      xr = -rad2;
    if(cellIndex==0 || cellIndex==1)
      yr = -rad2;
    if(_region.getCellsPerCol()==1) { //special case for 1-cell
      xr = 0;
      yr = 0;
    }
    return new Point(circle.x+xr, circle.y+yr);
  }
  
  /**
   * Return the last column cell the mouse clicked on, or None if the last
   * mouse click was not on a valid Cell position. 
   */
  private Cell getMouseCell() {
    if(_mousePos!=null) {
      int rad2sqrt = (int)(((double)(_colRadius/2)) / SQRT2);
      
      int w = _colRadius*2 + COLUMN_BORDER;
      int x = _mousePos.x / w;
      int y = _mousePos.y / w;
      Column col = null;
      try { //if mouse clicked outside entire grid, return null
        col = _region.getColumn(x, y);
      }catch(ArrayIndexOutOfBoundsException ex) {
        return null;
      }
      
      if(col.numCells()==1) //special case for 1-cell
        rad2sqrt = _colRadius-(_colRadius/3);
      
      for(int i=0; i<col.numCells(); ++i) {
        Cell cell = col.getCell(i);
        Point center = getCellPos(cell);
        if(_mousePos.x > center.x-rad2sqrt && _mousePos.y > center.y-rad2sqrt) {
          if(_mousePos.x < center.x+rad2sqrt && _mousePos.y < center.y+rad2sqrt)
            return cell;
        }
      }
    }
    return null;
  }
  
  /**
   * Draw an individual column cell with the center of the cell's
   * circle at the pixel location specified by 'center'. 
   * @param dc: The wx DC the paint with.
   * @param center: the pixel location of the center of the cell's circle.
   * @param rad: the pixel radius of the cell's circle.
   * @param cell: the HTM Cell to draw.
   */
  private boolean drawCell(Graphics g, Point center, int rad, Cell cell) {
    int cx = center.x;
    int cy = center.y;
    boolean wasDrawn = false;
    
    //Filled green circles for predicting cells (yellow for non-sequence)
    if(cell.isPredicting()) {
      wasDrawn = true;
      if(cell.hasActiveSequenceSegment())
        g.setColor(Color.GREEN);
      else
        g.setColor(Color.YELLOW);
      g.fillOval(cx-rad, cy-rad, rad*2, rad*2);
    }
    
    //Thick blue circles for active cells, otherwise thin black
    Color penColor = Color.WHITE;
    if(cell.isActive()) {
      wasDrawn = true;
      penColor = Color.BLUE;
    }
    else
      penColor = new Color(192,192,192);
    
    g.setColor(penColor);
    g.drawOval(cx-rad, cy-rad, rad*2, rad*2);
    
    //Vertical line inside circle for learning cells
    if(cell.isLearning()) {
      wasDrawn = true;
      g.setColor(Color.RED);
      g.drawLine(cx, cy-rad, cx, cy+rad);
      g.drawLine(cx-rad, cy, cx+rad, cy);
    }
    
    //Check recentUpdateList and mark cells that had segments updated
    //  if cell in self.region.recentUpdateMap:
    //  #segInfo = self.region.recentUpdateMap[cell]
    //  wasDrawn = True
    //  dc.SetPen(wx.Pen('BLACK', 1))
    //  dc.DrawLine(center[0], center[1]-radius, center[0], center[1]+radius)
    
    return wasDrawn;
  }

}
