from ast import List
import builtIns
from context import Context, SymbolTable
from llvmlite import ir, binding
target_data = binding.create_target_data("e S0")


def llvm_to_flotype(value):
    llvm_type = value.type
    if isinstance(llvm_type, ir.IntType):
        return (
            FloBool(value)
            if llvm_type.width == FloBool.llvmtype.width
            else FloInt(value)
        )
    if isinstance(llvm_type, ir.DoubleType):
        return FloFloat(value)

    elif llvm_type == FloStr.llvmtype:
        return FloStr(value)
    elif isinstance(llvm_type, ir.VoidType):
        return FloVoid()
    else:
        raise Exception(f"Type Not handled {llvm_type}")


def flotype_to_llvm(type):
    if isinstance(type, FloArray):
        return type.elm_type.llvmtype.as_pointer()
    return type.llvmtype


def str_to_flotype(str):
    if str == "int":
        return FloInt
    if str == "float":
        return FloFloat
    elif str == "str":
        return FloStr
    elif str == "bool":
        return FloBool
    elif str == "void":
        return FloVoid


class FloInt:
    llvmtype = ir.IntType(32)
    print_fmt = "%li"

    def __init__(self, value: int | ir.Constant):
        self.size = FloInt.llvmtype.width
        if isinstance(value, int):
            self.value = ir.Constant(FloInt.llvmtype, int(value))
        else:
            self.value = value
        self.i = 0

    @staticmethod
    def one():
        return FloInt(ir.Constant(FloInt.llvmtype, 1))

    @staticmethod
    def zero():
        return FloInt(ir.Constant(FloInt.llvmtype, 0))

    @staticmethod
    def default_llvm_val():
        return FloInt.zero().value

    def print_val(self, _):
        return self.value

    def toFloat(self, builder: ir.IRBuilder):
        return FloFloat(builder.sitofp(self.value, FloFloat.llvmtype))

    def add(self, builder: ir.IRBuilder, num):
        return FloInt(builder.add(self.value, num.value))

    def sub(self, builder: ir.IRBuilder, num):
        return FloInt(builder.sub(self.value, num.value))

    def mul(self, builder: ir.IRBuilder, num):
        return FloInt(builder.mul(self.value, num.value))

    def div(self, builder: ir.IRBuilder, num):
        return FloFloat(builder.sdiv(self.value, num.value))

    def mod(self, builder: ir.IRBuilder, num):
        return FloInt(builder.srem(self.value, num.value))

    def cmp(self, builder: ir.IRBuilder, op, num):
        if not isinstance(num, FloInt):
            return FloBool.false()
        return FloBool(builder.icmp_signed(op, self.value, num.value))

    def neg(self):
        self.value = self.value.neg()
        return self

    def pow(self, builder: ir.IRBuilder, num):
        fv = self.castTo(builder, FloFloat).pow(
            builder, num.castTo(builder, FloFloat))
        return fv

    def sl(self, builder: ir.IRBuilder, num):
        return FloInt(builder.shl(self.value, num.value))

    def sr(self, builder: ir.IRBuilder, num):
        return FloInt(builder.ashr(self.value, num.value))

    def or_(self, builder: ir.IRBuilder, num):
        return FloInt(builder.or_(self.value, num.value))

    def and_(self, builder: ir.IRBuilder, num):
        return FloInt(builder.and_(self.value, num.value))

    def not_(self, builder: ir.IRBuilder):
        return FloInt(builder.not_(self.value))

    def xor(self, builder: ir.IRBuilder, num):
        return FloInt(builder.xor(self.value, num.value))

    def castTo(self, builder: ir.IRBuilder, type):
        if type == FloFloat:
            return self.toFloat(builder)
        elif type == FloBool:
            return self.cmp(builder, "!=", FloInt.zero())
        else:
            raise Exception(f"Unhandled type cast: int to {type}")

    @staticmethod
    def str() -> str:
        return "int"


class FloFloat:
    llvmtype = ir.DoubleType()
    print_fmt = "%g"

    def __init__(self, value: float | ir.Constant):
        if isinstance(value, float):
            self.value = ir.Constant(ir.DoubleType(), value)
        else:
            self.value = value

    def toInt(self, builder: ir.IRBuilder):
        return FloInt(builder.fptosi(self.value, FloInt.llvmtype))

    def add(self, builder: ir.IRBuilder, num):
        return FloFloat(builder.fadd(self.value, num.value))

    def sub(self, builder: ir.IRBuilder, num):
        return FloFloat(builder.fsub(self.value, num.value))

    def mul(self, builder: ir.IRBuilder, num):
        return FloFloat(builder.fmul(self.value, num.value))

    def div(self, builder: ir.IRBuilder, num):
        return FloFloat(builder.fdiv(self.value, num.value))

    def cmp(self, builder: ir.IRBuilder, op, num):
        if not isinstance(num, FloFloat):
            return FloBool.false()
        return FloBool(builder.fcmp_ordered(op, self.value, num.value))

    def mod(self, builder: ir.IRBuilder, num):
        return FloFloat(builder.frem(self.value, num.value))

    def print_val(self, _):
        return self.value

    def pow(self, builder, num):
        v = builder.call(builtIns.get_instrinsic(
            "llvm.pow"), [self.value, num.value])
        return FloFloat(v)

    def neg(self):
        self.value = self.value.fneg()
        return self

    def castTo(self, builder: ir.IRBuilder, type):
        if type == FloInt:
            return self.toInt(builder)
        elif type == FloBool:
            return self.cmp(builder, "!=", FloFloat.zero())
        elif type == FloFloat:
            return self
        else:
            raise Exception(f"Unhandled type cast: float to {type}")

    @staticmethod
    def zero():
        return FloFloat(0.0)

    @staticmethod
    def one():
        return FloFloat(1.0)

    @staticmethod
    def default_llvm_val():
        return FloFloat.zero().value

    @staticmethod
    def str() -> str:
        return "float"


class FloBool:
    llvmtype = ir.IntType(1)
    print_fmt = "%s"

    def __init__(self, value):
        if isinstance(value, bool):
            self.value = ir.Constant(FloBool.llvmtype, int(value))
        else:
            self.value = value

    def cmp(self, builder: ir.IRBuilder, op, bool):
        if not isinstance(bool, FloBool):
            return FloBool.false()
        return FloBool(builder.icmp_signed(op, self.value, bool.value))

    def not_(self, builder: ir.IRBuilder):
        return FloBool(builder.not_(self.value))

    def or_(self, builder: ir.IRBuilder, bool):
        return FloBool(builder.or_(self.value, bool.value))

    def and_(self, builder: ir.IRBuilder, bool):
        return FloBool(builder.and_(self.value, bool.value))

    def print_val(self, builder: ir.IRBuilder):
        return builder.select(self.value, FloStr("true").value, FloStr("false").value)

    @staticmethod
    def default_llvm_val(_):
        return FloBool.true().value

    @staticmethod
    def true():
        return FloBool(True)

    @staticmethod
    def false():
        return FloBool(False)

    @staticmethod
    def str() -> str:
        return 'bool'


str_t = ir.global_context.get_identified_type("struct.str")
str_t.set_body(ir.IntType(8).as_pointer(), FloInt.llvmtype)


class FloStr:
    id = -1
    strs = {}
    llvmtype = str_t.as_pointer()
    print_fmt = "%s"

    def __init__(self, value, builder: ir.IRBuilder = None):
        # Check for already defined strings
        self.len_ptr = None   
        if isinstance(value, str):
            if FloStr.strs.get(value, None) != None:
                self.value = FloStr.strs[str(value)].value
                self.len_ptr = FloStr.strs[str(value)].len_ptr
            else:
                assert builder != None
                str_ptr = FloStr.create_global_const(value)
                self.value = FloStr.create_new_str_val(
                    builder, str_ptr, FloInt(len(value)))
                FloStr.strs[value] = self
        else:
            self.value = value

    @staticmethod
    def create_global_const(value):
        encoded = (value+'\0').encode(
            encoding="utf-8", errors="xmlcharrefreplace"
        )
        byte_array = bytearray(encoded)
        str_val = ir.Constant(
            ir.ArrayType(ir.IntType(8), len(byte_array)), byte_array
        )
        str_ptr = ir.GlobalVariable(
            Context.current_llvm_module, str_val.type, f"str.{FloStr.incr()}"
        )
        str_ptr.linkage = "private"
        str_ptr.global_constant = True
        str_ptr.unnamed_addr = True
        str_ptr.initializer = str_val
        return str_ptr.bitcast(str_t.elements[0])

    @staticmethod
    def create_new_str_val(builder: ir.IRBuilder, buffer_val, str_len: FloInt):
        struct_ptr = builder.alloca(str_t)
        buffer_ptr = builder.gep(
            struct_ptr, [FloInt.zero().value]*2, True)
        len_ptr = builder.gep(
            struct_ptr, [FloInt.zero().value, FloInt.one().value], True)
        builder.store(buffer_val, buffer_ptr)
        builder.store(str_len.value, len_ptr)
        return struct_ptr

    def get_buffer_ptr(self, builder: ir.IRBuilder):
        buff_ptr_ptr = builder.gep(self.value, [FloInt.zero().value]*2, True)
        return builder.load(buff_ptr_ptr)
    
    def get_length(self, builder: ir.IRBuilder):
        len_ptr = builder.gep(self.value, [FloInt.zero().value, FloInt.one().value], True)
        return FloInt(builder.load(len_ptr))

    def getElement(self, builder: ir.IRBuilder, index: FloInt):
        val = builder.load(builder.gep(self.get_buffer_ptr(builder), [index.value]))
        char_ty = str_t.elements[0].pointee
        arr_ty = ir.ArrayType(char_ty, 2)
        str_start_ptr = builder.gep(
            builder.alloca(arr_ty), [FloInt.zero().value]*2)
        builder.store(val, str_start_ptr)
        str_term_ptr = builder.gep(str_start_ptr, [FloInt.one().value])
        builder.store(ir.Constant(char_ty, 0), str_term_ptr)
        return FloStr(FloStr.create_new_str_val(builder, str_start_ptr, FloInt.one()))

    def add(self, builder: ir.IRBuilder, str):
        s1_length = self.get_length(builder)
        s2_length = str.get_length(builder)
        result_str_len = s1_length.add(builder, s2_length)
        arr_space = builder.alloca(ir.IntType(
            8), result_str_len.add(builder, FloInt.one()).value)
        false_val = FloBool.false().value
        s1_ptr = self.get_buffer_ptr(builder)
        s2_ptr = str.get_buffer_ptr(builder)
        start_ptr = builder.gep(arr_space, [FloInt.zero().value])
        mid_ptr = builder.gep(start_ptr, [s1_length.value])
        builder.call(builtIns.get_instrinsic("llvm.memcpy"), [
                     start_ptr, s1_ptr, s1_length.value, false_val])
        builder.call(builtIns.get_instrinsic("llvm.memcpy"), [
                     mid_ptr, s2_ptr, s2_length.add(builder, FloInt.one()).value, false_val])
        return FloStr(FloStr.create_new_str_val(builder, arr_space, result_str_len))

    def incr():
        FloStr.id += 1
        return FloStr.id

    def print_val(self, builder: ir.IRBuilder):
        return self.get_buffer_ptr(builder)

    @staticmethod
    def default_llvm_val():
        return FloStr("").value

    @staticmethod
    def str() -> str:
        return "str"


class FloArray:
    def __init__(self, builder: ir.IRBuilder, elms, size=0):
        self.size = size
        if isinstance(elms, list):
            self.elm_type = elms[0].__class__
            self.size = len(elms)
            self.type = ir.ArrayType(self.elm_type.llvmtype, self.size)
            arr_ptr = builder.alloca(self.type)
            for index in range(len(elms)):
                ptr = builder.gep(
                    arr_ptr, [FloInt.zero().value, FloInt(index).value], True)
                builder.store(elms[index].value, ptr)
            self.value = builder.bitcast(
                arr_ptr, self.elm_type.llvmtype.as_pointer())
        elif builder == None:
            self.elm_type = elms
        else:
            self.value = elms
            self.elm_type = llvm_to_flotype(
                ir.Constant(elms.type.pointee, 0)).__class__

    def add(self, builder: ir.IRBuilder, arr):
        memcpy_func = builtIns.get_instrinsic("llvm.memcpy")
        res_array_size = self.size + arr.size
        res_array_space = builder.bitcast(builder.alloca(ir.ArrayType(
            self.elm_type.llvmtype, res_array_size)),  self.elm_type.llvmtype.as_pointer())
        arr1_pos_ptr = builder.gep(
            res_array_space, [FloInt.zero().value])
        arr2_pos_ptr = builder.gep(
            res_array_space, [FloInt(self.size).value])

        arr1_ptr = builder.bitcast(self.value, memcpy_func.args[0].type)
        arr2_ptr = builder.bitcast(arr.value, memcpy_func.args[0].type)
        arr1_pos_ptr = builder.bitcast(arr1_pos_ptr, memcpy_func.args[0].type)
        arr2_pos_ptr = builder.bitcast(arr2_pos_ptr, memcpy_func.args[0].type)
        elem_size = self.elm_type.llvmtype.get_abi_size(target_data)
        arr1_num_of_bytes = elem_size * self.size
        arr2_num_of_bytes = elem_size * arr.size

        builder.call(memcpy_func, [arr1_pos_ptr, arr1_ptr, FloInt(
            arr1_num_of_bytes).value, FloBool.false().value])
        builder.call(memcpy_func, [arr2_pos_ptr, arr2_ptr, FloInt(
            arr2_num_of_bytes).value, FloBool.false().value])

        res_array = FloArray(builder, res_array_space, res_array_size)
        res_array.elm_type = self.elm_type
        res_array.size = res_array_size
        return res_array

    def getElement(self, builder: ir.IRBuilder, index):
        ptr = builder.gep(self.value, [index.value], True)
        return self.elm_type(builder.load(ptr))

    def setElement(self, builder: ir.IRBuilder, index, value):
        ptr = builder.gep(self.value, [index.value], True)
        builder.store(value.value, ptr)
        return value
    # TODO: Inaccurate type str

    def str(self) -> str:
        return f"{self.elm_type.str()} {'[]'}"

    def __eq__(self, __o: object) -> bool:
        return isinstance(__o, FloArray) and self.elm_type == __o.elm_type

# TODO: Unecessary loads (re-load only when you have stored)


class FloRef:
    def __init__(self, builder: ir.IRBuilder, value, name=''):
        self.builder = builder
        self.addr = self.builder.alloca(value.value.type, None, name)
        self.referee = value
        self.builder.store(value.value, self.addr)

    def load(self):
        self.referee.value = self.builder.load(self.addr)
        return self.referee

    @staticmethod
    def refcpy(builder: ir.IRBuilder, ref1, ref2):
        size = ref1.referee.value.type.get_abi_size(target_data)
        mem_cpy_fn = builtIns.get_instrinsic("llvm.memcpy")
        ref1_ptr = builder.bitcast(ref1.addr, mem_cpy_fn.args[0].type)
        ref2_ptr = builder.bitcast(ref2.addr, mem_cpy_fn.args[1].type)
        builder.call(mem_cpy_fn, [ref1_ptr, ref2_ptr,
                     FloInt(size).value, FloBool.false().value])

    def store(self, value):
        self.builder.store(value.value, self.addr)
        # if isinstance(self.referee, FloStr):
        #     FloRef.refcpy(self.builder, self.referee.len_ptr, value.len_ptr)


class FloFunc:
    def __init__(self, arg_types, return_type, name):
        fncty = ir.FunctionType(flotype_to_llvm(return_type), [
                                flotype_to_llvm(arg_ty) for arg_ty in arg_types])
        self.return_type = return_type
        self.arg_types = arg_types
        self.value = ir.Function(Context.current_llvm_module, fncty, name)
        fn_entry_block = self.value.append_basic_block()
        self.builder = ir.IRBuilder(fn_entry_block)

    def call(self, builder: ir.IRBuilder, args):
        return llvm_to_flotype(builder.call(self.value, [arg.value for arg in args]))

    def extend_symbol_table(self, symbol_table: SymbolTable, arg_names: List(str)):
        for i in range(len(arg_names)):
            arg_val = self.arg_types[i](self.value.args[i]) if not isinstance(self.arg_types[i], FloArray) else FloArray(
                self.builder, self.value.args[i])
            symbol_table.set(arg_names[i], FloRef(
                self.builder, arg_val, arg_names[i]))
        return symbol_table

    def str(self) -> str:
        return f"({self.arg_types[0]})=>{self.return_type}"


class FloInlineFunc(FloFunc):
    def __init__(self, call, arg_types, return_type):
        self.arg_types = arg_types
        self.return_type = return_type
        self.call_method = call

    def call(self, *kargs):
        return self.call_method(*kargs)


class FloVoid:
    print_fmt = "%s"
    llvmtype = ir.VoidType()

    def print_val(self, _):
        return FloStr("null").value

    @staticmethod
    def str(self) -> str:
        "void"


class FloDict:
    def __init__(self, elementType):
        self.elementType = elementType

    def __eq__(self, o: object) -> bool:
        if isinstance(o, FloDict):
            return self.elementType == o.elementType
        return False
