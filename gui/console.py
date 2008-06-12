import sys
import os
import thread
import wx

class LogFrame(wx.Frame):
    def __init__(self,application):
        wx.Frame.__init__(self, None, -1, style = wx.DEFAULT_FRAME_STYLE)
        vsplit = wx.BoxSizer(wx.VERTICAL)
        
        #hsplit = wx.BoxSizer(wx.HORIZONTAL)
        #startbutton = wx.Button(self, -1, "Start")
        #hsplit.Add(startbutton, 1, wx.EXPAND)
        #stopbutton = wx.Button(self, -1, "Stop")
        #hsplit.Add(stopbutton, 1, wx.EXPAND)
        #vsplit.Add(hsplit, 0, wx.EXPAND)

        browserbutton = wx.Button(self, -1, "Open mediaTUM Browser Window")
        self.Bind(wx.EVT_BUTTON, self.OpenBrowser, browserbutton)
        vsplit.Add(browserbutton, 0, wx.EXPAND)

        self.application = application
        self.txt = wx.TextCtrl(self, style=wx.TE_MULTILINE|wx.TE_READONLY)
        self.txt.SetMinSize((700,400))
        self.SetAutoLayout(True)
        self.SetSizer(vsplit)

        vsplit.Add(self.txt, 1, wx.EXPAND, 0)
        vsplit.Fit(self)
        vsplit.SetSizeHints(self)
        
        self.Bind(wx.EVT_PAINT, self.OnPaint)
        self.Bind(wx.EVT_CLOSE, self.exit)

    def OnPaint(self, event):
        self.Refresh()

    def exit(self, event):
        sys.exit(0)

    def OpenBrowser(self, event):
        os.system("launch http://127.0.0.1:8081/")


class MyApp(wx.App):
    def __init__(self):
        wx.App.__init__(self, redirect=False, filename=None, useBestVisual=False)
        self.frame = LogFrame(self)
        self.SetTopWindow(self.frame)
        self.frame.Show(True)
    def OnInit(self):
        return True

class mystdout:
    def __init__(self, stdout, app):
        self.stdout = stdout
        self.app = app
        self.lock = thread.allocate_lock()
    def write(self, s):
        self.lock.acquire()
        try:
            self.app.frame.txt.WriteText(s)
            wx.PostEvent(self.app.frame, wx.PaintEvent(42))
        except:
            self.stdout.write("error\n")
            self.stdout.write(str(sys.exc_info()[0]))
            self.stdout.write(str(sys.exc_info()[1]))
            for l in traceback.extract_tb(sys.exc_info()[2]):
                self.stdout.write("  File \"%s\", line %d, in %s\n" % (l[0],l[1],l[2]))
                self.stdout.write("    %s\n" % l[3])
            return s
        finally:
            self.lock.release()
    def flush(self):
        pass

def start():
    app = MyApp()
    sys.stdout = sys.stderr = mystdout(sys.stdout, app)
    thread_id = thread.start_new_thread(app.MainLoop, ())
