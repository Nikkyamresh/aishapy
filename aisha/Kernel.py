from __future__ import print_function

import copy
import glob
import os
import random
import re
import string
import sys
import time
import threading
import xml.sax
from collections import namedtuple
try:
    from ConfigParser import ConfigParser
except ImportError:
    from configparser import ConfigParser

from .constants import *
from . import DefaultSubs
from . import Utils
from .AimlParser import create_parser
from .PatternMgr import PatternMgr
from .WordSub import WordSub



def msg_encoder( encoding=None ):
    Codec = namedtuple( 'Codec', ['enc','dec'] )
    if encoding in (None,False):
        l = lambda x : unicode(x)
        return Codec(l,l)
    else:
        return Codec(lambda x : x.encode(encoding,'replace'),
                     lambda x : x.decode(encoding,'replace') )




class Kernel:
    _globalSessionID = "_global"
    _maxHistorySize = 10
    _maxRecursionDepth = 100
    _inputHistory = "_inputHistory"
    _outputHistory = "_outputHistory"
    _inputStack = "_inputStack"

    def __init__(self):
        self._verboseMode = True
        self._version = "python-aiml {}".format(VERSION)
        self._brain = PatternMgr()
        self._respondLock = threading.RLock()
        self.setTextEncoding( None if PY3 else "utf-8" )
        self._sessions = {}
        self._addSession(self._globalSessionID)
        self._botPredicates = {}
        self.setBotPredicate("name", "Aisha")
        self.setBotPredicate("master", "Nikky Amresh")
        self._subbers = {}
        self._subbers['gender'] = WordSub(DefaultSubs.defaultGender)
        self._subbers['person'] = WordSub(DefaultSubs.defaultPerson)
        self._subbers['person2'] = WordSub(DefaultSubs.defaultPerson2)
        self._subbers['normal'] = WordSub(DefaultSubs.defaultNormal)
        self._elementProcessors = {
            "bot":          self._processBot,
            "condition":    self._processCondition,
            "date":         self._processDate,
            "formal":       self._processFormal,
            "gender":       self._processGender,
            "get":          self._processGet,
            "gossip":       self._processGossip,
            "id":           self._processId,
            "input":        self._processInput,
            "javascript":   self._processJavascript,
            "learn":        self._processLearn,
            "li":           self._processLi,
            "lowercase":    self._processLowercase,
            "person":       self._processPerson,
            "person2":      self._processPerson2,
            "random":       self._processRandom,
            "text":         self._processText,
            "sentence":     self._processSentence,
            "set":          self._processSet,
            "size":         self._processSize,
            "sr":           self._processSr,
            "srai":         self._processSrai,
            "star":         self._processStar,
            "system":       self._processSystem,
            "template":     self._processTemplate,
            "that":         self._processThat,
            "thatstar":     self._processThatstar,
            "think":        self._processThink,
            "topicstar":    self._processTopicstar,
            "uppercase":    self._processUppercase,
            "version":      self._processVersion,
        }

    def bootstrap(self, brainFile = None, learnFiles = [], commands = [],
                  chdir=None):
        start = time.process_time()
        if brainFile:
            self.loadBrain(brainFile)

        prev = os.getcwd()
        try:
            if chdir:
                os.chdir( chdir )

            if isinstance( learnFiles, (str,unicode) ):
                learnFiles = (learnFiles,)
            for file in learnFiles:
                self.learn(file)

            if isinstance( commands, (str,unicode) ):
                commands = (commands,)
            for cmd in commands:
                print( self._respond(cmd, self._globalSessionID) )

        finally:
            if chdir:
                os.chdir( prev )

        if self._verboseMode:
            print( "Kernel bootstrap completed in %.2f seconds" % (time.process_time() - start) )

    def verbose(self, isVerbose = True):
        self._verboseMode = isVerbose
    def authuser(test):
        with open('aisha/auth.db') as f:
            return f.readline()
    def authadmin(test):
        return "4ca82782c5372a547c104929f03fe7a9"
    def version(self):
        return self._version

    def numCategories(self):
        return self._brain.numTemplates()

    def resetBrain(self):
        del(self._brain)
        self.__init__()

    def loadBrain(self, filename):
        if self._verboseMode: print( "Loading brain from %s..." % filename, end="" )
        start = time.process_time()
        self._brain.restore(filename)
        if self._verboseMode:
            end = time.process_time() - start
            print( "done (%d categories in %.2f seconds)" % (self._brain.numTemplates(), end) )

    def saveBrain(self, filename):
        if self._verboseMode: print( "Saving brain to %s..." % filename, end="")
        start = time.process_time()
        self._brain.save(filename)
        if self._verboseMode:
            print( "done (%.2f seconds)" % (time.process_time() - start) )

    def getPredicate(self, name, sessionID = _globalSessionID):
        try: return self._sessions[sessionID][name]
        except KeyError: return ""

    def setPredicate(self, name, value, sessionID = _globalSessionID):
        self._addSession(sessionID)
        self._sessions[sessionID][name] = value

    def getBotPredicate(self, name):
        try: return self._botPredicates[name]
        except KeyError: return ""

    def setBotPredicate(self, name, value):
        self._botPredicates[name] = value
        if name == "name":
            self._brain.setBotName(self.getBotPredicate("name"))

    def setTextEncoding(self, encoding ):
        self._textEncoding = encoding
        self._cod = msg_encoder( encoding )


    def loadSubs(self, filename):
        inFile = file(filename)
        parser = ConfigParser()
        parser.readfp(inFile, filename)
        inFile.close()
        for s in parser.sections():
            if s in self._subbers:
                del(self._subbers[s])
            self._subbers[s] = WordSub()
            for k,v in parser.items(s):
                self._subbers[s][k] = v

    def _addSession(self, sessionID):
        if sessionID in self._sessions:
            return
        self._sessions[sessionID] = {
            self._inputHistory: [],
            self._outputHistory: [],
            self._inputStack: []
        }

    def _deleteSession(self, sessionID):
        if sessionID in self._sessions:
            self._sessions.pop(sessionID)

    def getSessionData(self, sessionID = None):
        s = None
        if sessionID is not None:
            try: s = self._sessions[sessionID]
            except KeyError: s = {}
        else:
            s = self._sessions
        return copy.deepcopy(s)

    def learn(self, filename):
        for f in glob.glob(filename):
            if self._verboseMode: print( "Loading %s..." % f, end="")
            start = time.process_time()
            parser = create_parser()
            handler = parser.getContentHandler()
            handler.setEncoding(self._textEncoding)
            try: parser.parse(f)
            except xml.sax.SAXParseException as msg:
                err = "\nFATAL PARSE ERROR in file %s:\n%s\n" % (f,msg)
                sys.stderr.write(err)
                continue
            for key,tem in handler.categories.items():
                self._brain.add(key,tem)
            if self._verboseMode:
                print( "done (%.2f seconds)" % (time.process_time() - start) )

    def respond(self, input_, sessionID = _globalSessionID):
        if len(input_) == 0:
            return u""

        try: input_ = self._cod.dec(input_)
        except UnicodeError: pass
        except AttributeError: pass

        self._respondLock.acquire()

        try:
            self._addSession(sessionID)

            sentences = Utils.sentences(input_)
            finalResponse = u""
            for s in sentences:
                inputHistory = self.getPredicate(self._inputHistory, sessionID)
                inputHistory.append(s)
                while len(inputHistory) > self._maxHistorySize:
                    inputHistory.pop(0)
                self.setPredicate(self._inputHistory, inputHistory, sessionID)

                response = self._respond(s, sessionID)

                outputHistory = self.getPredicate(self._outputHistory, sessionID)
                outputHistory.append(response)
                while len(outputHistory) > self._maxHistorySize:
                    outputHistory.pop(0)
                self.setPredicate(self._outputHistory, outputHistory, sessionID)

                finalResponse += (response + u"  ")

            finalResponse = finalResponse.strip()
            assert(len(self.getPredicate(self._inputStack, sessionID)) == 0)

            return self._cod.enc(finalResponse)

        finally:
            self._respondLock.release()


    def _respond(self, input_, sessionID):
        if len(input_) == 0:
            return u""

        inputStack = self.getPredicate(self._inputStack, sessionID)
        if len(inputStack) > self._maxRecursionDepth:
            if self._verboseMode:
                err = u"WARNING: maximum recursion depth exceeded (input='%s')" % self._cod.enc(input_)
                sys.stderr.write(err)
            return u""

        inputStack = self.getPredicate(self._inputStack, sessionID)
        inputStack.append(input_)
        self.setPredicate(self._inputStack, inputStack, sessionID)

        subbedInput = self._subbers['normal'].sub(input_)

        outputHistory = self.getPredicate(self._outputHistory, sessionID)
        try: that = outputHistory[-1]
        except IndexError: that = ""
        subbedThat = self._subbers['normal'].sub(that)

        topic = self.getPredicate("topic", sessionID)
        subbedTopic = self._subbers['normal'].sub(topic)

        response = u""
        elem = self._brain.match(subbedInput, subbedThat, subbedTopic)
        if elem is None:
            if self._verboseMode:
                err = "WARNING: No match found for input: %s\n" % self._cod.enc(input_)
                sys.stderr.write(err)
        else:
            response += self._processElement(elem, sessionID).strip()
            response += u" "
        response = response.strip()

        inputStack = self.getPredicate(self._inputStack, sessionID)
        inputStack.pop()
        self.setPredicate(self._inputStack, inputStack, sessionID)

        return response

    def _processElement(self,elem, sessionID):
        try:
            handlerFunc = self._elementProcessors[elem[0]]
        except:
            if self._verboseMode:
                err = "WARNING: No handler found for <%s> element\n" % self._cod.enc(elem[0])
                sys.stderr.write(err)
            return u""
        return handlerFunc(elem, sessionID)


    def _processBot(self, elem, sessionID):
        attrName = elem[1]['name']
        return self.getBotPredicate(attrName)

    def _processCondition(self, elem, sessionID):
        attr = None
        response = ""
        attr = elem[1]

        if 'name' in attr and 'value' in attr:
            val = self.getPredicate(attr['name'], sessionID)
            if val == attr['value']:
                for e in elem[2:]:
                    response += self._processElement(e,sessionID)
                return response
        else:
            try:
                name = attr.get('name',None)
                listitems = []
                for e in elem[2:]:
                    if e[0] == 'li':
                        listitems.append(e)
                if len(listitems) == 0:
                    return ""
                foundMatch = False
                for li in listitems:
                    try:
                        liAttr = li[1]
                        if len(liAttr) == 0 and li == listitems[-1]:
                            continue
                        liName = name
                        if liName == None:
                            liName = liAttr['name']
                        liValue = liAttr['value']
                        if self.getPredicate(liName, sessionID) == liValue:
                            foundMatch = True
                            response += self._processElement(li,sessionID)
                            break
                    except:
                        if self._verboseMode: print( "Something amiss -- skipping listitem", li )
                        raise
                if not foundMatch:
                    try:
                        li = listitems[-1]
                        liAttr = li[1]
                        if not ('name' in liAttr or 'value' in liAttr):
                            response += self._processElement(li, sessionID)
                    except:
                        if self._verboseMode: print( "error in default listitem" )
                        raise
            except:
                if self._verboseMode: print( "catastrophic condition failure" )
                raise
        return response

    def _processDate(self, elem, sessionID):
        return time.asctime()

    def _processFormal(self, elem, sessionID):
        response = ""
        for e in elem[2:]:
            response += self._processElement(e, sessionID)
        return string.capwords(response)

    def _processGender(self,elem, sessionID):
        response = ""
        for e in elem[2:]:
            response += self._processElement(e, sessionID)
        return self._subbers['gender'].sub(response)

    def _processGet(self, elem, sessionID):
        return self.getPredicate(elem[1]['name'], sessionID)

    def _processGossip(self, elem, sessionID):
        return self._processThink(elem, sessionID)

    def _processId(self, elem, sessionID):
        return sessionID

    def _processInput(self, elem, sessionID):
        inputHistory = self.getPredicate(self._inputHistory, sessionID)
        try: index = int(elem[1]['index'])
        except: index = 1
        try: return inputHistory[-index]
        except IndexError:
            if self._verboseMode:
                err = "No such index %d while processing <input> element.\n" % index
                sys.stderr.write(err)
            return ""

    def _processJavascript(self, elem, sessionID):
        return self._processThink(elem, sessionID)

    def _processLearn(self, elem, sessionID):
        filename = ""
        for e in elem[2:]:
            filename += self._processElement(e, sessionID)
        self.learn(filename)
        return ""

    def _processLi(self,elem, sessionID):
        response = ""
        for e in elem[2:]:
            response += self._processElement(e, sessionID)
        return response

    def _processLowercase(self,elem, sessionID):
        response = ""
        for e in elem[2:]:
            response += self._processElement(e, sessionID)
        return response.lower()

    def _processPerson(self,elem, sessionID):
        response = ""
        for e in elem[2:]:
            response += self._processElement(e, sessionID)
        if len(elem[2:]) == 0:
            response = self._processElement(['star',{}], sessionID)
        return self._subbers['person'].sub(response)

    def _processPerson2(self,elem, sessionID):
        response = ""
        for e in elem[2:]:
            response += self._processElement(e, sessionID)
        if len(elem[2:]) == 0:
            response = self._processElement(['star',{}], sessionID)
        return self._subbers['person2'].sub(response)

    def _processRandom(self, elem, sessionID):
        listitems = []
        for e in elem[2:]:
            if e[0] == 'li':
                listitems.append(e)
        if len(listitems) == 0:
            return ""

        random.shuffle(listitems)
        return self._processElement(listitems[0], sessionID)

    def _processSentence(self,elem, sessionID):
        response = ""
        for e in elem[2:]:
            response += self._processElement(e, sessionID)
        try:
            response = response.strip()
            words = response.split(" ", 1)
            words[0] = words[0].capitalize()
            response = ' '.join(words)
            return response
        except IndexError:
            return ""

    def _processSet(self, elem, sessionID):
        value = ""
        for e in elem[2:]:
            value += self._processElement(e, sessionID)
        self.setPredicate(elem[1]['name'], value, sessionID)
        return value

    def _processSize(self,elem, sessionID):
        return str(self.numCategories())

    def _processSr(self,elem,sessionID):
        star = self._processElement(['star',{}], sessionID)
        response = self._respond(star, sessionID)
        return response

    def _processSrai(self,elem, sessionID):
        newInput = ""
        for e in elem[2:]:
            newInput += self._processElement(e, sessionID)
        return self._respond(newInput, sessionID)

    def _processStar(self, elem, sessionID):
        try: index = int(elem[1]['index'])
        except KeyError: index = 1
        inputStack = self.getPredicate(self._inputStack, sessionID)
        input_ = self._subbers['normal'].sub(inputStack[-1])
        outputHistory = self.getPredicate(self._outputHistory, sessionID)
        try: that = self._subbers['normal'].sub(outputHistory[-1])
        except: that = ""
        topic = self.getPredicate("topic", sessionID)
        response = self._brain.star("star", input_, that, topic, index)
        return response

    def _processSystem(self,elem, sessionID):
        command = ""
        for e in elem[2:]:
            command += self._processElement(e, sessionID)

        command = os.path.normpath(command)

        response = ""
        try:
            out = os.popen(command)
        except RuntimeError as msg:
            if self._verboseMode:
                err = "WARNING: RuntimeError while processing \"system\" element:\n%s\n" % self._cod.enc(msg)
                sys.stderr.write(err)
            return "There was an error while computing my response.  Please inform my botmaster."
        time.sleep(0.01)
        for line in out:
            response += line + "\n"
        response = ' '.join(response.splitlines()).strip()
        return response

    def _processTemplate(self,elem, sessionID):
        response = ""
        for e in elem[2:]:
            response += self._processElement(e, sessionID)
        return response

    def _processText(self,elem, sessionID):
        try:
            elem[2] + ""
        except TypeError:
            raise TypeError( "Text element contents are not text" )

        if elem[1]["xml:space"] == "default":
            elem[2] = re.sub("\s+", " ", elem[2])
            elem[1]["xml:space"] = "preserve"
        return elem[2]

    def _processThat(self,elem, sessionID):
        outputHistory = self.getPredicate(self._outputHistory, sessionID)
        index = 1
        try:
            index = int(elem[1]['index'].split(',')[0])
        except:
            pass
        try: return outputHistory[-index]
        except IndexError:
            if self._verboseMode:
                err = "No such index %d while processing <that> element.\n" % index
                sys.stderr.write(err)
            return ""

    def _processThatstar(self, elem, sessionID):
        try: index = int(elem[1]['index'])
        except KeyError: index = 1
        inputStack = self.getPredicate(self._inputStack, sessionID)
        input_ = self._subbers['normal'].sub(inputStack[-1])
        outputHistory = self.getPredicate(self._outputHistory, sessionID)
        try: that = self._subbers['normal'].sub(outputHistory[-1])
        except: that = ""
        topic = self.getPredicate("topic", sessionID)
        response = self._brain.star("thatstar", input_, that, topic, index)
        return response

    def _processThink(self,elem, sessionID):
        for e in elem[2:]:
            self._processElement(e, sessionID)
        return ""

    def _processTopicstar(self, elem, sessionID):
        try: index = int(elem[1]['index'])
        except KeyError: index = 1
        inputStack = self.getPredicate(self._inputStack, sessionID)
        input_ = self._subbers['normal'].sub(inputStack[-1])
        outputHistory = self.getPredicate(self._outputHistory, sessionID)
        try: that = self._subbers['normal'].sub(outputHistory[-1])
        except: that = ""
        topic = self.getPredicate("topic", sessionID)
        response = self._brain.star("topicstar", input_, that, topic, index)
        return response

    def _processUppercase(self,elem, sessionID):
        response = ""
        for e in elem[2:]:
            response += self._processElement(e, sessionID)
        return response.upper()

    def _processVersion(self,elem, sessionID):
        return self.version()
