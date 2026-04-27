.code16

.equ CODE_SEG, 0x08
.equ DATA_SEG, 0x10

start:

    int $0x10

    cli                     # disable interrupts
    lgdt gdt_descriptor     # load GDT

    movl %cr0, %eax         # load cr0 in eax
    orl  $0x1, %eax         # write 1 to PE
    movl %eax, %cr0         # write back to cr0

    ljmp $CODE_SEG, $protected_mode

gdt_start:
    .quad 0x0000000000000000    # first segment invalid
    .quad 0x00CF9A000000FFFF    # code segment, 4gb, ring 0, executable, readable
    .quad 0x00CF92000000FFFF    # data segment, 4gb, ring 0, read-only
gdt_end:

gdt_descriptor:
    .word gdt_end - gdt_start - 1   # size
    .long gdt_start                 # base

.code32
protected_mode:
    movw $0x10, %ax                 # load ax with the data selector
    movw %ax, %ds                   # data segment
    movw %ax, %es                   # extra segment
    movw %ax, %fs                   # 
    movw %ax, %gs                   # general purpose segment
    movw %ax, %ss                   # stack segment
                                    # set all segment selectors to the data segment in protected mode

# ----------------- PRINT STRING ----------------------------------

    movl $0xb8000, %edi 
    movl $1000, %ecx
    movb $0x0F, %ah                 # clear VGA buffer for BIOS banners
    movb $0x20, %al
clear_loop:
    stosw
    loop clear_loop



    movl $0xb8000, %edi             # load edi with VGA buffer 
    movl $string,  %esi             # load esi with the string to print

    movb $0x0A, %ah                 # set text properties in higher byte of EAX lower half (AL)

print_loop:
    lodsb                           # load the character in lower byte of AL
    testb %al, %al                  # test if character in AL is zero

    jz done                         # if character is zero jump to done
    stosw                           # store character and atributes in the position marked by EDI
    jmp print_loop                  # repeat for next character



done:
halt:
    hlt

string:
    .asciz "Tiny_Admins"
