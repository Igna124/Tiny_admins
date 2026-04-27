set -e

as -g -o helloworld.o helloworld.s

ld --oformat binary -o helloworld.img -T link.ld helloworld.o

