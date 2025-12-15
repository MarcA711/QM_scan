# -*- coding: utf-8 -*-
"""
Created on Fri Aug 26 10:12:56 2022

@author: Esteban Gomez-Lopez
AG Nanooptik
Institut fur Physik
Humboldt-Universitat zu Berlin
"""

import numpy as np

"Waveform functions"
def gaussian(x,x0,w):
    w = w/(2*np.sqrt(2*np.log(2)))
    return np.exp(-(x-x0)**2/(2*w**2))

def supergauss(x,x0,w,n):
    w = w/(2*np.sqrt(2*np.log(2)))
    return np.exp(-((x-x0)**2/(2*w**2))**n)

def lor(x,x0,w):
    return np.exp((w/2)**2/((x-x0)**2+(w/2)**2))

"Create the marker data to send to AWG"
def createMarkerData(marker1_arr):
    # Marker data is an 8 bit value. Bit 7 = marker 1, bit 6 = marker 2, bit 5 = marker 3, bit 4 = marker 4
    markerData = (1 << 7) * marker1_arr.astype(np.uint8)
    return markerData

"Send waveform to AWG"
#Name = name of waveform, recordLength = num samples in waveform, wfmArr = array of normalized voltages (output of createWaveform...)
def sendWaveform(awg, name, recordLength, wfmArr):
    delete_wfm = 'wlist:waveform:delete "{:s}"'.format(name) #Command to delete waveform with same name from the waveform list
    create_wfm = 'wlist:waveform:new "{:s}", {:d}'.format(name, recordLength) #Command to create waveform with this name
    wfm_bytes = len(wfmArr) * 4 #Convert to number of bytes as specified by manual
    wfm_header = 'wlist:waveform:data "{:s}", 0, {:d}, '.format(name, recordLength, len(str(wfm_bytes)), wfm_bytes) #Wfm header (see manual)
    awg.write(delete_wfm)
    awg.write(create_wfm)
    ret=awg.write_binary_values(wfm_header, wfmArr) #Send waveform as binary values
    print('Waveform bytes: {}'.format(ret))
    return ret

"Send marker data to AWG"
#Name = name of waveform, recordLength = num samples in marker (should be same as for wfm), markerData = in bits
def sendMarkerData(awg, name, recordLength, markerData):
    marker_bytes = len(markerData) * 4 #Convert to number of bytes as specified by manual
    marker_header = 'wlist:waveform:marker:data "{:s}", 0, {:d}, '.format(name, recordLength, len(str(marker_bytes)), marker_bytes) #Marker header (see manual)
    ret=awg.write_binary_values(marker_header, markerData,datatype='B') #Send marker data as binary values
    print('Marker bytes: {}'.format(ret))
    return ret

"Load waveform + markers to AWG channel"
def loadWaveform(awg, name, channelNum):
    if channelNum ==1:
        return awg.write('source1:waveform "{}"'.format(name))
    elif channelNum == 2:
        return awg.write('source2:waveform "{}"'.format(name))
    else:
        print("Enter valid channel number (1 or 2)")

"Check for error reports from AW"
def checkErrors(awg):
    error = awg.query('system:error:all?')
    print('Status: {}'.format(error))