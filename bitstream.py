from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional
import os.path
from pathlib import Path
import pexpect
import functools
import sys
from functools import cached_property

from piradip.vivado.bd import *

class FR3TB_Capture(BD):
    board_name = "FR3_TB"
    bitstream_name = "FR3_TB_NRT"
    
    def create_gpio(self):
        print("Creating GPIO...")
        
        self.gpio = GPIO(self, "pl_gpio")
        self.slice32 = Slice32(self, "gpio_slice", None)
        
        self.axi_interconnect.aximm.connect(self.gpio.pins["S_AXI"])
        
        self.connect(self.gpio.pins["gpio_io_o"], self.slice32.pins["din"])

        self.RX_EN_LDO = self.reexport(self.slice32.pins["dout0"])
        self.RX_EN_LDO.set_phys(RFMC.ADC.IO_08.Ball, "LVCMOS18")
        
        self.RX_SW_ENb = self.reexport(self.slice32.pins["dout1"])
        self.RX_SW_ENb.set_phys(RFMC.ADC.IO_12.Ball, "LVCMOS18")

        self.RX_SW_CTRL = self.reexport(self.slice32.pins["dout2"])
        self.RX_SW_CTRL.set_phys(RFMC.ADC.IO_13.Ball, "LVCMOS18")

        self.EN_HF_LDO = self.reexport(self.slice32.pins["dout3"])
        self.EN_HF_LDO.set_phys(RFMC.ADC.IO_14.Ball, "LVCMOS18")

        self.TX_EN_LDO = self.reexport(self.slice32.pins["dout4"])
        self.TX_EN_LDO.set_phys(RFMC.DAC.IO_00.Ball, "LVCMOS18")
                
    def __init__(self, t, name):
        super().__init__(t, name)


        print("Creating Zynq UltraScale(TM) Processing System cell...")
                
        self.ps = Zynq_US_PS(self, "ps")
        
        self.ps.setup_aximm()

        print("Creating AXI Interconnect...")

        self.axi_interconnect = AXIInterconnect(self, "axi_interconnect",
                                                num_subordinates=2, num_managers=3,
                                                global_clock=self.ps.aximm_clocks[0],
                                                global_reset=self.ps.aximm_clocks[0].assoc_resetn)

        self.ps.pl_clk[0].connect(self.axi_interconnect.pins["ACLK"])
        self.ps.pl_clk[0].assoc_resetn.connect(self.axi_interconnect.pins["ARESETN"])
        
        self.axi_interconnect.pins["S00_AXI"].connect(self.ps.pins["M_AXI_HPM0_FPD"])
        self.axi_interconnect.pins["S01_AXI"].connect(self.ps.pins["M_AXI_HPM1_FPD"])
                
        self.create_gpio()
        
        print("Creating SPI...")
        use_piradspi = False
        
        self.axi_spi = AXI_SPI(self, "spi", { "CONFIG.C_NUM_SS_BITS": 5, "CONFIG.Multiples16": 2 })

        self.axi_spi.pins["ext_spi_clk"].connect(self.ps.pl_clk[0])
            
        self.axi_interconnect.aximm.connect(self.axi_spi.pins["AXI_LITE"])

        self.mosi = self.reexport(self.axi_spi.pins["io0_o"])
        self.mosi.set_phys(RFMC.ADC.IO_01.Ball, "LVCMOS18")

        self.sclk = self.reexport(self.axi_spi.pins["sck_o"])
        self.sclk.set_phys(RFMC.ADC.IO_02.Ball, "LVCMOS18")

        self.csn_slice = Slice8(self, "csn_slice", None)

        self.connect(self.axi_spi.pins["ss_o"], self.csn_slice.pins["din"])
        
        self.MAX_EN = self.reexport(self.csn_slice.pins["dout0"], "MAX_EN")
        self.MAX_EN.set_phys(RFMC.ADC.IO_04.Ball, "LVCMOS18")
    
        self.LMX_LF_EN = self.reexport(self.csn_slice.pins["dout1"], "LMX_LF_EN")
        self.LMX_LF_EN.set_phys(RFMC.ADC.IO_05.Ball, "LVCMOS18")

        self.LMX_HF_EN = self.reexport(self.csn_slice.pins["dout2"], "LMX_HF_EN")
        self.LMX_HF_EN.set_phys(RFMC.ADC.IO_06.Ball, "LVCMOS18")

        self.ADRF6520_EN = self.reexport(self.csn_slice.pins["dout3"], "ADRF6520_EN")
        self.ADRF6520_EN.set_phys(RFMC.ADC.IO_10.Ball, "LVCMOS18")

        self.LTC5594_EN = self.reexport(self.csn_slice.pins["dout4"], "LTC5594_EN")
        self.LTC5594_EN.set_phys(RFMC.DAC.IO_04.Ball, "LVCMOS18")
        
        

        
        self.capture = SampleCapture(self, NCOFreq="1.0")

        for p in self.capture.external_interfaces:
            port = self.reexport(p)
            if p in self.capture.external_clocks:
                port.set_property_list([("CONFIG.FREQ_HZ", "4000000000.0")])

                
        #self.capture.dump_pins()

        self.axi_interconnect.aximm.connect(self.capture.pins["S00_AXI"])
        self.ps.pl_resetn[0].connect(self.capture.pins["ext_reset_in"])

        self.ps.connect_interrupts()

bitstream_definition= FR3TB_Capture
