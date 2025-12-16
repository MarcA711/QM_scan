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
import AWGfun

class AwgCtl():
    sample_rate = 2.5E9 #(samples/s)
    samples = 5000 #(maximum 2E9 samples in memory)

    def __init__(self):
        # Set up VISA instrument object
        rm = visa.ResourceManager('@py')
        self.awg = rm.open_resource('TCPIP0::141.20.45.148::inst0::INSTR')
        self.awg.timeout = 10000 #float('+inf') #(in ms)
        print('Connected to ', self.awg.query('*idn?'))

    def __del__(self):
        self.awg.close()

    def gen_pulse(self, write_width, signal_width, offset):
        sample_rate = 2.5E9 #(samples/s)
        samples = 5000 #(maximum 2E9 samples in memory)

        tw_pulse_c = write_width * 1E-9 #(in s) width of control pulse
        tw_pulse_s = signal_width * 1E-9 #(in s) width of signal pulse
        tw_pulse_p = 15E-9 #(in s) width of pump pulse

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
        s_storage = np.rint(t_storage*sample_rate)
        sw_pulse_c = np.rint(tw_pulse_c*sample_rate)
        sw_pulse_s = np.rint(tw_pulse_s*sample_rate)
        sw_pulse_p = np.rint(tw_pulse_p*sample_rate)

        "Writing pulses"
        pulse_c = AWGfun.gaussian(x, s0_pulse_c, sw_pulse_c)+AWGfun.gaussian(x, s0_pulse_c+s_storage, sw_pulse_c)
        pulse_s = AWGfun.gaussian(x, s0_pulse_s, sw_pulse_s)
        pulse_p = AWGfun.supergauss(x, s0_pulse_p, sw_pulse_p, 5)

        "Writting waveforms for maximum amplitude (-1 to 1)"
        control_ch = 2*(pulse_p+pulse_c)-1 
        signal_ch = 2*(pulse_s)-1

        "Storing waveforms"
        marker1 = np.zeros(samples, dtype=int)
        marker1[mark_start:mark_stop] = np.ones(mark_stop-mark_start, dtype=int)

        "Naming waveforms"
        tc_int = int(np.rint(tw_pulse_c*1E9))
        tp_int = int(np.rint(tw_pulse_p*1E9))
        ts_int = int(np.rint(tw_pulse_s*1E9))
        tstorage_int = int(np.rint(t_storage*1E9))

        name_control = 'control_ch_P{}ns_C{}ns_storage{}ns'.format(tp_int,tc_int,tstorage_int)
        name_signal = 'signal_ch_S{}ns'.format(ts_int)

        return samples, name_control, name_signal, control_ch, signal_ch, marker1

    def set_awg(self, awg, write_width, signal_width, offset):
        "Generate Pulses"
        samples, name_control, name_signal, control_ch, signal_ch, marker1 = self.gen_pulse(write_width, signal_width, offset)

        "Send Waveform Data"
        #AWGFunc.sendWaveform(awg, name, numSamples, wfm_arr)
        AWGfun.sendWaveform(awg, name_control, samples, control_ch)
        AWGfun.sendWaveform(awg, name_signal, samples, signal_ch)

        "Send Marker data"
        #AWGFunc.sendMarkerData(awg, name, numSamples, markerData)
        markerData = AWGfun.createMarkerData(marker1)
        AWGfun.sendMarkerData(awg, name_control, samples, markerData)
        AWGfun.sendMarkerData(awg, name_signal, samples, markerData)

        "Load waveform onto channels, turn on outputs, and begin playback"
        # channelNum = 1
        # AWGfun.loadWaveform(awg, name, channelNum)
        AWGfun.loadWaveform(awg, name_control, 1)
        AWGfun.loadWaveform(awg, name_signal, 2)

        #IMPORTANT: If not sending anything to a channel, need to write the corresponding output off.
        awg.write('output1 on')
        awg.write('output2 on')
        awg.write('output3 off')
        awg.write('output4 off')
        awg.write('awgcontrol:run:immediate') #Start run

        "Check for errors"
        AWGfun.checkErrors(awg)
