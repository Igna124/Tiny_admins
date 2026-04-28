.code16
.text
.global _start

_start:
	cli
	xor %ax, %ax
	mov %ax, %ds
	mov %ax, %es
	sti

	mov $0x0003, %ax
	int $0x10

	mov $msg, %si
	mov $0x0e, %ah

loop:
	lodsb
	or %al, %al
	jz halt
	int $0x10
	jmp loop

halt:
	hlt
	jmp halt

msg:
	.asciz "hello world"

.word 0xaa55
