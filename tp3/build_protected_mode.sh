set -e

as -g -o protected_mode.o protected_mode.s

ld --oformat binary -o protected_mode.img -T link.ld protected_mode.o

