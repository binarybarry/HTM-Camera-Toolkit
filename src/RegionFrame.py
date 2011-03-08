"""
Created on Jan 22, 2011

@author: Barry Maturkanich

This file contains UI code to render a visualization of the state of
an HTM Region after its most recently completed time step.

The Visualization for a Region will display all Columns in their respective
Grid positions as well as the states of all columns and cells.

From the User Tutorial Text:

The big circles are Columns, arranged as a grid in the same manner
as the Region.

Active columns are drawn with a blue outline.  The gray-scale
background of a column represents how many of its input synapses
were active ranging from black=100% to white=0%.

The smaller circle(s) inside the Columns are the cell(s) for each
Column.

Active cells are drawn with a blue outline.

Predicted cells are green if predicted by a sequence segment,
or yellow if predicted by a non-sequence segment.

Learning cells are marked with red line(s) on top.

Cells which had segments updated this time step are marked
with a vertical black line.

You may click on any cell that had updates and you will see
some cells color red or purple.  The red cells indicate existing
synapse connections that were either increased or decreased, and
purple cells indicate a new (or first time updated) synapse
connection.

The Input Origins option shows roughly where input bits were active
in the original input data matrix.
"""

import wx
from HTM.Region import Region

SQRT2 = 1.414213562373095

class RegionFrame(wx.Frame):
  """
  wxPython Frame to visualize the state of an existing CLA Region.
  The RegionFrame contains within it a RegionCanvas which is the actual
  control that does the visualizing of the Region states.
  """

  def __init__(self, region, parent=None):
    """ Build a RegionFrame with the specified Region to visualize. """
    super(RegionFrame, self).__init__(parent, title="Region Visualizer",
          style=wx.DEFAULT_FRAME_STYLE|wx.NO_FULL_REPAINT_ON_RESIZE)
    
    self.regionCanvas = RegionCanvas(self, region)

    menubar = wx.MenuBar()
    
    options = wx.Menu()
    self.miShowInput = wx.MenuItem(options, 1, 'Show Input Origins', \
                                      'Paint Input Origins', wx.ITEM_CHECK)
    self.miShowInactive = wx.MenuItem(options, 2, 'Show Inactive Columns', \
                                      'Paint Inactive Columns', wx.ITEM_CHECK)
    options.AppendItem(self.miShowInput)
    options.AppendItem(self.miShowInactive)
    self.Bind(wx.EVT_MENU, self.onShowInput, id=1)
    self.Bind(wx.EVT_MENU, self.onShowInactive, id=2)
    
    help = wx.Menu()
    help.Append(wx.ID_HELP, 'Tutorial Text', 'Show Tutorial Text')
    self.Bind(wx.EVT_MENU, self.onHelp, id=wx.ID_HELP)
    
    menubar.Append(options, "&Options")
    menubar.Append(help, "&Help")
    self.SetMenuBar(menubar)
    
    ratio = region.width*1.0 / region.height
    maxWidth = min(1000, 60*region.width) #max 60pixels per column
    self.SetSize((maxWidth,int(maxWidth/ratio)))
  
  def onHelp(self, evt=None):
    """ Top-level menu tutorial text help command was activated. """
    text = "This window visualizes the current state of an HTM Region.\n\n" + \
           "The big circles are Columns, arranged as a grid in the same manner " + \
           "as the Region.\n\n" + \
           "Active columns are drawn with a blue outline.  The gray-scale " + \
           "background of a column represents how many of its input synapses " + \
           "were active ranging from black=100% to white=0%.\n\n" + \
           "The smaller circle(s) inside the Columns are the cell(s) for each " + \
           "Column.\n\n" + \
           "Active cells are drawn with a blue outline.\n\n" + \
           "Predicted cells are green if predicted by a sequence segment, " + \
           "or yellow if predicted by a non-sequence segment.\n\n" + \
           "Learning cells are marked with red line(s) on top.\n\n" + \
           "Cells which had segments updated this time step are marked " + \
           "with a vertical black line.\n\n" + \
           "You may click on any cell that had updates and you will see " + \
           "some cells color red or purple.  The red cells indicate existing " + \
           "synapse connections that were either increased or decreased, and " + \
           "purple cells indicate a new (or first time updated) synapse " + \
           "connection.\n\n" + \
           "The Input Origins option shows roughly where input bits were active " + \
           "in the original input data matrix."
    msg = wx.MessageDialog(self, text, "Region Visualizer Tutorial", \
                           wx.OK | wx.ICON_INFORMATION)
    msg.ShowModal()
  
  def onShowInactive(self, evt=None):
    """ Called when menu option for show inactive columns is activated. """
    self.regionCanvas.showInactive = self.miShowInactive.IsChecked()
    self.regionCanvas.draw()
    
  def onShowInput(self, evt=None):
    """ Called when menu option for show inactive columns is activated. """
    self.regionCanvas.showInput = self.miShowInput.IsChecked()
    self.regionCanvas.draw()
  
  def draw(self):
    """ Draw the current Region state in the canvas. """
    self.regionCanvas.syncInputData(self.regionCanvas.region.inputData)
    self.regionCanvas.draw()

class SimpleRegionFrame(wx.Frame):
  """
  wxPython Frame to visualize the state of a CLA Region.  This simple version
  of RegionFrame is stand-alone and will create a test Region with a very small
  default data set to experiment with.
  """

  def __init__(self, parent=None):
    super(SimpleRegionFrame, self).__init__(parent, title="Region Visualizer",
          size=(700,755), 
          style=wx.DEFAULT_FRAME_STYLE|wx.NO_FULL_REPAINT_ON_RESIZE)
    regionWin = RegionTestWindow(self)
    

class RegionTestWindow(wx.Panel):
  """
  wxPython Panel for user to control and visualize a Simple Test CLA Region.
  """
  
  def __init__(self, parent):
    super(RegionTestWindow, self).__init__(parent)
    
    self.createRegion()
    
    #add buttons on top control bar
    self.hSizer = wx.BoxSizer(wx.HORIZONTAL)
    
    self.runButton = wx.Button(self, -1, "Run 1 Time Step")
    self.runButton.Bind(wx.EVT_BUTTON, self.runRegionOnce)
    self.hSizer.Add(self.runButton, 1, wx.EXPAND|wx.ALL, border=5 )
    
    self.run10Button = wx.Button(self, -1, "Run 10 Time Steps")
    self.run10Button.Bind(wx.EVT_BUTTON, self.runRegionTen)
    self.hSizer.Add(self.run10Button, 1, wx.EXPAND|wx.ALL, border=5 )
    
    #add RegionCanvas where state will be painted
    self.canvas = RegionCanvas(self, self.region)
    
    # Use some sizers to see layout options
    self.vSizer = wx.BoxSizer(wx.VERTICAL)
    self.vSizer.Add(self.hSizer, 0, wx.ALIGN_RIGHT)
    self.vSizer.Add(self.canvas, 1, wx.EXPAND)

    #Layout sizers
    self.SetSizer(self.vSizer)
    self.SetAutoLayout(1)
    self.vSizer.Fit(self)
  
  def getData1(self):
    datas = []
    datas.append([
      [1,0,0,0,0,0,0,0,0],
      [0,1,0,0,0,0,0,0,0],
      [0,0,1,0,0,0,0,0,0],
      [0,0,0,1,0,0,0,0,0],
      [0,0,0,0,1,0,0,0,0],
      [0,0,0,0,0,0,0,0,0],
#      [0,0,0,0,0,0,0,0,0],
#      [0,0,0,0,0,0,0,0,0],
#      [0,0,0,0,0,0,0,0,0],
      ])
    datas.append([
      [0,0,0,0,0,0,0,0,1],
      [0,0,0,0,0,0,0,1,0],
      [0,0,0,0,0,0,1,0,0],
      [0,0,0,0,0,1,0,0,0],
      [0,0,0,0,1,0,0,0,0],
      [0,0,0,0,0,0,0,0,0],
#      [0,0,0,0,0,0,0,0,0],
#      [0,0,0,0,0,0,0,0,0],
#      [0,0,0,0,0,0,0,0,0],
      ])
    datas.append([
      [0,0,0,0,0,0,0,0,0],
      [0,0,0,0,0,0,0,0,0],
      [0,0,0,0,0,0,0,0,0],
      [0,0,0,0,0,0,0,0,0],
      [0,0,0,0,1,0,0,0,0],
      [0,0,0,0,0,1,0,0,0],
#      [0,0,0,0,0,0,1,0,0],
#      [0,0,0,0,0,0,0,1,0],
#      [0,0,0,0,0,0,0,0,1],
      ])
    datas.append([
      [0,0,0,0,0,0,0,0,0],
      [0,0,0,0,0,0,0,0,0],
      [0,0,0,0,0,0,0,0,0],
      [0,0,0,0,0,0,0,0,0],
      [0,0,0,0,1,0,0,0,0],
      [0,0,0,1,0,0,0,0,0],
#      [0,0,1,0,0,0,0,0,0],
#      [0,1,0,0,0,0,0,0,0],
#      [1,0,0,0,0,0,0,0,0],
      ])
    return datas
  
  def getData2(self):
    datas = []
    datas.append([
      [1,0,0,0,0,0,0,0,0],
      [0,1,0,0,0,0,0,0,0],
      [0,0,1,0,0,0,0,0,0],
      [0,0,0,1,0,0,0,0,0],
      [0,0,0,0,1,0,0,0,0],
      [0,0,0,0,0,0,0,0,0],
      [0,0,0,0,0,0,0,0,0],
      [0,0,0,0,0,0,0,0,0],
      [0,0,0,0,0,0,0,0,0],
      ])
    datas.append([
      [0,0,0,0,0,0,0,0,0],
      [0,0,0,0,0,0,0,0,0],
      [0,0,0,0,0,0,0,0,0],
      [0,0,0,0,0,0,0,0,0],
      [0,0,0,0,1,0,0,0,0],
      [0,0,0,1,0,0,0,0,0],
      [0,0,1,0,0,0,0,0,0],
      [0,1,0,0,0,0,0,0,0],
      [1,0,0,0,0,0,0,0,0],
      ])
    datas.append([
      [0,0,0,0,0,0,0,0,0],
      [0,0,0,0,0,0,0,0,0],
      [0,0,0,0,0,0,0,0,0],
      [0,0,0,0,0,0,0,0,0],
      [0,0,0,0,1,0,0,0,0],
      [0,0,0,0,0,1,0,0,0],
      [0,0,0,0,0,0,1,0,0],
      [0,0,0,0,0,0,0,1,0],
      [0,0,0,0,0,0,0,0,1],
      ])
    datas.append([
      [0,0,0,0,0,0,0,0,1],
      [0,0,0,0,0,0,0,1,0],
      [0,0,0,0,0,0,1,0,0],
      [0,0,0,0,0,1,0,0,0],
      [0,0,0,0,1,0,0,0,0],
      [0,0,0,0,0,0,0,0,0],
      [0,0,0,0,0,0,0,0,0],
      [0,0,0,0,0,0,0,0,0],
      [0,0,0,0,0,0,0,0,0],
      ])
    return datas
  
  def getData3(self):
    """ doc """
    datas = []
    datas.append([
      [0,0,0,0,1,0,0,0,0],
      [0,0,0,0,1,0,0,0,0],
      [0,0,0,0,1,0,0,0,0],
      [0,0,0,0,1,0,0,0,0],
      [0,0,0,0,1,0,0,0,0],
      [0,0,0,0,0,0,0,0,0],
      [0,0,0,0,0,0,0,0,0],
      [0,0,0,0,0,0,0,0,0],
      [0,0,0,0,0,0,0,0,0],
      ])
    datas.append([
      [0,0,0,0,0,0,0,0,0],
      [0,0,0,0,0,0,0,0,0],
      [0,0,0,0,0,0,0,0,0],
      [0,0,0,0,0,0,0,0,0],
      [0,0,0,0,1,1,1,1,1],
      [0,0,0,0,0,0,0,0,0],
      [0,0,0,0,0,0,0,0,0],
      [0,0,0,0,0,0,0,0,0],
      [0,0,0,0,0,0,0,0,0],
      ])
    datas.append([
      [0,0,0,0,0,0,0,0,0],
      [0,0,0,0,0,0,0,0,0],
      [0,0,0,0,0,0,0,0,0],
      [0,0,0,0,0,0,0,0,0],
      [0,0,0,0,1,0,0,0,0],
      [0,0,0,0,1,0,0,0,0],
      [0,0,0,0,1,0,0,0,0],
      [0,0,0,0,1,0,0,0,0],
      [0,0,0,0,1,0,0,0,0],
      ])
    datas.append([
      [0,0,0,0,0,0,0,0,0],
      [0,0,0,0,0,0,0,0,0],
      [0,0,0,0,0,0,0,0,0],
      [0,0,0,0,0,0,0,0,0],
      [1,1,1,1,1,0,0,0,0],
      [0,0,0,0,0,0,0,0,0],
      [0,0,0,0,0,0,0,0,0],
      [0,0,0,0,0,0,0,0,0],
      [0,0,0,0,0,0,0,0,0],
      ])
    return datas
  
  def getData4(self):
    """ doc """
    datas = []
    datas.append([
      [0,0,0,0,1,0,0,0,0],
      [0,0,0,0,1,0,0,0,0],
      [0,0,0,0,1,0,0,0,0],
      [0,0,0,0,1,0,0,0,0],
      [0,0,0,0,1,0,0,0,0],
      [0,0,0,0,0,0,0,0,0],
      [0,0,0,0,0,0,0,0,0],
      [0,0,0,0,0,0,0,0,0],
      [0,0,0,0,0,0,0,0,0],
      ])
    datas.append([
      [0,0,0,0,0,0,0,0,0],
      [0,0,0,0,0,0,0,0,0],
      [0,0,0,0,0,0,0,0,0],
      [0,0,0,0,0,0,0,0,0],
      [1,1,1,1,1,0,0,0,0],
      [0,0,0,0,0,0,0,0,0],
      [0,0,0,0,0,0,0,0,0],
      [0,0,0,0,0,0,0,0,0],
      [0,0,0,0,0,0,0,0,0],
      ])
    datas.append([
      [0,0,0,0,0,0,0,0,0],
      [0,0,0,0,0,0,0,0,0],
      [0,0,0,0,0,0,0,0,0],
      [0,0,0,0,0,0,0,0,0],
      [0,0,0,0,1,0,0,0,0],
      [0,0,0,0,1,0,0,0,0],
      [0,0,0,0,1,0,0,0,0],
      [0,0,0,0,1,0,0,0,0],
      [0,0,0,0,1,0,0,0,0],
      ])
    datas.append([
      [0,0,0,0,0,0,0,0,0],
      [0,0,0,0,0,0,0,0,0],
      [0,0,0,0,0,0,0,0,0],
      [0,0,0,0,0,0,0,0,0],
      [0,0,0,0,1,1,1,1,1],
      [0,0,0,0,0,0,0,0,0],
      [0,0,0,0,0,0,0,0,0],
      [0,0,0,0,0,0,0,0,0],
      [0,0,0,0,0,0,0,0,0],
      ])
    return datas
  
  def createRegion(self):
    """ Create the CLA Region and some default simple data. """
    self.datas = []
    self.datas.append(self.getData1())
#    self.datas.append(self.getData2())
#    self.datas.append(self.getData3())
#    self.datas.append(self.getData4())

    imgs = []
#    imgs.append(Image.open("C:/apps/numenta/cla/bitmaps/A.bmp"))
#    imgs.append(Image.open("C:/apps/numenta/cla/bitmaps/B.bmp"))
#    imgs.append(Image.open("C:/apps/numenta/cla/bitmaps/C.bmp"))
#    imgs.append(Image.open("C:/apps/numenta/cla/bitmaps/D.bmp"))
#    imgs.append(Image.open("C:/apps/numenta/cla/bitmaps/E.bmp"))
#    imgs.append(Image.open("C:/apps/numenta/cla/bitmaps/F.bmp"))
#    imgs.append(Image.open("C:/apps/numenta/cla/bitmaps/G.bmp"))
    
    datas = []
    for img in imgs:
      pix = img.load()
      imgData = []
      for r in xrange(img.size[0]):
        row = []
        for c in xrange(img.size[1]):
          p = pix[c,r]
          if p==0:
            p = 1
          elif p==255:
            p = 0
          row.append(p)
        imgData.append(row)
      datas.append(imgData)
    self.datas.append(datas)
    
    self.dNum = 0
    self.data = list(self.datas[0][0])
    self.time = 0
    self.region = Region(self.data)
  
  def runRegionOnce(self, event):
    self.runRegion()
  
  def runRegionTen(self, event):
    self.runRegion(timeSteps=10)
  
  def runRegion(self, timeSteps=1):
    """ Run the Region for the specified number of time steps. """
    for t in xrange(timeSteps):
      self.region.runOnce()
      #draw state of Region after run completes
      self.canvas.syncInputData(self.data)
      self.canvas.draw()
      
      #now update the data to its next frame
      self.time += 1
#      if self.time % len(self.datas[self.dNum]) == 0:
#        self.dNum = random.randint(0,len(self.datas)-1)
#      dN = self.dNum
      dN = 0
      newData = list(self.datas[dN][self.time % len(self.datas[dN])])
      for i in xrange(len(self.data)):
        self.data[i] = list(newData[i])
  
  def shiftRowsVertically(self):
    """ Shift all data rows down in a rotating manner. """
    firstRow = self.data[0]
    for i in xrange(len(self.data)-1):
      self.data[i] = self.data[i+1]
    self.data[-1] = firstRow
    

class RegionCanvas(wx.Window):
  """
  wxPython Window to visualize the current state of a CLA Region.
  """
  
  def __init__(self, parent, region):
    super(RegionCanvas, self).__init__(parent, style=wx.NO_FULL_REPAINT_ON_RESIZE)
    self.SetBackgroundColour('WHITE')
    self.Bind(wx.EVT_SIZE, self.onSize)
    self.Bind(wx.EVT_IDLE, self.onIdle)
    self.Bind(wx.EVT_PAINT, self.onPaint)
    self.Bind(wx.EVT_LEFT_DOWN, self.onMouseLeftDown)
    
    self.COLUMN_BORDER = 1
    self.data = None
    self.mousePos = None
    
    self.showInput = False
    self.showInactive = False
    
    self.region = region
    self.initBuffer()
    
  def initBuffer(self):
    """ Initialize the bitmap used for buffering the display. """
    size = self.GetClientSize()
    #compute circle radius for drawing region columns:
    numXs = len(self.region.columnGrid)
    numYs = len(self.region.columnGrid[0])
    
    bordersWidth = (self.COLUMN_BORDER * (numXs+1))
    bordersHeight= (self.COLUMN_BORDER * (numYs+1))
    maxRadWidth = (size.width - bordersWidth) / numXs
    maxRadHeight = (size.height - bordersHeight) / numYs
    self.colRadius = min(maxRadWidth, maxRadHeight) / 2
    
    #Now create new bitmap same size as the window
    self.reInitBuffer = False
    self.buffer = wx.EmptyBitmap(size.width, size.height)
    dc = wx.BufferedDC(None, self.buffer)
    dc.SetBackground(wx.Brush(self.GetBackgroundColour()))
    dc.Clear()
    self.draw(dc)
  
  def onMouseLeftDown(self, event):
    """ Called when left mouse button clicked somewhere in the Canvas """
    self.mousePos = event.GetPositionTuple()
    self.draw()
  
  def onSize(self, event):
    """ Called when the window is resized. We set a flag so the idle
        handler will resize the buffer. """
    self.reInitBuffer = True

  def onIdle(self, event):
    """ If the size was changed then resize the bitmap used for double
        buffering to match the window size.  We do it in Idle time so
        there is only one refresh after resizing is done, not lots while
        it is happening. """
    if self.reInitBuffer:
      self.initBuffer()
      self.Refresh(False)
  
  def onPaint(self, event):
    """ Called on window paint event. We will blit using our own 
    buffer separately. """
    dc = wx.BufferedPaintDC(self, self.buffer)
    
  def draw(self, dc=None):
    """ Draw the entire current state of the Region to the canvas. """
    if not dc:
      dc = wx.BufferedDC(wx.ClientDC(self), self.buffer)
    
    #First draw circles for columns same dimensions as region's col grid
    #Thick blue circles for active column, thin black for inactive
    #Fill circles with gray-scale of last input overlap %
    rad = self.colRadius
    rad2 = rad/2
    rad2sqrt = rad2/SQRT2
    
    dc.BeginDrawing()
    dc.SetBrush(wx.Brush('WHITE'))
    dc.Clear()
    
    for col in self.region.columns:
      wasDrawn = False
      if col.isActive:
        wasDrawn = True
        dc.SetPen(wx.Pen('BLUE', 1))
      else:
        dc.SetPen(wx.Pen((192,192,192), 1))
      gray = 255 - round(col.getOverlapPercentage() * 255)
      dc.SetBrush(wx.Brush((gray,gray,gray)))
      
      circle = self.getColumnPos(col)
      dc.DrawCircle(circle[0], circle[1], rad)
      
      #Now draw individual column cells inside the column's circle
      radCell = rad2sqrt+1
      rad2C = rad2-1
      if len(col.cells)==1:
        radCell = rad-(rad/3)
        rad2C = 0
      
      clocs = ((circle[0]-rad2C, circle[1]-rad2C), (circle[0]+rad2C, circle[1]-rad2C), \
               (circle[0]-rad2C, circle[1]+rad2C), (circle[0]+rad2C, circle[1]+rad2C))  
      for i in xrange(len(col.cells)):
        wasDrawn |= self.drawCell(dc, clocs[i], radCell, col.cells[i])
      
      #Draw small black circle to indicate input bit origin locations
      if self.showInput and self.data!=None and self.data[col.ix][col.iy]==1:
        wasDrawn = True
        dc.SetPen(wx.Pen('BLACK', 1))
        dc.SetBrush(wx.Brush((128,0,128)))
        dc.DrawCircle(circle[0], circle[1], max(2, rad/6))
      
      #if column had no activity at all, hide it completely
      if not self.showInactive and not wasDrawn:
        dc.SetBrush(wx.Brush('WHITE'))
        dc.SetPen(wx.Pen('WHITE', 1))
        dc.DrawRectangle(circle[0]-rad, circle[1]-rad, rad*2,rad*2)
      
    #determine if a cell was clicked, if so draw its recentUpdateInfo
    mouseCell = self.getMouseCell()
    if mouseCell and mouseCell in self.region.recentUpdateMap:
      segInfoList = self.region.recentUpdateMap[mouseCell]
      for segInfo in segInfoList:
        #draw red borders for new synapse-cells, purple for existing active
        dc.SetPen(wx.Pen('BLACK', 1))
        dc.SetBrush(wx.Brush('RED'))
        for syn in segInfo.activeSynapses:
          center = self.getCellPos(syn.inputSource)
          dc.DrawCircle(center[0], center[1], radCell)
          
        dc.SetBrush(wx.Brush('PURPLE'))
        for syn in segInfo.addedSynapses:
          center = self.getCellPos(syn.inputSource)
          dc.DrawCircle(center[0], center[1], radCell)
    
    dc.EndDrawing()
  
  def getColumnPos(self, col):
    """ Get the pixel-position of the center of the column's circle. """
    b = self.COLUMN_BORDER
    rad = self.colRadius
    d = rad*2
    x = col.cx
    y = col.cy
    return ((b*(x+1))+(d*x)+rad, (b*(y+1))+(d*y)+rad)
  
  def getCellPos(self, cell):
    """ Get the pixel-position of the center of the cell's circle. """
    rad = self.colRadius
    rad2 = rad/2
    circle = self.getColumnPos(cell.column)
    xr = rad2
    yr = rad2
    if cell.index==0 or cell.index==2:
      xr = -rad2
    if cell.index==0 or cell.index==1:
      yr = -rad2
    if len(cell.column.cells)==1: #special case for 1-cell
      xr = 0
      yr = 0
    return (circle[0]+xr, circle[1]+yr)
  
  def getMouseCell(self):
    """ 
    Return the last column cell the mouse clicked on, or None if the last
    mouse click was not on a valid Cell position. 
    """
    if self.mousePos:
      rad2sqrt = (self.colRadius/2)/SQRT2
      
      w = self.colRadius*2 + self.COLUMN_BORDER
      x = self.mousePos[0] / w
      y = self.mousePos[1] / w
      column = None
      try: #if mouse clicked outside entire grid, return None
        column = self.region.columnGrid[x][y]
      except IndexError:
        return None
      
      if column!=None:
        if len(column.cells)==1: #special case for 1-cell
          rad2sqrt =  self.colRadius-(self.colRadius/3)
        
        for cell in column.cells:
          center = self.getCellPos(cell)
          if self.mousePos[0] > center[0]-rad2sqrt and \
             self.mousePos[1] > center[1]-rad2sqrt:
            if self.mousePos[0] < center[0]+rad2sqrt and \
               self.mousePos[1] < center[1]+rad2sqrt:
              return cell
    return None
  
  def drawCell(self, dc, center, radius, cell):
    """ 
    Draw an individual column cell with the center of the cell's
    circle at the pixel location specified by 'center'. 
    @param dc: The wx DC the paint with.
    @param center: the pixel location of the center of the cell's circle.
    @param radius: the pixel radius of the cell's circle.
    @param cell: the HTM Cell to draw.
    """
    #Thick blue circles for active cells, otherwise thin black
    #Filled green circles for predicting cells
    #Vertical line inside circle for learning cells
    wasDrawn = False
    if cell.isActive:
      wasDrawn = True
      dc.SetPen(wx.Pen('BLUE', 1))
    else:
      dc.SetPen(wx.Pen((192,192,192), 1))
    
    if cell.isPredicting:
      wasDrawn = True
      activeSeqSegs = [seg for seg in cell.segments \
                       if seg.isActive() and seg.isSequence]
      if len(activeSeqSegs) > 0:
        dc.SetBrush(wx.Brush('GREEN'))
      else:
        dc.SetBrush(wx.Brush('YELLOW'))
    else:
      dc.SetBrush(wx.Brush('WHITE'))
    
    dc.DrawCircle(center[0], center[1], radius)
    if cell.isLearning:
      wasDrawn = True
      dc.SetPen(wx.Pen('RED', 1))
      dc.DrawLine(center[0], center[1]-radius, center[0], center[1]+radius)
      dc.DrawLine(center[0]-radius, center[1], center[0]+radius, center[1])
    
    #Check recentUpdateList and mark cells that had segments updated
    if cell in self.region.recentUpdateMap:
      #segInfo = self.region.recentUpdateMap[cell]
      wasDrawn = True
      dc.SetPen(wx.Pen('BLACK', 1))
      dc.DrawLine(center[0], center[1]-radius, center[0], center[1]+radius)
      
    return wasDrawn
      
  def syncInputData(self, data):
    self.data = data
    self.mousePos = None


if __name__ == '__main__':
  app = wx.App(redirect=0) #send stdout to console, not new window..
  frame = SimpleRegionFrame()
  frame.Show()
  app.MainLoop()

