import sys
import os
import thread
import wx

class LockedClass:
    def __getattr__(self,name):
        cls = self.__class__
        if name in cls.__dict__:
            a = cls.__dict__[name]
        elif name in self.__dict__:
            a = self.__dict__[name]
        else:
            raise AttributeError("no such member: "+str(name)) 

        if a and type(a) == type(self.get):
            lock = self.lock
            def f(*args, **kargs):
                lock.acquire()
                try:
                    return a()
                finally:
                    lock.release()
            return f
        return a


class LogFrame(wx.Frame):
    def __init__(self,application,lock):
        wx.Frame.__init__(self, None, -1, style = wx.DEFAULT_FRAME_STYLE)
        self.lock = lock
        self.output = []

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
        # copy content of self.output
        self.lock.acquire()
        try:
            output,self.output = self.output[:],[]
        finally:
            self.lock.release()

        for txt in output:
            self.txt.WriteText(txt)
        self.Refresh()

    def exit(self, event):
        sys.exit(0)

    def OpenBrowser(self, event):
        os.system("launch http://127.0.0.1:8081/")

class MyApp(wx.App):
    def __init__(self, lock):
        wx.App.__init__(self, redirect=False, filename=None, useBestVisual=False)
        self.frame = LogFrame(self, lock)
        self.lock = lock
        self.SetTopWindow(self.frame)
        self.frame.Show(True)
    def OnInit(self):
        return True

class mystdout:
    def __init__(self, stdout, app, lock):
        self.stdout = stdout
        self.app = app
        self.lock = lock
    def write(self, s):
        try:
            self.lock.acquire()
            try:
                self.app.frame.output += [s]
            finally:
                self.lock.release()
            wx.PostEvent(self.app.frame, wx.PaintEvent(42))
        except:
            self.stdout.write("error\n")
            self.stdout.write(str(sys.exc_info()[0]))
            self.stdout.write(str(sys.exc_info()[1]))
            for l in traceback.extract_tb(sys.exc_info()[2]):
                self.stdout.write("  File \"%s\", line %d, in %s\n" % (l[0],l[1],l[2]))
                self.stdout.write("    %s\n" % l[3])
            return s
    def flush(self):
        pass

def start():
    lock = thread.allocate_lock()
    app = MyApp(lock)
    sys.stdout = sys.stderr = mystdout(sys.stdout, app, lock)
    thread_id = thread.start_new_thread(app.MainLoop, ())
