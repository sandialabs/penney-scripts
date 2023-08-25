# Additional Makefile with external tools
# Include in main makefile with 
# -include maketools

TELF=$(BUILD_DIR)/$(TARGET).elf
TBIN=$(BUILD_DIR)/$(TARGET).bin

# If not using a board with a board config file, specify the openocd target and interface files
OPENOCD_TARGET_FILE=stm32wbx.cfg
OPENOCD_INTERFACE_FILE=stlink.cfg
OPENOCD_TRANSPORT=jtag

# CTAGS_PATH should either be defined in the environment or should be empty
# in which case it is assumed to be on the path
CTAGS=$(CTAGS_PATH)\ctags

# ST utility names
STLINK=ST-LINK_CLI
STPROG=STM32_Programmer_CLI

# OTA Application is pre-compiled binary supplied by ST
CUBE_REPO_DIR=C:\Users\kpenney\STM32Cube
OTA_BINARY_DIR=$(CUBE_REPO_DIR)/Repository/STM32Cube_FW_WB_V1.12.1/Projects/P-NUCLEO-WB55.Nucleo/Applications/BLE/BLE_Ota\Binary
OTA_BINARY_FILE=$(OTA_BINARY_DIR)/BLE_Ota_reference.hex

.PHONY: openocd
openocd: $(TELF)
	openocd -s $(OPENOCD_SCRIPTS) -f interface/$(OPENOCD_INTERFACE_FILE) -f target/$(OPENOCD_TARGET_FILE)

.PHONY: flash
flash: $(TELF)
	openocd -s $(OPENOCD_SCRIPTS) -f interface/$(OPENOCD_INTERFACE_FILE) -f target/$(OPENOCD_TARGET_FILE)\
					-c "program $(TELF) verify reset exit"

.PHONY: stprog_flash
stprog_flash:
	$(STPROG) -c port=SWD reset=HWrst -d $(TELF) -v -rst

.PHONY: load
load:
	$(STPROG) -c port=SWD reset=Hwrst -d $(TBIN) 0x08007000 -v

.PHONY: load_ota
load_ota:
	$(STPROG) -c port=SWD reset=Hwrst -d $(OTA_BINARY_FILE) -v

.PHONY: usb_flash
usb_flash:
	$(STPROG) -c port=usb1 -d $(TELF) -v

.PHONY: reset
reset:
	$(STPROG) -c port=SWD reset=HWrst -rst

.PHONY: stlink_flash
stlink_flash: $(TBIN)
	$(STLINK) -c -P $(TBIN)

.PHONY: tags
tags:
	$(CTAGS) -R
