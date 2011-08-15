"""
Created on May 11, 2011

@author: Barry Maturkanich

Helper file to launch the HMAX Camera Toolkit application.
"""

import wx
from NetworkFrame import NetworkFrame

if __name__ == '__main__':
  app = wx.App(redirect=0) #send stdout to console, not new window..
  frame = NetworkFrame()
  frame.Show()
  app.MainLoop()