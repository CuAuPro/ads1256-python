import spidev
import wiringpi as wp
import time


# ADS1256 general
NR_BITS = 24

# ADS1256 Register
STATUS = 0x00
MUX = 0x01
ADCON = 0x02
DRATE = 0x03
IO = 0x04
OFC0 = 0x05
OFC1 = 0x06
OFC2 = 0x07
FSC0 = 0x08
FSC1 = 0x09
FSC2 = 0x0A

# ADS1256 Command
WAKEUP = 0x00
RDATA = 0x01
RDATAC = 0x03
SDATAC = 0x0f
RREG = 0x10
WREG = 0x50
SELFCAL = 0xF0
SELFOCAL = 0xF1
SELFGCAL = 0xF2
SYSOCAL = 0xF3
SYSGCAL = 0xF4
SYNC = 0xFC
STANDBY = 0xFD
RESET = 0xFE

# define multiplexer codes
ADS1256_MUXP_AIN0 = 0x00
ADS1256_MUXP_AIN1 = 0x10
ADS1256_MUXP_AIN2 = 0x20
ADS1256_MUXP_AIN3 = 0x30
ADS1256_MUXP_AIN4 = 0x40
ADS1256_MUXP_AIN5 = 0x50
ADS1256_MUXP_AIN6 = 0x60
ADS1256_MUXP_AIN7 = 0x70
ADS1256_MUXP_AINCOM = 0x80

ADS1256_MUXN_AIN0 = 0x00
ADS1256_MUXN_AIN1 = 0x01
ADS1256_MUXN_AIN2 = 0x02
ADS1256_MUXN_AIN3 = 0x03
ADS1256_MUXN_AIN4 = 0x04
ADS1256_MUXN_AIN5 = 0x05
ADS1256_MUXN_AIN6 = 0x06
ADS1256_MUXN_AIN7 = 0x07
ADS1256_MUXN_AINCOM = 0x08

# define gain codes
ADS1256_GAIN_1 = 0x00
ADS1256_GAIN_2 = 0x01
ADS1256_GAIN_4 = 0x02
ADS1256_GAIN_8 = 0x03
ADS1256_GAIN_16 = 0x04
ADS1256_GAIN_32 = 0x05
ADS1256_GAIN_64 = 0x06

# define drate codes
"""
        NOTE : 	Data Rate vary depending on crystal frequency. Data rates
   listed below assumes the crystal frequency is 7.68Mhz
                for other frequency consult the datasheet.
"""

ADS1256_DRATE_30000SPS = 0xF0
ADS1256_DRATE_15000SPS = 0xE0
ADS1256_DRATE_7500SPS = 0xD0
ADS1256_DRATE_3750SPS = 0xC0
ADS1256_DRATE_2000SPS = 0xB0
ADS1256_DRATE_1000SPS = 0xA1
ADS1256_DRATE_500SPS = 0x92
ADS1256_DRATE_100SPS = 0x82
ADS1256_DRATE_60SPS = 0x72
ADS1256_DRATE_50SPS = 0x63
ADS1256_DRATE_30SPS = 0x53
ADS1256_DRATE_25SPS = 0x43
ADS1256_DRATE_15SPS = 0x33
ADS1256_DRATE_10SPS = 0x23
ADS1256_DRATE_5SPS = 0x13
ADS1256_DRATE_2_5SPS = 0x03


class ADS1256:
    def __init__(self, bus=1, device=1, cs_pin=2, drdy_pin=None, vref=2.5, freq=768000):
        self.spi = spidev.SpiDev()
        self.spi.open(bus, device)
        self.cs_pin = cs_pin
        self.drdy_pin = drdy_pin  
        self.tau = 0.1/freq    # Refer to Timing Characteristics
           
        wp.wiringPiSetup()
        # Set CS as output
        wp.pinMode(self.cs_pin, wp.GPIO.OUTPUT)
        if self.drdy_pin is not None:
            # Set DRDY as input
            wp.pinMode(self.drdy_pin, wp.GPIO.INPUT)

        self.spi.mode = 0b01
        self.spi.max_speed_hz = freq
        #self.spi.cshigh = True
        #self.spi.lsbfirst = False
        #self.spi.no_cs = False
        #self.spi.threewire = False
        self.spi.bits_per_word = 8
        #self.spi.loop = False
        
        self.nr_channels = 8
        # Default conversion factor
        self.conversionFactor = 1.0   
        self.vref = vref
        self.feature = 0
        self.bits = NR_BITS

    def __del__(self):
        self.spi.close()
        return
    
    def writeRegister(self, reg, wdata):
        self.CSON()
        self.spi.xfer2([WREG | reg, 0x00, wdata])
        time.sleep(4*self.tau)  # t11 delay (4*tCLKIN) after WREG command
        self.CSOFF()
        return
    
    def readRegister(self, reg):
        self.CSON()
        self.spi.xfer2([RREG | reg, 0x00])
        time.sleep(50*self.tau)  # t6 delay (50*tCLKIN)
        readValue = self.spi.xfer2([0])[0]
        time.sleep(4*self.tau)  # t11 delay
        self.CSOFF()
        return readValue

    def sendCommand(self, reg):
        self.CSON()
        self.waitDRDY()
        self.spi.xfer2([reg])
        time.sleep(4*self.tau)  # t11
        self.CSOFF()
        return
    
    def setConversionFactor(self, val):
        self._conversionFactor = val
        return
    
    def readTest(self):
        self.CSON()
        self.spi.xfer2([RDATA])  # RDATA command
        time.sleep(50*self.tau)  # t6 delay
        data = self.spi.xfer2([WAKEUP, WAKEUP, WAKEUP])  # read 24-bit data
        self.CSOFF()
        return data

    def readCurrentChannel(self):
        self.CSON()
        self.spi.xfer2([RDATA])  # RDATA command
        time.sleep(50*self.tau)  # t6 delay
        adsCode = self.read_float32()
        self.CSOFF()
        result = ((adsCode / 0x7FFFFF) * ((2 * self.vref) / self.pga)) * self.conversionFactor
        return result

    # Call this ONLY after RDATA command
    def read_uint24(self):
        self.CSON()
        data = self.spi.xfer2([WAKEUP, WAKEUP, WAKEUP])  # read 24-bit data
        self.CSOFF()

        # Combine all 3-bytes to 24-bit data using byte shifting.
        value = (data[0] << 16) + (data[1] << 8) + data[2]
        return value

    # Call this ONLY after RDATA command
    def read_int32(self):
        value = self.read_uint24()

        # compute the 2's complement of int value val
        if (value & (1 << (self.bits - 1))) != 0: # if sign bit is set e.g., 8bit: 128-255
            value = value - (1 << self.bits)  

        return value
    
    # Call this ONLY after RDATA command
    def read_float32(self):
        value = self.read_int32()
        return float(value)

    def setChannel(self, ch_p, ch_n=-1):

        muxp = {
            0: ADS1256_MUXP_AIN0,
            1: ADS1256_MUXP_AIN1,
            2: ADS1256_MUXP_AIN2,
            3: ADS1256_MUXP_AIN3,
            4: ADS1256_MUXP_AIN4,
            5: ADS1256_MUXP_AIN5,
            6: ADS1256_MUXP_AIN6,
            7: ADS1256_MUXP_AIN7,
        }.get(ch_p, ADS1256_MUXP_AINCOM)

        muxn = {
            0: ADS1256_MUXN_AIN0,
            1: ADS1256_MUXN_AIN1,
            2: ADS1256_MUXN_AIN2,
            3: ADS1256_MUXN_AIN3,
            4: ADS1256_MUXN_AIN4,
            5: ADS1256_MUXN_AIN5,
            6: ADS1256_MUXN_AIN6,
            7: ADS1256_MUXN_AIN7,
        }.get(ch_n, ADS1256_MUXN_AINCOM)

        mux_channel = muxp | muxn

        self.CSON()
        self.writeRegister(MUX, mux_channel)
        self.sendCommand(SYNC)
        self.sendCommand(WAKEUP)
        self.CSOFF()
        return
    
    def configure(self, drate, gain, buffenable):
        self.pga = 1 << gain
        self.sendCommand(RESET)
        self.sendCommand(SDATAC) # send out SDATAC command to stop continous reading mode
        self.writeRegister(DRATE, drate)
        bytemask = 0b00000111
        adcon = self.readRegister(ADCON)
        byte2send = (adcon & ~bytemask) | gain
        self.writeRegister(ADCON, byte2send)
        if buffenable:
            status = self.readRegister(STATUS)
            status |= 1 << 1
            self.writeRegister(STATUS, status)
        self.sendCommand(SELFCAL) # perform self calibration
        self.waitDRDY() # wait ADS1256 to settle after self calibration
        return
    
    def CSON(self):
        wp.digitalWrite(self.cs_pin, wp.GPIO.LOW)
        return
    
    def CSOFF(self):
        wp.digitalWrite(self.cs_pin, wp.GPIO.HIGH)
        return
    
    def waitDRDY(self):
        if self.drdy_pin is not None: # Hardware trigger
            while wp.digitalRead(self.drdy_pin) != 0:
                pass
        else: # Software trigger
            while self.readRegister(STATUS) & (1<<0) != 0:
                pass
        return

