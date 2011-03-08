'''
Created on Mar 6, 2011

@author: Barry Maturkanich

The main class to launch the primary Camera Toolkit window.
'''

import wx
from CameraFrame import CameraFrame

if __name__ == '__main__':
  app = wx.App(redirect=0) #send stdout to console, not new window..
  frame = CameraFrame()
  frame.Show()
  app.MainLoop()