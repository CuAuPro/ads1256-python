import wiringpi as wp
import time
from drivers import ads1256
wp.wiringPiSetup()      # For sequential pin numbering

adc = ads1256.ADS1256(bus=1, device=1, cs_pin=2, drdy_pin=5)

adc.configure(ads1256.ADS1256_DRATE_15SPS,ads1256.ADS1256_GAIN_1, False)

##################################################
#               READING MANUAL DIFF CH0 / CH1
##################################################
adc.setChannel(0,1)
adc.waitDRDY()
val = round(adc.readCurrentChannel(),4)
print("Manual CH0/CH1: {}".format(val))

##################################################
#               READING MANUAL DIFF CH1 / CH0
##################################################
adc.setChannel(1,0)
adc.waitDRDY()
val = round(adc.readCurrentChannel(),4)
print("Manual CH1/CH0: {}".format(val))

##################################################
#               READING MANUAL CH0
##################################################
adc.setChannel(0)
adc.waitDRDY()
val = round(adc.readCurrentChannel(),4)
print("Manual CH0: {}".format(val))
##################################################
#               READING MANUAL CH0
##################################################
adc.setChannel(1)
adc.waitDRDY()
val = round(adc.readCurrentChannel(),4)
print("Manual CH1: {}".format(val))

