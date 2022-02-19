from ast import List
import contextlib
import struct
import builtIns as bi
from context import Context, SymbolTable
from llvmlite import ir, binding
target_data = binding.create_target_data("e S0")


@contextlib.contextmanager
def define_or_call_method(name: str, this):
    fnc = FloFunc([this], FloVoid, name)
    FloFunc.defined_methods[name] = fnc
    yield fnc.builder
    fnc.call(this)


class FloType:
    def cast_to():
        raise Exception("undefined cast")

    @staticmethod
    def str():
        return "any"

    @staticmethod
    def flotype_to_llvm(type):
        return type.llvmtype

    @staticmethod
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


class FloInt(FloType):
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

    def to_float(self, builder: ir.IRBuilder):
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
        fv = self.cast_to(builder, FloFloat).pow(
            builder, num.cast_to(builder, FloFloat))
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

    def cast_to(self, builder: ir.IRBuilder, type):
        if type == FloFloat:
            return self.to_float(builder)
        elif type == FloBool:
            return self.cmp(builder, "!=", FloInt.zero())
        else:
            raise Exception(f"Unhandled type cast: int to {type}")

    @staticmethod
    def str() -> str:
        return "int"


class FloFloat(FloType):
    llvmtype = ir.DoubleType()
    print_fmt = "%g"

    def __init__(self, value: float | ir.Constant):
        if isinstance(value, float):
            self.value = ir.Constant(ir.DoubleType(), value)
        else:
            self.value = value

    def to_int(self, builder: ir.IRBuilder):
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
        v = builder.call(bi.get_instrinsic("pow"), [self.value, num.value])
        return FloFloat(v)

    def neg(self):
        self.value = self.value.fneg()
        return self

    def cast_to(self, builder: ir.IRBuilder, type):
        if type == FloInt:
            return self.to_int(builder)
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


class FloBool(FloType):
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
        return builder.select(self.value, FloStr.create_global_const("true"), FloStr.create_global_const("false"))

    def cast_to(self, builder: ir.IRBuilder, type):
        if type == FloInt:
            return FloInt(self.value.zext(FloInt.llvmtype))
        else:
            raise Exception()

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


class FloStr(FloType):
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
        size = str_t.get_abi_size(target_data)
        i8_struct_ptr = builder.call(
            bi.get_instrinsic("malloc"), [FloInt(size).value])
        struct_ptr = builder.bitcast(i8_struct_ptr, str_t.as_pointer())
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
        len_ptr = builder.gep(
            self.value, [FloInt.zero().value, FloInt.one().value], True)
        return FloInt(builder.load(len_ptr))

    def get_element(self, builder: ir.IRBuilder, index: FloInt):
        val = builder.load(builder.gep(
            self.get_buffer_ptr(builder), [index.value]))
        char_ty = str_t.elements[0].pointee
        arr_ty = ir.ArrayType(char_ty, 2)
        str_start_ptr = builder.gep(
            builder.alloca(arr_ty), [FloInt.zero().value]*2)
        builder.store(val, str_start_ptr)
        str_term_ptr = builder.gep(str_start_ptr, [FloInt.one().value])
        builder.store(ir.Constant(char_ty, 0), str_term_ptr)
        return FloStr(FloStr.create_new_str_val(builder, str_start_ptr, FloInt.one()))

    def add(self, builder: ir.IRBuilder, str):
        false = FloBool.false().value
        memcpy_fnc = bi.get_instrinsic("memcpy")
        str1_len = self.get_length(builder)
        str2_len = str.get_length(builder)
        new_str_len = str1_len.add(builder, str2_len)
        new_str_buf = builder.call(bi.get_instrinsic("malloc"), [
                                   new_str_len.add(builder, FloInt.one()).value])
        str1_buf_ptr = self.get_buffer_ptr(builder)
        str2_buf_ptr = str.get_buffer_ptr(builder)
        idx0 = builder.gep(new_str_buf, [FloInt.zero().value])
        idx1 = builder.gep(idx0, [str1_len.value])
        builder.call(memcpy_fnc, [idx0, str1_buf_ptr, str1_len.value, false])
        builder.call(memcpy_fnc, [idx1, str2_buf_ptr, str2_len.add(
            builder, FloInt.one()).value, false])
        return FloStr(FloStr.create_new_str_val(builder, new_str_buf, new_str_len))

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


array_t = ir.global_context.get_identified_type("struct.arr")
array_t.set_body(ir.IntType(8).as_pointer(), FloInt.llvmtype, FloInt.llvmtype)


class FloArray(FloType):
    llvmtype = array_t.as_pointer()

    def __init__(self, value, builder: ir.IRBuilder = None, size=None):
        self.size = size
        if isinstance(value, list):
            assert builder != None
            arr_len = len(value)
            self.elm_type = value[0].__class__
            arr_size = size if size else arr_len*2
            arr_buff = self._create_array_buffer(builder, value, arr_size)
            self.value = self._create_array_struct(
                builder, arr_buff, FloInt(arr_len), FloInt(arr_size))
        else:
            self.value = value

    def get_len_ptr(self, builder: ir.IRBuilder):
        return builder.gep(self.value, [FloInt.zero().value, FloInt.one().value])

    def get_length(self, builder: ir.IRBuilder):
        len_ptr = self.get_len_ptr(builder)
        return FloInt(builder.load(len_ptr))

    def get_size_ptr(self, builder: ir.IRBuilder):
        return builder.gep(self.value, [FloInt.zero().value, FloInt(2).value])

    def get_size(self, builder: ir.IRBuilder):
        size_ptr = self.get_size_ptr(builder)
        return FloInt(builder.load(size_ptr))

    def get_buffer_ptr(self, builder: ir.IRBuilder):
        array_buff_ptr = builder.gep(self.value, [FloInt.zero().value]*2)
        return builder.bitcast(builder.load(array_buff_ptr), self.elm_type.llvmtype.as_pointer())

    def _create_array_struct(self, builder: ir.IRBuilder, arr_buff, arr_len: FloInt, arr_size: FloInt):
        struct_size = array_t.get_abi_size(target_data)
        i8_struct = builder.call(bi.get_instrinsic("malloc"), [FloInt(struct_size).value])
        struct = builder.bitcast(i8_struct, array_t.as_pointer())
        arr_buff_ptr = builder.gep(struct, [FloInt.zero().value]*2)
        arr_len_ptr = builder.gep(
            struct, [FloInt.zero().value, FloInt.one().value])
        arr_size_ptr = builder.gep(
            struct, [FloInt.zero().value, FloInt(2).value])
        builder.store(arr_len.value, arr_len_ptr)
        builder.store(arr_size.value, arr_size_ptr)
        builder.store(builder.bitcast(
            arr_buff, array_t.elements[0]), arr_buff_ptr)
        return struct

    def _create_array_buffer(self, builder: ir.IRBuilder, array_values, size):
        array_buffer = builder.alloca(ir.ArrayType(self.elm_type.llvmtype, size))
        for index in range(len(array_values)):
            ptr = builder.gep(
                array_buffer, [FloInt.zero().value, FloInt(index).value], True)
            builder.store(array_values[index].value, ptr)
        return array_buffer

    def new_array_with_val(self, value):
        array = FloArray(value)
        array.elm_type = self.elm_type
        return array

    def get_elem_ty_size(self):
        return FloInt(self.elm_type.llvmtype.get_abi_size(target_data))

    def grow(self, builder: ir.IRBuilder):
        realloc = bi.get_instrinsic("realloc")
        new_size = self.get_size(builder).mul(builder, FloInt(2))
        elem_size = self.get_elem_ty_size()
        buff_ptr = builder.load(builder.gep(
            self.value, [FloInt.zero().value]*2))
        builder.call(
            realloc, [buff_ptr, new_size.mul(builder, elem_size).value])
        size_ptr = self.get_size_ptr(builder)
        builder.store(new_size.value, size_ptr)

    def add(self, builder: ir.IRBuilder, arr):
        memcpy_func = bi.get_instrinsic("memcpy")
        false = FloBool.false().value
        arr1_len = self.get_length(builder)
        arr2_len = arr.get_length(builder)
        new_arr_len = arr1_len.add(builder, arr2_len)
        
        alloc_size = self.get_elem_ty_size().mul(builder, new_arr_len).value
        i8_arr_buffer = builder.call(bi.get_instrinsic("malloc"), [alloc_size])
        new_arr_buff = builder.bitcast(i8_arr_buffer, self.elm_type.llvmtype.as_pointer())
        arr1_pos_ptr = builder.gep(new_arr_buff, [FloInt.zero().value])
        arr1_pos_ptr = builder.bitcast(arr1_pos_ptr, memcpy_func.args[0].type)
        arr2_pos_ptr = builder.gep(new_arr_buff, [arr1_len.value])
        arr2_pos_ptr = builder.bitcast(arr2_pos_ptr, memcpy_func.args[1].type)

        arr1_ptr = builder.bitcast(self.get_buffer_ptr(
            builder), memcpy_func.args[1].type)
        arr2_ptr = builder.bitcast(arr.get_buffer_ptr(
            builder), memcpy_func.args[1].type)
        elem_size = self.get_elem_ty_size()
        arr1_num_of_bytes = arr1_len.mul(builder, elem_size)
        arr2_num_of_bytes = arr2_len.mul(builder, elem_size)

        builder.call(memcpy_func, [arr1_pos_ptr,
                     arr1_ptr, arr1_num_of_bytes.value, false])
        builder.call(memcpy_func, [arr2_pos_ptr,
                     arr2_ptr, arr2_num_of_bytes.value, false])

        new_arr_val = self._create_array_struct(
            builder, new_arr_buff, new_arr_len, new_arr_len)
        return self.new_array_with_val(new_arr_val)

    def get_element(self, builder: ir.IRBuilder, index):
        ptr = builder.gep(self.get_buffer_ptr(builder), [index.value], True)
        if isinstance(self.elm_type, FloArray):
            return self.elm_type.new_array_with_val(builder.load(ptr))
        return self.elm_type(builder.load(ptr))

    def set_element(self, builder: ir.IRBuilder, index, value):
        ptr = builder.gep(self.get_buffer_ptr(builder), [index.value], True)
        builder.store(value.value, ptr)
        return value

    def sl(self, builder: ir.IRBuilder, value):
        len_ptr = self.get_len_ptr(builder)
        len = self.get_length(builder)
        size = self.get_size(builder)
        incremented_len = len.add(builder, FloInt.one())
        with builder.if_then(incremented_len.cmp(builder, '>=', size).value):
            self.grow(builder)
        self.set_element(builder, len, value)
        builder.store(incremented_len.value, len_ptr)
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
        self.addr = self.builder.alloca(value.llvmtype, None, name)
        self.referee = value
        self.builder.store(value.value, self.addr)

    def load(self):
        self.referee.value = self.builder.load(self.addr)
        return self.referee

    def store(self, value):
        self.builder.store(value.value, self.addr)


class FloFunc(FloType):
    defined_methods = {}

    def __init__(self, arg_types, return_type, name):
        fncty = ir.FunctionType(FloType.flotype_to_llvm(return_type), [
                                FloType.flotype_to_llvm(arg_ty) for arg_ty in arg_types])
        self.return_type = return_type
        self.arg_types = arg_types
        self.value = ir.Function(Context.current_llvm_module, fncty, name)
        fn_entry_block = self.value.append_basic_block()
        self.builder = ir.IRBuilder(fn_entry_block)

    def call(self, builder: ir.IRBuilder, args):
        rt_value = builder.call(self.value, [arg.value for arg in args])
        if isinstance(self.return_type, FloArray):
            return self.return_type.new_array_with_val(rt_value)
        if self.return_type == FloVoid:
            return self.return_type()
        return self.return_type(rt_value)

    def extend_symbol_table(self, symbol_table: SymbolTable, arg_names: List(str)):
        for i in range(len(arg_names)):
            if isinstance(self.arg_types[i], FloArray):
                arg_val = self.arg_types[i].new_array_with_val(
                    self.value.args[i])
            else:
                arg_val = self.arg_types[i](self.value.args[i])
            symbol_table.set(arg_names[i], FloRef(
                self.builder, arg_val, arg_names[i]))
        return symbol_table

    def str(self) -> str:
        return f"({self.arg_types[0]})=>{self.return_type.str()}"


class FloInlineFunc(FloFunc):
    def __init__(self, call, arg_types, return_type):
        self.arg_types = arg_types
        self.return_type = return_type
        self.call_method = call

    def call(self, *kargs):
        return self.call_method(*kargs)


class FloVoid(FloType):
    print_fmt = "%s"
    llvmtype = ir.VoidType()

    def print_val(self, _):
        return FloStr("null").value

    @staticmethod
    def str() -> str:
        return "void"
