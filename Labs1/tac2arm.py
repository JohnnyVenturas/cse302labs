#! /usr/bin/env python3

# Author: Pierre-Yves Strub <pierre-yves@strub.nu>
# Mon, 26 Sep 2022 22:34:42 +0200

# --------------------------------------------------------------------
import json, sys

# --------------------------------------------------------------------
class CodeEmitter:
    def __init__(self):
        self._temps = dict()
        self._asm   = []

    def __call__(self, instr):
        opcode = instr['opcode']
        args   = instr['args'][:]

        if instr['result'] is not None:
            args.append(instr['result'])

        getattr(self, f'_emit_{opcode}')(*args)

    def _temp(self, temp):
        index = self._temps.setdefault(temp, len(self._temps))
        return f'[SP, #{8*index}]'

    def _get_asm(self, opcode, *args):
        if not args:
            return opcode
        return f'{opcode}\t{", ".join(args)}'

    def _emit(self, opcode, *args):
        self._asm.append(self._get_asm(opcode, *args))

    def _emit_const(self, ctt, dst):
        self._emit('mov', 'X2', f'#{ctt}')
        self._emit('str', 'X2', self._temp(dst))

    def _emit_copy(self, src, dst):
        self._emit('ldr', 'X2', self._temp(src))
        self._emit('str', 'X2', self._temp(dst))

    def _emit_alu2(self, opcode, op1, op2, dst):
        self._emit('ldr', 'X0', self._temp(op1))
        self._emit('ldr', 'X1', self._temp(op2))
        self._emit(opcode, 'X2', 'X0', 'X1')
        self._emit('str', 'X2', self._temp(dst))

    def _emit_add(self, op1, op2, dst):
        self._emit_alu2('add', op1, op2, dst)
        
    def _emit_sub(self, op1, op2, dst):
        self._emit_alu2('sub', op1, op2, dst)

    def _emit_mul(self, op1, op2, dst):
        self._emit_alu2('mul', op1, op2, dst)

    def _emit_div(self, op1, op2, dst):
        self._emit_alu2('sdiv', op1, op2, dst)

    def _emit_mod(self, op1, op2, dst):
        self._emit('ldr' , 'X0', self._temp(op1))
        self._emit('ldr' , 'X1', self._temp(op2))
        self._emit('sdiv', 'X2', 'X0', 'X1')
        self._emit('mul' , 'X2', 'X2', 'X1')
        self._emit('sub' , 'X2', 'X0', 'X2')
        self._emit('str' , 'X2', self._temp(dst))

    def _emit_and(self, op1, op2, dst):
        self._emit_alu2('and', op1, op2, dst)

    def _emit_or(self, op1, op2, dst):
        self._emit_alu2('orr', op1, op2, dst)

    def _emit_xor(self, op1, op2, dst):
        self._emit_alu2('eor', op1, op2, dst)

    def _emit_shl(self, op1, op2, dst):
        self._emit_alu2('lsl', op1, op2, dst)

    def _emit_shr(self, op1, op2, dst):
        self._emit_alu2('lsr', op1, op2, dst)

    def _emit_print(self, arg):
        self._emit('ldr' , 'X2', self._temp(arg))
        self._emit('stp' , 'X29', 'X30', '[SP, #-16]!')
        self._emit('str' , 'X2', '[SP, #-16]!')
        self._emit('adrp', 'X0', 'l._dformat@PAGE')
        self._emit('add' , 'X0', 'X0', 'l._dformat@PAGEOFF')
        self._emit('bl'  , '_printf')
        self._emit('add' , 'SP', 'SP', '#16')
        self._emit('ldp' , 'X29', 'X30', '[SP]', '#16')

    def __str__(self):
        return self.code()

    def code(self):
        nvars  = len(self._temps)
        nvars += nvars & 1

        aout = [
            self._get_asm('sub', 'SP', 'SP', f'#{8*nvars}')
        ] + self._asm + [
            self._get_asm('add', 'SP', 'SP', f'#{8*nvars}')
        ]

        return "\n".join(f'\t{x}' for x in aout)

# --------------------------------------------------------------------
def _main():
    if len(sys.argv)-1 != 1:
        print(f'Usage: {sys.argv[0]} [SOURCE.json]')
        exit(1)

    filename = sys.argv[1]

    with open(filename) as stream:
        tac = json.load(stream)

    main    = [x for x in tac if x['proc'] == '@main'][0]['body']
    emitter = CodeEmitter()

    for instr in main:
        emitter(instr)

    print('\t.text')
    print('\t.global\t_main')
    print('\t.align\t4')
    print()
    print('_main:')
    print('\t.cfi_startproc')
    print('\tstp\tX29, X30, [SP, #-16]!')
    print(emitter)
    print('\tldp\tX29, X30, [SP], #16')
    print('\tret')
    print('\t.cfi_endproc')
    print()
    print('\t.data')
    print('l._dformat:')
    print('\t.asciz\t"%d\\n"')

# --------------------------------------------------------------------
if __name__ == '__main__':
    _main()
