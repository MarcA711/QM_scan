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
import matplotlib.pyplot as plt
import AWGfun
import pulse_gen as gen

# Set up VISA instrument object
rm = visa.ResourceManager('@py')
awg = rm.open_resource('TCPIP0::141.20.45.148::inst0::INSTR')
awg.timeout = 10000 #float('+inf') #(in ms)
print('Connected to ', awg.query('*idn?'))

#%%
"Send Waveform Data"
#AWGFunc.sendWaveform(awg, name, numSamples, wfm_arr)
AWGfun.sendWaveform(awg, gen.name_control, gen.samples, gen.control_ch)
AWGfun.sendWaveform(awg, gen.name_signal, gen.samples, gen.signal_ch)

"Send Marker data"
#AWGFunc.sendMarkerData(awg, name, numSamples, markerData)
markerData = AWGfun.createMarkerData(gen.marker1)
AWGfun.sendMarkerData(awg, gen.name_control, gen.samples, markerData)
AWGfun.sendMarkerData(awg, gen.name_signal, gen.samples, markerData)

"Load waveform onto channels, turn on outputs, and begin playback"
# channelNum = 1
# AWGfun.loadWaveform(awg, name, channelNum)
AWGfun.loadWaveform(awg, gen.name_control, 1)
AWGfun.loadWaveform(awg, gen.name_signal, 2)

#IMPORTANT: If not sending anything to a channel, need to write the corresponding output off.
awg.write('output1 on')
awg.write('output2 on')
awg.write('output3 off')
awg.write('output4 off')
awg.write('awgcontrol:run:immediate') #Start run

"Check for errors"
AWGfun.checkErrors(awg)

awg.close()

"Plot and save waveforms"
gen.plot_sequence()
gen.save_wfm()










# -*- coding: utf-8 -*-
"""
Created on Fri Aug 26 10:07:02 2022

Create waveforms usable by the Tektronix AWG5204.
Two waveforms to be used as control and signal for the Quantum memory.

@author: Esteban Gomez-Lopez
AG Nanooptik
Institut fur Physik
Humboldt-Universitat zu Berlin
"""

import numpy as np
import matplotlib.pyplot as plt
import AWGfun

sample_rate = 2.5E9 #(samples/s)
samples = 5000 #(maximum 2E9 samples in memory)

tw_pulse_c = 15E-9 #(in s) width of control pulse
tw_pulse_s = 10E-9 #(in s) width of signal pulse
tw_pulse_p = 15E-9 #(in s) width of pump pulse

t0_pulse_p = 150E-9 #(in s) center of pump pulse
t0_pulse_c = t0_pulse_p + tw_pulse_p + 150E-9 #(in s) center of control pulse
t0_pulse_s = t0_pulse_c + 27E-9 #(in s) center of signal pulse

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
output = np.zeros([3,samples])
output_ch = np.zeros([2,5,samples])
k = (pulse_c,pulse_s,pulse_p)
k_ch = (control_ch,signal_ch)
marker1 = np.zeros(samples, dtype=int)
marker1[mark_start:mark_stop] = np.ones(mark_stop-mark_start, dtype=int)
for i in range(0,3):
    output[i] = k[i]

for i in range(0,2):
    output_ch[i,0] = k_ch[i]
    output_ch[i,1:5] = marker1

"Naming waveforms"
tc_int = int(np.rint(tw_pulse_c*1E9))
tp_int = int(np.rint(tw_pulse_p*1E9))
ts_int = int(np.rint(tw_pulse_s*1E9))
tstorage_int = int(np.rint(t_storage*1E9))

name_control = 'control_ch_P{}ns_C{}ns_storage{}ns'.format(tp_int,tc_int,tstorage_int)
name_signal = 'signal_ch_S{}ns'.format(ts_int)

"Plotting pulse sequence"
def plot_sequence():
    plt.close('all')
    fig,axs = plt.subplots(2,1)
    [axs[0].plot(t*1E9,output[i]) for i in range(0,3)]
    [axs[1].plot(x,output_ch[i,0]) for i in range(0,2)]
    axs[1].plot(x,output_ch[0,1])
    axs[0].set_xlabel('Time [ns]')
    axs[1].set_xlabel('Samples')
    [axs[i].set_ylabel('Norm. intensity') for i in range(0,2)]
    axs[0].legend(['Control','Signal','Pump'])
    axs[1].legend(['Control channel','Signal channel','Marker state'])

"Saving pulses as .txt file"
def save_wfm():
    np.savetxt(('Saved waveforms\\'+name_control+'.txt'), output_ch[0].transpose(), 
                delimiter=',',fmt=['%f','%d','%d','%d','%d'])  
    
    np.savetxt(('Saved waveforms\\'+name_signal+'.txt'), output_ch[1].transpose(), 
                delimiter=',', fmt=['%f','%d','%d','%d','%d']) # , fmt=['%f']
    















# -*- coding: utf-8 -*-
"""
Created on Thu May 30 13:03:28 2024

Test script to minimize the BIAS of the control and signal EOMs for Quantum Memory measurements 
using same powermeter PM16-120

@author: QD-Lab
"""

import QM_lib_v4 as qm
import time

mode = ['min','max']
run = mode[0] #min to minimize BIAS, max to maximize them

v1 = -0.45 #Signal EOM BIAS
v2 = 1.6 #Control EOM BIAS
v_step = 0.005 #voltage steps of the AFG
long_iter = 50

factor_pr_pt = 264.46 #conversion from reflected to transmitted power of control beam at PBS

try: 
    #Initializing AFG3102 for BIAS control and setting it to DC mode
    afg = qm.AFG(afg_ip = 'TCPIP::141.20.46.169::INSTR')
    afg.set_ch1(v1)
    afg.set_ch2(v2)
    
    #Initializing and assigning variables to elliptec shutters 
    print('Connecting to Elliptec shutters...')
    shutters = qm.shutters(com_s = 'COM4',com_c = 'COM13')
    shsignal = shutters.shs()
    shcontrol = shutters.shc()
    
    #Initializing PM16-120
    print('Connecting to PM16-120...')
    pms = qm.pm160(address = 'USB0::4883::32891::230105519::0::INSTR')
    print('Signal monitor connected')
    pmc = qm.pm160(address = 'USB0::4883::32891::230105520::0::INSTR')
    print('Control monitor connected')
    
    if run == 'min':
        #Minimizer of signal BIAS
        afg_min = qm.afg_bias(afg,pms,pmc) #call for afg, ph and pm objects
        shsignal.open()
        shcontrol.close()
        time.sleep(2)
        afg_min1 = afg_min.bias_min(ch = 1, v1 = v1, v_step=v_step, max_iter = long_iter)
        
        #Minimizer of control BIAS
        shsignal.close()
        shcontrol.open()
        time.sleep(2)
        afg_min2 = afg_min.bias_min(ch = 2, v2 = v2, v_step=v_step, max_iter = long_iter)
        
        shsignal.open()
        shcontrol.open()
        
    if run == 'max':
        #Maximizer of signal BIAS
        afg_max = qm.afg_bias(afg,pms,pmc) #call for afg, ph and pm objects
        shsignal.open()
        shcontrol.close()
        time.sleep(2)
        afg_max1 = afg_max.bias_max(ch = 1, v1 = v1, v_step=v_step*2, max_iter = long_iter)
        
        #Maximizer of control BIAS
        shsignal.close()
        shcontrol.open()
        time.sleep(2)
        afg_max2 = afg_max.bias_max(ch = 2, v2 = v2, v_step=v_step*2, max_iter = long_iter)
        
        shsignal.close()
        shcontrol.open()
        
        pt_uW = afg_max2[1] * factor_pr_pt 
        pt_mw = pt_uW/1000
        print('Control power on transmitted path P_t = {:.3f} mW'.format(pt_mw))

        shsignal.open()
        shcontrol.open()
        
except Exception as e:
    print(f'\nAn exception occurred: {e}')

finally: #execute even if exception is not caught
#%%
    print("\nClosing connection to devices...")
    #Ending connections    
    if 'shutters' in locals():
        shutters.disconnect() #closing connection to elliptec shutters
    if 'afg' in locals():
        afg.close_device() #Closing connection to AFG3102 
    if 'pms' in locals():
        pms.close() #Closing connection to signal PM160  
    if 'pmc' in locals():
        pmc.close() #Closing connection to control PM160  
 




