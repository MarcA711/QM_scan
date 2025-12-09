from snAPI.Main import *
import matplotlib.pyplot as plt

sn = snAPI()
sn.getDevice()

sn.initDevice(MeasMode.Histogram)
sn.loadIniConfig("./MH.ini")

sn.histogram.measure(acqTime=1000, waitFinished=True, savePTU=True)
data, bins = sn.histogram.getData()

if len(data):
    plt.clf()
    plt.plot(bins, data[0], linewidth=2.0, label='sync')
    for c in range(1, 1+sn.deviceConfig["NumChans"]):
        plt.plot(bins, data[c], linewidth=2.0, label=f'chan{c}')
    plt.xlabel('Time [ps]')
    plt.ylabel('Counts', )
    plt.legend()
    plt.title("Counts / Time")
    plt.pause(0.01)

plt.show(block=True)