#################################################################################################
# utils 
#################################################################################################

import xbmc
import xbmcgui
import xbmcaddon
import xbmcvfs
import json
import os
import cProfile
import pstats
import time
import inspect
import sqlite3
import string
import unicodedata
from xml.etree.ElementTree import Element, SubElement, Comment, tostring
from xml.etree import ElementTree
from xml.dom import minidom
import xml.etree.cElementTree as ET

from API import API
from PlayUtils import PlayUtils
from DownloadUtils import DownloadUtils
downloadUtils = DownloadUtils()
addonSettings = xbmcaddon.Addon(id='plugin.video.emby')
language = addonSettings.getLocalizedString

 
def logMsg(title, msg, level = 1):
    logLevel = int(addonSettings.getSetting("logLevel"))
    if(logLevel >= level):
        if(logLevel == 2): # inspect.stack() is expensive
            try:
                xbmc.log(title + " -> " + inspect.stack()[1][3] + " : " + str(msg))
            except UnicodeEncodeError:
                xbmc.log(title + " -> " + inspect.stack()[1][3] + " : " + str(msg.encode('utf-8')))
        else:
            try:
                xbmc.log(title + " -> " + str(msg))
            except UnicodeEncodeError:
                xbmc.log(title + " -> " + str(msg.encode('utf-8')))

def convertEncoding(data):
    #nasty hack to make sure we have a unicode string
    try:
        return data.decode('utf-8')
    except:
        return data
          
def KodiSQL():
    if xbmc.getInfoLabel("System.BuildVersion").startswith("13"):
        #gotham
        dbVersion = "78"
    if xbmc.getInfoLabel("System.BuildVersion").startswith("15"):
        #isengard
        dbVersion = "91"
    else: 
        #helix
        dbVersion = "90"
    
    dbPath = xbmc.translatePath("special://userdata/Database/MyVideos" + dbVersion + ".db")
    connection = sqlite3.connect(dbPath)

    return connection
        

def checkAuthentication():
    #check authentication
    if addonSettings.getSetting('username') != "" and addonSettings.getSetting('ipaddress') != "":
        try:
            downloadUtils.authenticate()
        except Exception, e:
            logMsg("Emby authentication failed",e)
            pass
    
def prettifyXml(elem):
    rough_string = etree.tostring(elem, "utf-8")
    reparsed = minidom.parseString(rough_string)
    return reparsed.toprettyxml(indent="\t")        
    
def get_params( paramstring ):
    xbmc.log("Parameter string: " + paramstring)
    param={}
    if len(paramstring)>=2:
        params=paramstring

        if params[0] == "?":
            cleanedparams=params[1:]
        else:
            cleanedparams=params

        if (params[len(params)-1]=='/'):
                params=params[0:len(params)-2]

        pairsofparams=cleanedparams.split('&')
        for i in range(len(pairsofparams)):
                splitparams={}
                splitparams=pairsofparams[i].split('=')
                if (len(splitparams))==2:
                        param[splitparams[0]]=splitparams[1]
                elif (len(splitparams))==3:
                        param[splitparams[0]]=splitparams[1]+"="+splitparams[2]
    return param

def startProfiling():
    pr = cProfile.Profile()
    pr.enable()
    return pr
    
def stopProfiling(pr, profileName):
    pr.disable()
    ps = pstats.Stats(pr)
    
    addondir = xbmc.translatePath(xbmcaddon.Addon(id='plugin.video.emby').getAddonInfo('profile'))    
    
    fileTimeStamp = time.strftime("%Y-%m-%d %H-%M-%S")
    tabFileNamepath = os.path.join(addondir, "profiles")
    tabFileName = os.path.join(addondir, "profiles" , profileName + "_profile_(" + fileTimeStamp + ").tab")
    
    if not xbmcvfs.exists(tabFileNamepath):
        xbmcvfs.mkdir(tabFileNamepath)
    
    f = open(tabFileName, 'wb')
    f.write("NumbCalls\tTotalTime\tCumulativeTime\tFunctionName\tFileName\r\n")
    for (key, value) in ps.stats.items():
        (filename, count, func_name) = key
        (ccalls, ncalls, total_time, cumulative_time, callers) = value
        try:
            f.write(str(ncalls) + "\t" + "{:10.4f}".format(total_time) + "\t" + "{:10.4f}".format(cumulative_time) + "\t" + func_name + "\t" + filename + "\r\n")
        except ValueError:
            f.write(str(ncalls) + "\t" + "{0}".format(total_time) + "\t" + "{0}".format(cumulative_time) + "\t" + func_name + "\t" + filename + "\r\n")
    f.close()

def CleanName(filename):
    validFilenameChars = "-_.() %s%s" % (string.ascii_letters, string.digits)
    cleanedFilename = unicodedata.normalize('NFKD', filename).encode('ASCII', 'ignore')
    return ''.join(c for c in cleanedFilename if c in validFilenameChars)
   

def removeDirectory(path):
    if xbmcvfs.exists(path):
        allDirs, allFiles = xbmcvfs.listdir(path)
        for dir in allDirs:
            xbmcvfs.rmdir(os.path.join(path,dir))
        for file in allFiles:
            xbmcvfs.delete(os.path.join(path,file))
        
        xbmcvfs.rmdir(path)
        
def reset():

    return_value = xbmcgui.Dialog().yesno("Warning", "Are you sure you want to reset your local database?")
    if return_value == 0:
        return
    
    # first stop any db sync
    WINDOW = xbmcgui.Window( 10000 )
    WINDOW.setProperty("SyncDatabaseShouldStop", "true")
    
    count = 0
    while(WINDOW.getProperty("SyncDatabaseRunning") == "true"):
        count += 1
        if(count > 10):
            dialog.ok('Warning', 'Could not stop DB sync, you should try again.')
            return
        xbmc.sleep(1000)

    # clear video database
    connection = KodiSQL()
    cursor = connection.cursor()
    try:
        cursor.execute("DROP TABLE episode;")
    except:
        pass
    try:
        cursor.execute("DROP TABLE movie;")
    except:
        pass
    try:
        cursor.execute("DROP TABLE tvshow;")
    except:
        pass
    try:
        cursor.execute("DROP TABLE actors;")
    except:
        pass
    try:
        cursor.execute("DROP TABLE actorlinkepisode;")
    except:
        pass
    try:
        cursor.execute("DROP TABLE actorlinkmovie;")
    except:
        pass
    try:
        cursor.execute("DROP TABLE actorlinktvshow;")
    except:
        pass
    try:
        cursor.execute("DROP TABLE art;")
    except:
        pass
    try:
        cursor.execute("DROP TABLE artistlinkmusicvideo;")
    except:
        pass
    try:
        cursor.execute("DROP TABLE countrylinkmovie;")
    except:
        pass
    try:
        cursor.execute("DROP TABLE directorlinkepisode;")
    except:
        pass
    try:
        cursor.execute("DROP TABLE directorlinkmovie;")
    except:
        pass
    try:
        cursor.execute("DROP TABLE directorlinkmusicvideo;")
    except:
        pass
    try:
        cursor.execute("DROP TABLE directorlinktvshow;")
    except:
        pass
    try:
        cursor.execute("DROP TABLE files;")
    except:
        pass
    try:
        cursor.execute("DROP TABLE genre;")
    except:
        pass
    try:
        cursor.execute("DROP TABLE genrelinkmovie;")
    except:
        pass
    try:
        cursor.execute("DROP TABLE genrelinkmusicvideo;")
    except:
        pass
    try:
        cursor.execute("DROP TABLE genrelinktvshow;")
    except:
        pass
    try:
        cursor.execute("DROP TABLE movielinktvshow;")
    except:
        pass
    try:
        cursor.execute("DROP TABLE musicvideo;")
    except:
        pass
    try:
        cursor.execute("DROP TABLE path;")
    except:
        pass
    try:
        cursor.execute("DROP TABLE seasons;")
    except:
        pass
    try:
        cursor.execute("DROP TABLE sets;")
    except:
        pass
    try:
        cursor.execute("DROP TABLE stacktimes;")
    except:
        pass
    try:
        cursor.execute("DROP TABLE streamdetails;")
    except:
        pass
    try:
        cursor.execute("DROP TABLE studio;")
    except:
        pass
    try:
        cursor.execute("DROP TABLE studiolinkmovie;")
    except:
        pass
    try:
        cursor.execute("DROP TABLE studiolinkmusicvideo;")
    except:
        pass
    try:
        cursor.execute("DROP TABLE studiolinktvshow;")
    except:
        pass
    try:
        cursor.execute("DROP TABLE tag;")
    except:
        pass
    try:
        cursor.execute("DROP TABLE taglinks;")
    except:
        pass
    try:
        cursor.execute("DROP TABLE tvshowlinkepisode;")
    except:
        pass
    try:
        cursor.execute("DROP TABLE tvshowlinkpath;")
    except:
        pass
    try:
        cursor.execute("DROP TABLE version;")
    except:
        pass
    try:
        cursor.execute("DROP TABLE writerlinkepisode;")
    except:
        pass
    try:
        cursor.execute("DROP TABLE writerlinkmovie;")  
    except:
        pass
    
    try:
        connection.commit()
        logMsg("Emby","Removed tables from kodi database")
    finally:
        cursor.close()
        
    # check for old library folder and delete if present
    addon = xbmcaddon.Addon(id='plugin.video.emby')
    addondir = xbmc.translatePath(addon.getAddonInfo('profile'))
    dataPath = os.path.join(addondir,"library" + os.sep)
    removeDirectory(dataPath)
    
    # remove old entries from sources.xml
    
    # reset addon settings values
    addon.setSetting("SyncInstallRunDone", "false") 
    addon.setSetting("SyncFirstCountsRunDone", "false")
    
    dialog = xbmcgui.Dialog()
    dialog.ok('Emby Reset', 'Reset of Emby has completed, you need to restart.')
    xbmc.executebuiltin("RestartApp")
     
