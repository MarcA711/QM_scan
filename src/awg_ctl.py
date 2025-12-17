# -*- coding: utf-8 -*-
"""
Created on Wed Sep 28 13:36:43 2022

Connect and control Tektronix AWG5204
Scripts: pulse_gen.py, AWGfun.py

@author: Esteban Gomez-Lopez
AG Nanooptik
Institut fur Physik
Humboldt-Universitat zu Berlin
"""

import pyvisa as visa
import numpy as np

class AwgCtl:
    def __init__(self):
        # Set up VISA instrument object
        rm = visa.ResourceManager('@py')
        self.awg = rm.open_resource('TCPIP0::141.20.45.148::inst0::INSTR')
        self.awg.timeout = 10000 #float('+inf') #(in ms)
        print('Connected to ', self.awg.query('*idn?'))

    def __del__(self):
        self.awg.write('output1 off')
        self.awg.write('output2 off')
        self.awg.write('output3 off')
        self.awg.write('output4 off')
        self.awg.write('awgcontrol:stop:immediate')
        self.awg.close()

    def gaussian(x,x0,w):
        w = w/(2*np.sqrt(2*np.log(2)))
        return np.exp(-(x-x0)**2/(2*w**2))

    def supergauss(x,x0,w,n):
        w = w/(2*np.sqrt(2*np.log(2)))
        return np.exp(-((x-x0)**2/(2*w**2))**n)

    def lor(x,x0,w):
        return np.exp((w/2)**2/((x-x0)**2+(w/2)**2))
    
    def createMarkerData(marker1_arr):
        # Marker data is an 8 bit value. Bit 7 = marker 1, bit 6 = marker 2, bit 5 = marker 3, bit 4 = marker 4
        markerData = (1 << 7) * marker1_arr.astype(np.uint8)
        return markerData

    def gen_scan_pulse(write_width, signal_width, offset):
        sample_rate = 2.5E9 #(samples/s)
        samples = 5000 #(maximum 2E9 samples in memory)

        tw_pulse_c = write_width * 1E-9 #(in s) width of control pulse
        tw_pulse_s = signal_width * 1E-9 #(in s) width of signal pulse
        tw_pulse_p = 100E-9 #(in s) width of pump pulse

        t0_pulse_p = 150E-9 #(in s) center of pump pulse
        t0_pulse_c = t0_pulse_p + tw_pulse_p + 150E-9 #(in s) center of control pulse
        t0_pulse_s = t0_pulse_c + 27E-9 + offset*1E-9 #(in s) center of signal pulse

        t_storage = 100E-9 #(in s) Storage time. Delay between write and read pulses

        mark_start = 50
        mark_stop = int(samples - samples/2)

        x = np.arange(0,samples)
        t = x/sample_rate

        "Translating time based parameters to samples"
        s0_pulse_c = np.rint(t0_pulse_c*sample_rate)
        s0_pulse_s = np.rint(t0_pulse_s*sample_rate)
        s0_pulse_p = np.rint(t0_pulse_p*sample_rate)
        s0_pulse_r = s0_pulse_c+s_storage
        s_storage = np.rint(t_storage*sample_rate)
        sw_pulse_c = np.rint(tw_pulse_c*sample_rate)
        sw_pulse_s = np.rint(tw_pulse_s*sample_rate)
        sw_pulse_p = np.rint(tw_pulse_p*sample_rate)

        "Writing pulses"
        pulse_c = AwgCtl.gaussian(x, s0_pulse_c, sw_pulse_c)+AwgCtl.gaussian(x, s0_pulse_r, sw_pulse_c)
        pulse_s = AwgCtl.gaussian(x, s0_pulse_s, sw_pulse_s)
        pulse_p = AwgCtl.supergauss(x, s0_pulse_p, sw_pulse_p, 5)

        "Writting waveforms for maximum amplitude (-1 to 1)"
        control_ch = 2*(pulse_p+pulse_c)-1 
        signal_ch = 2*(pulse_s)-1

        "Storing waveforms"
        marker1 = np.zeros(samples, dtype=int)
        marker1[mark_start:mark_stop] = np.ones(mark_stop-mark_start, dtype=int)

        return samples, control_ch, signal_ch, marker1, s0_pulse_r, s0_pulse_s
    
    def gen_ref_pulse(signal_width):
        sample_rate = 2.5E9 #(samples/s)
        samples = 5000 #(maximum 2E9 samples in memory)

        tw_pulse_s = signal_width * 1E-9 #(in s) width of signal pulse
        tw_pulse_p = 5 * tw_pulse_s #(in s) width of pump pulse
        t0 = 150e-9 + (tw_pulse_p/2) # center of pulse

        mark_start = 50
        mark_stop = int(samples - samples/2)

        x = np.arange(0,samples)
        t = x/sample_rate

        "Translating time based parameters to samples"
        s0 = np.rint(t0*sample_rate)
        sw_pulse_s = np.rint(tw_pulse_s*sample_rate)
        sw_pulse_p = np.rint(tw_pulse_p*sample_rate)

        "Writing pulses"
        pulse_s = AwgCtl.gaussian(x, s0, sw_pulse_s)
        pulse_p = AwgCtl.supergauss(x, s0, sw_pulse_p, 5)

        "Writting waveforms for maximum amplitude (-1 to 1)"
        control_ch = 2*(pulse_p)-1
        signal_ch = 2*(pulse_s)-1

        "Storing waveforms"
        marker1 = np.zeros(samples, dtype=int)
        marker1[mark_start:mark_stop] = np.ones(mark_stop-mark_start, dtype=int)

        return samples, control_ch, signal_ch, marker1, t0, tw_pulse_s

    def sendMarkerData(self, name, recordLength, markerData):
        marker_bytes = len(markerData) * 4 #Convert to number of bytes as specified by manual
        marker_header = 'wlist:waveform:marker:data "{:s}", 0, {:d}, '.format(name, recordLength, len(str(marker_bytes)), marker_bytes) #Marker header (see manual)
        ret=self.awg.write_binary_values(marker_header, markerData,datatype='B') #Send marker data as binary values
        return ret
    
    def sendWaveform(self, name, recordLength, wfmArr):
        delete_wfm = 'wlist:waveform:delete "{:s}"'.format(name) #Command to delete waveform with same name from the waveform list
        create_wfm = 'wlist:waveform:new "{:s}", {:d}'.format(name, recordLength) #Command to create waveform with this name
        wfm_bytes = len(wfmArr) * 4 #Convert to number of bytes as specified by manual
        wfm_header = 'wlist:waveform:data "{:s}", 0, {:d}, '.format(name, recordLength, len(str(wfm_bytes)), wfm_bytes) #Wfm header (see manual)
        self.awg.write(delete_wfm)
        self.awg.write(create_wfm)
        ret=self.awg.write_binary_values(wfm_header, wfmArr) #Send waveform as binary values
        return ret
    
    def loadWaveform(self, name, channelNum):
        if channelNum in [1,2]:
            return self.awg.write(f"source{channelNum}:waveform \"{name}\"")
        else:
            print("Enter valid channel number (1 or 2)")

    "Check for error reports from AW"
    def checkErrors(self):
        error = self.awg.query('system:error:all?')
        print('Status: {}'.format(error))

    def set_awg(self, samples, control_ch, signal_ch, marker1):
        "Send Waveform Data"
        self.sendWaveform("control_pulse", samples, control_ch)
        self.sendWaveform("signal_pulse", samples, signal_ch)

        "Send Marker data"
        markerData = AwgCtl.createMarkerData(marker1)
        self.sendMarkerData("control_pulse", samples, markerData)
        self.sendMarkerData("signal_pulse", samples, markerData)

        "Load waveform onto channels, turn on outputs, and begin playback"
        self.loadWaveform("control_pulse", 1)
        self.loadWaveform("signal_pulse", 2)

        #IMPORTANT: If not sending anything to a channel, need to write the corresponding output off.
        self.awg.write('output1 on')
        self.awg.write('output2 on')
        self.awg.write('output3 off')
        self.awg.write('output4 off')
        self.awg.write('awgcontrol:run:immediate') #Start run

        "Check for errors"
        self.checkErrors()
