# TBS2102B + N9310
# python v3.11.4, pyvisa v1.13.0

'''


  ┌────────────────┐     ┌────────────────┐      ┌───────────────┐
  │                │     │                │      │               │
  │  N9310A        │     │  DSO TBS       │      │   PC          │
  │                │     │                │      │               │
  │                │     │                │      │               │
  │                │     │                │      │               │
  │        RF OUT──┼─────┤► CHx           │      │               │
  │                │     │                │      │               │
  │                │     │                │      │  USB1   USB2  │
  └────────▲───────┘     └────────▲───────┘      └───┬──────┬────┘
           │                      │                  │      │
           │                      └──────────────────┘      │
           │                                                │
           └────────────────────────────────────────────────┘

'''

'''
Check bandwidth
This test checks the bandwidth of all input channels.
1. Connect the output of the leveled sine wave generator (for example, Fluke 9500) to the channel 1 input as shown:
2. Push the front-panel Default Setup button to set the instrument to the factory default settings.
3. Push the front-panel Trigger Menu button.
4. Push the Coupling bezel button, and then use the Multipurpose knob to select and then set Noise Reject (DC Low
Sensitivity).
5. Push the front-panel Trigger Menu button.
6. Push the Source bezel button and use Multipurpose knob a to select the channel being tested as the trigger source.
7. Push the Menu Off button, so you can see the screen.
8. Push the channel button (1, 2, 3, or 4) for the channel that you want to check.
9. Push the Probe Setup bezel button, and then use the Multipurpose knob to select Set to 1 X.
10. Push the front-panel Measure button, and then push the bezel button for the channel you are testing.
11. Use Multipurpose knob a to select the Peak-to-peak measurement.
12. Turn the Vertical Scale knob to set the vertical scale to 500 mV/div.
13. Turn the Horizontal Scale knob to 400 μs/div.
14. Set the leveled sine wave generator frequency to 1 kHz.
15. Set the leveled sine wave generator output level so the peak-to-peak measurement is between 2.98 V and 3.02 V.
16. Set the leveled sine wave generator frequency to:
- 100 MHz if you are checking a TBS2104 or TBS2102
- 70 MHz if you are checking a TBS2074 or TBS2072
17. Use the Horizontal Scale knob to set the instrument to 10 ns/div.
18. Check that the peak-to-peak measurement is ≥2.12 V. Enter this measurement in the test record.
19. Move the input cable to the next channel to be tested.
20. Repeat steps 3 through 19 for all input channels.
Performance verification
TBS2000 Series Specification and Performance Verification 
'''


import pyvisa as visa  # http://github.com/hgrecco/pyvisa
import numpy as np     # http://www.numpy.org/
from math import log10 #
import matplotlib.pyplot as plt
import time            #

rm = visa.ResourceManager()
print(rm.list_resources())
# Open connetion DSO
scope = rm.open_resource(rm.list_resources('?*0x0699?*::INSTR')[0]) # 0699  Tektronix, Inc.
scope.timeout = 10000 # ms
scope.encoding = 'latin_1'
scope.read_termination = '\n'
scope.write_termination = None
scope.write('*cls') # clear ESR
print(scope.query('*idn?'))
# Open connetion RFGenerator
generator = rm.open_resource(rm.list_resources('?*0x0957?*::INSTR')[0]) # 0957  Agilent Technologies, Inc.
generator.timeout = 10000 # ms
generator.encoding = 'latin_1'
generator.read_termination = '\n'
generator.write_termination = None
generator.write('*cls') # clear ESR
generator.write('*rst') # clear ESR


freq_start_khz = 5e3
freq_stop_khz =  150e3
num_samp_per_decade = 20

freq_list = np.logspace(
    start=log10(freq_start_khz), 
    stop=log10(freq_stop_khz), 
    num=num_samp_per_decade, 
    endpoint=False,
    base=10,
)
freq_list = np.append(freq_list, freq_stop_khz)  # Appending end
amp_list = np.zeros(len(freq_list))
# io config
scope.write('header 0')
scope.write('data:encdg RIBINARY')
scope.write('data:source CH1') # channel
scope.write('data:start 1') # first sample
record = int(scope.query('wfmpre:nr_pt?'))
scope.write('data:stop {}'.format(record)) # last sample
scope.write('wfmpre:byt_nr 1') # 1 byte per sample
generator.write("AMPL:CW 500 mV")
generator.write("FREQ:CW 5000 kHz")
generator.write("RFOutput:STATE ON")
time.sleep(2)



##################
## Main Area Plot
##################
# to run GUI event loop
plt.ion()
# here we are creating sub plots
fig = plt.figure(figsize=(10, 8))
ax = fig.add_subplot(111)
ax.set_xscale('log')
ax.set(xlabel='kHz', ylabel='Vpp', title='Vpp vs kHz')
ax.yaxis.label.set(rotation=0, ha='right')  # modify properties on ylabel
ax.axis(xmin=freq_start_khz,xmax=freq_stop_khz, ymin=0, ymax=4)
ax.grid(which='minor',linestyle='dotted', linewidth=1)
ax.grid(which='major',linestyle='dotted', linewidth=1)

plt.gca().axes.xaxis.set_ticklabels([])
#Plot
line,=ax.plot(freq_list,amp_list)

for index, i in enumerate(freq_list):
    command = "FREQ:CW %i kHz" % i
    #print(command)
    generator.write(command)
    time.sleep(2)
    #https://forum.tek.com/viewtopic.php?t=138685
    bin_wave = scope.query_binary_values('curve?', datatype='b', container=np.array, chunk_size = 1024**2)
    # error checking
    
    #r = int(scope.query('*esr?'))
    #print('event status register: 0b{:08b}'.format(r))
    #r = scope.query('allev?').strip()
    #print('all event messages: {}'.format(r))   
    
    vscale = float(scope.query('wfmpre:ymult?')) # volts / level
    unscaled_wave = np.array(bin_wave, dtype='double') # data type conversion
    scaled_wave=unscaled_wave * vscale
    diff=(max(scaled_wave)-min(scaled_wave))
    print('%i kHz : %2.2f' %(i,diff) )
    amp_list[index] = diff       
    line.set_ydata(amp_list)
    ax.set_title('%i kHz : %2.2f Vpp' %(i,diff)); 
    fig.canvas.draw()
    fig.canvas.flush_events()

scope.close()
generator.close()
rm.close()


import pandas as pd
from datetime import datetime
file_name = "TBS2102B_"+datetime.now().strftime("%Y%m%d%H%M%S") + ".csv"
df = pd.DataFrame({"Freq" : freq_list, "Amp" : amp_list})
df.to_csv(file_name, index=False)




# Reset generator to default values
'''
generator.write("*RST")
'''
# Set Frequency in Continuous Wave (CW) [9kHz - 3GHz]
# Receives a string including value and unit (e.g: "4.3 MHz"), or a number representing frequency in Hz
# See User's Guide / Subsystem Command Reference / Frequency Subsystem to see available units
'''
generator.write("FREQ:CW 4.3 MHz")
'''
# Set frequency sweep limits for RF ouput [9kHz - 3GHz] and enables sweeping by default
# Optionally set logarithmic scale to sweep (linear by default).
'''
generator.write("RFOutput:STATE OFF")
generator.write("FREQ:RF:START 1 MHz")
generator.write("FREQ:RF:STOP 10 MHz")
generator.write("FREQ:RF:SCALE LIN")
generator.write("FREQ:RF:SCALE LOG")
generator.write("RFOutput:STATE ON")
'''
# Set frequency sweep limits for LF values [0.020 Hz - 80kHz] and enables sweeping by default
# Receives strings including value and unit (e.g: "3 kHz"), or numbers representing frequency in Hz
# Logarithmic scale is not available for this range
'''
generator.write("LFOutput:STATE OFF")
generator.write("FREQ:RF:START 10 Hz")
generator.write("FREQ:RF:STOP 100 Hz")
generator.write("LFOutput:STATE ON")
'''
# Sets Amplitude in Continuous Wave (CW) [-127dBm to +13dBm]
# Receives a string including value and unit (e.g: "-100 dBm"), or a number representing amplitude in dBm
# See User's Guide / Subsystem Command Reference / Amplitude Subsystem to see available units and ranges
'''
generator.write("AMPL:CW 1000 mV")
'''
# Sets Amplitude Sweep range [-127dBm to +13dBm] and enables sweep by default
# Receives strings including value and unit (e.g: "-100 dBm"), or numbers representing amplitude in dBm
# See User's Guide / Subsystem Command Reference / Amplitude Subsystem to see available units and ranges
'''
generator.write("AMPL:START -10 dBm")
generator.write("AMPL:STOP 0 dBm")
generator.write("SWEEP:REPEAT SINGLE") #SINGLE or CONTINUOUS
generator.write("SWEEP:DIRECTION UP") #DOWN or UP
generator.write("SWEEP:STEP:POINTS 100")
generator.write("SWEEP:STEP:DWELL 100 ms")
generator.write("SWEEP:STRG EXT") #EXT or KEY
generator.write("SWEEP:STRG:SLOPE EXTP") #EXTP or EXTN
generator.write("TRIGGER:SSWP") #SSWP or IMMEDIATE
generator.write("SWEEP:RF:STATE ON") #ON or OFF
'''

