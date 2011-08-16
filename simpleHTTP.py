import tornado.web
import tornado.ioloop
import serial
import os
import json
import sys
import glob

class Port():
    """ Port - Class maintains all functions for dealing with a serial port
        ser - is the serial port object from serial.py  most of the function acts as a psss through
        OpenPort(<portname>) = Opens a serial Port (ser.openPort(<your port>)
        ReadTil(<delimiter>) = read serial port until delimiter is found ReadTil('=")
        WriteTG(<tg commmand>) = write string to a tingG board WriteTG("go x10")
        Scan() = returns a list of serial ports.
        """
    ser = serial.Serial()

    def __init__(self,portName):
            r  = self.OpenPort(self.ser,portName)
            if r == True:
                print "port  " + self.ser.port + " is open"
            else:
                print "port " + self.ser.port + " failed to open"
  
            
    def OpenPort(self, ser,portName):
        ser.port = portName
        ser.baudrate= 115200
        ser.xonxoff = True
        ser.timeout = 10
        ser.open()  
        return ser.isOpen()


    def ReadTil(self, c):
        s = ""
        while True:
            g = self.ser.read()
            if g == c:
                return s+g
            else:
                s = s+g
            
    def WriteTG(self, s):
        self.ser.write(s + "\r\n")
        r = self.ReadTil('>')
        return r

    def scan(self):
        available = []
        ports = glob.glob('/dev/tty.usbserial*') + glob.glob('/dev/cu.usbserial*')
        currPort = self.ser.portstr
        for port in ports:
            try:
                s = serial.Serial(port)
                available.append( (port, s.portstr))
                s.close()   # explicit close 'cause of delayed GC in java
                print "testing port:" + s.portstr
            except serial.SerialException:
                pass
            self.OpenPort(self.ser,currPort)
            return available

class CommandHandler(tornado.web.RequestHandler):
    """ Command Handler for TG - passes command to TG via Port object

        /tg?<cmd1=args>&<cmd2=....

        Each command must be a valid TG command, arguments are used to modify a command
        e.g. set return type to JSON etc

        /tg??=JSON
        """

    dicValues = {}
    
    def get(self):
        print "TG Command Processor Get"
        cmds = self.request.query.replace("%20"," ")
        cmds = cmds.split("&")
        #CMDS an array of commmands
        message = ""
        try:
            for cmd in cmds:
                print "Get - Command: " +  cmd
                #cmds can have an =  spliting the tg command from server side mods
                c = cmd.split("=")

                if len(c)==1: #no args
                    message= message + p.WriteTG(c[0]) +'\n'
                    print message
                    
                else: #Args - right now only JSON but can add more later
                    if c[1] == "JSON":
                        #convert response to  a dictionary
                        d = self.jsonify(p.WriteTG(c[0]))
                        message = message + json.dumps(d) + '\n'
                    else:
                        #handle other args
                        pass         
        
           #request.finish()
        except: 
            ErrorString = str((sys.exc_info()[1]))
            print ErrorString
            self.write("ERROR: " + ErrorString + '\n')
            pass
        self.write(message)
        
    def put(self):
        print "TG Command Proccessor"
        cmd = self.request.query
        print"Put Command= " + cmd
        self.write("got - " + self.request.query)

    def jsonify(self,s):
        l = s.splitlines()
        try:
            map(self.AddKeyValue,l)
        except:
            pass
        return self.dicValues
    
    def AddKeyValue(self,t):
        toks = t.split(":")
        self.dicValues[toks[0]]=toks[1]
        
                

class EveryThingHandler(tornado.web.RequestHandler):
    """ EveryThingHandler - handles generic requests
        Most important function is to sever the TG webpage.
        """
    def get(self):
        self.render("TGJQ.html")

    def getfile(self,fname):
        f = open(fname)
        contents = f.read()
        f.close
        return contents
    
class ServerHandler(tornado.web.RequestHandler):
    """ServerHandler - Handle all requests directed towards the Server
        Server commands are in the form

        /Server?<cmd1=arg1,arg2>&<cmd2=....
        
        ListPorts = Lists avaialble Ports /server?ListPorts
        OpenPort = Open a port /server?OpenPort=<your port>"""

    print "TG Server Manager"
    commands = {}
    
    def get(self):
        print "Command: " +  self.request.query
        commands =  {
            "ListPorts": self.ListPorts,
            "OpenPort": self.OpenPort
            }

        toks = self.request.query.split("&")
        try:
            for cmd in toks:
                cmdargs = cmd.split('=')
                if len(cmdargs) == 2:
                    commands[cmdargs[0]](cmdargs[1])
                else:
                    commands[cmdargs[0]]()
        except:
            self.write( "Error in command" + cmd )
            print (sys.exc_info()[0])
            pass

    def ListPorts(self):
        r = p.scan()
        self.write("Available Ports:")
        print  r
        for  port in r:
            self.write(port[0])

    def OpenPort(self,arg):
        r = p.OpenPort(p.ser,arg)
        if r:
            self.write( "Port: " + p.ser.port + " is Open")
        else:        
            self.write( "Port: " + p.ser.port + " is NOT open")
#  To Do
# deal with security?
# build in generic web page support?
# Use List comprehension instead of loops to be more pythonic eg
# commands[r]{arg} for r in toks
# Add multiple commands to TG handler

application = tornado.web.Application([
    (r"/tg?", CommandHandler),
    (r"/server?", ServerHandler),
    (r".*",EveryThingHandler)
    ],debug=True,autoescaping=True,static_path=os.path.join(os.getcwd(), "static"),)

#Add optional args for baud etc.
p = Port('/dev/tty.usbserial-A700fhWc')

if __name__ == "__main__":   
    application.listen(8888)    
    tornado.ioloop.IOLoop.instance().start()
