"""
MicroPython MAX30102 Optical Pulse Oximeter Driver
Provides sensor initialization and FIFO reading for Red and IR channels.
Compatible with ESP32 I2C bus.
"""

from machine import I2C
import time

class MAX30102:
    def __init__(self, i2c, address=0x57):
        self.i2c = i2c
        self.addr = address
        self.setup_sensor()

    def _write_reg(self, reg, value):
        self.i2c.writeto_mem(self.addr, reg, bytes([value]))

    def _read_reg(self, reg, nbytes=1):
        return self.i2c.readfrom_mem(self.addr, reg, nbytes)

    def setup_sensor(self):
        # 1. Reset sensor
        self._write_reg(0x09, 0x40)
        time.sleep_ms(50)

        # 2. FIFO Configuration: SMP_AVE=4 (average 4 samples), FIFO_ROLLOVER_EN=1
        self._write_reg(0x08, 0x5F)

        # 3. Mode Configuration: SpO2 Mode (0x03) = Red + IR LEDs active
        self._write_reg(0x09, 0x03)

        # 4. SpO2 Configuration: SPO2_ADC_RGE=4096nA, SPO2_SR=100Hz, LED_PW=411us (18-bit)
        self._write_reg(0x0A, 0x27)

        # 5. LED Pulse Amplitude (current): ~7.2mA for RED, ~7.2mA for IR
        self._write_reg(0x0C, 0x24) # RED LED
        self._write_reg(0x0D, 0x24) # IR LED

        # 6. Reset FIFO pointers
        self._write_reg(0x04, 0x00) # FIFO Write Pointer
        self._write_reg(0x05, 0x00) # Overflow Counter
        self._write_reg(0x06, 0x00) # FIFO Read Pointer

    def read_fifo(self):
        """
        Reads 6 bytes from the FIFO data register (0x07).
        Returns (red, ir) as integer values.
        """
        try:
            data = self.i2c.readfrom_mem(self.addr, 0x07, 6)
            red = ((data[0] << 16) | (data[1] << 8) | data[2]) & 0x03FFFF
            ir  = ((data[3] << 16) | (data[4] << 8) | data[5]) & 0x03FFFF
            return red, ir
        except Exception:
            return 0, 0
