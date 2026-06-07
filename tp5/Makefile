ARCH = arm64
CROSS_COMPILE = aarch64-linux-gnu-

KDIR = /home/user/programacion/raspberrypi/rpi-kernel

obj-m += signal-sensors.o


all:
		make -C $(KDIR) M=$(PWD) ARCH=$(ARCH) CROSS_COMPILE=$(CROSS_COMPILE) modules

clean:
		rm -f *.o *.ko *.mod.c *.mod *.o.cmd *.ko.cmd modules.order 
		rm -f .*.cmd .*.o
		rm -rf .tmp_versions
