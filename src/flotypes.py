from ast import List
import contextlib
import uuid
import builtIns as bi
from context import Context, SymbolTable
from llvmlite import ir, binding
target_data = binding.create_target_data("e S0")


@contextlib.contextmanager
def define_or_call_method(builder, name: str, args, rt_type):
    c_builder = None
    if FloFunc.defined_methods.get(name):
        fnc: FloFunc = FloFunc.defined_methods.get(name)
    else:
        fnc = FloFunc(args, rt_type, name)
        saved_vals = [arg.value for arg in args]
        for i, arg_value in enumerate(fnc.value.args):
            args[i].value = arg_value
        FloFunc.defined_methods[name] = fnc
        c_builder = fnc.builder

    def ret(rt_value):
        fnc.ret(rt_value)
        for i, saved_value in enumerate(saved_vals):
            args[i].value = saved_value

    def call():
        return fnc.call(builder, args)

    yield c_builder, ret, call


class FloType:
    llvmtype = None
    value: ir.Value

    def create_uuid(self) -> None:
        self.uuid = uuid.uuid1()

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


class FloIterable(FloType):
    @staticmethod
    @contextlib.contextmanager
    def foreach(self, builder: ir.IRBuilder, len=None):
        entry = builder.append_basic_block('foreach.entry')
        loop = builder.append_basic_block('foreach.loop')
        builder.branch(entry)
        builder.position_at_start(entry)
        i_ref = FloRef(builder, FloInt.zero())
        if len == None:
            len = self.get_length(builder)
        builder.branch(loop)
        builder.position_at_start(loop)
        index: FloInt = i_ref.load()
        inr_index = index.add(builder, FloInt.one())
        i_ref.store(inr_index)
        cond = inr_index.cmp(builder, '<', len).value
        exit = builder.append_basic_block('foreach.exit')
        yield self.get_element(builder, index), index, loop, exit
        builder.cbranch(cond, loop, exit)
        builder.position_at_start(exit)


class FloVoid(FloType):
    llvmtype = ir.VoidType()

    def print_val(builder):
        bi.call_printf(builder, "null")

    @staticmethod
    def str() -> str:
        return "void"


class FloInt(FloType):
    llvmtype = ir.IntType(32)

    def __init__(self, value: int | ir.Constant):
        self.create_uuid()
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

    def print_val(self, builder):
        bi.call_printf(builder, "%d", self.value)

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
        elif type == FloStr:
            malloc = bi.get_instrinsic("malloc")
            sprintf = bi.get_instrinsic("sprintf")
            log10 = bi.get_instrinsic("log10")
            float_val = self.cast_to(builder, FloFloat)
            str_len = FloFloat(builder.call(log10, [float_val.value]))
            str_len = str_len.cast_to(
                builder, FloInt).add(builder, FloInt.one())
            str_leni = str_len.add(builder, FloInt.one()).value
            str_buff = builder.call(malloc, [str_leni])
            fmt = FloStr.create_global_const("%d")
            builder.call(sprintf, [str_buff, fmt, self.value])
            str_buff = FloMem(str_buff)
            str_struct = FloStr.create_new_str_val(builder, str_buff, str_len)
            return str_struct
        else:
            raise Exception(f"Unhandled type cast: int to {type.str()}")

    @staticmethod
    def str() -> str:
        return "int"


class FloFloat(FloType):
    llvmtype = ir.DoubleType()

    def __init__(self, value: float | ir.Constant):
        self.create_uuid()
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

    def print_val(self, builder):
        bi.call_printf(builder, "%g", self.value)

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
        elif type == FloStr:
            malloc = bi.get_instrinsic("malloc")
            sprintf = bi.get_instrinsic("sprintf")
            strlen = bi.get_instrinsic("strlen")
            str_buff = builder.call(malloc, [FloInt(1).value])
            fmt = FloStr.create_global_const("%f")
            builder.call(sprintf, [str_buff, fmt, self.value])
            str_len = FloInt(builder.call(strlen, [str_buff]))
            str_buff = FloMem(str_buff)
            return FloStr.create_new_str_val(builder, str_buff, str_len)
        elif type == FloFloat:
            return self
        else:
            raise Exception(f"Unhandled type cast: float to {type.str()}")

    @staticmethod
    def zero():
        return FloFloat(0.0)

    @staticmethod
    def one():
        return FloFloat(1.0)

    @staticmethod
    def str() -> str:
        return "float"


class FloBool(FloType):
    llvmtype = ir.IntType(1)
    print_fmt = "%s"

    def __init__(self, value):
        self.create_uuid()
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
        value = builder.select(self.value, FloStr.create_global_const(
            "true"), FloStr.create_global_const("false"))
        bi.call_printf(builder, "%s", value)

    def cast_to(self, builder: ir.IRBuilder, type):
        if type == FloInt:
            return FloInt(builder.zext(self.value, FloInt.llvmtype))
        elif type == FloFloat:
            return self.cast_to(builder, FloInt).to_float(builder)
        else:
            raise Exception(f"Unhandled type cast: bool to {type.str()}")

    @staticmethod
    def true():
        return FloBool(True)

    @staticmethod
    def false():
        return FloBool(False)

    @staticmethod
    def str() -> str:
        return 'bool'


class FloMem(FloType):
    llvmtype = ir.IntType(8).as_pointer()

    def __init__(self, value):
        self.value = value


str_t = ir.global_context.get_identified_type("struct.str")
str_t.set_body(FloMem.llvmtype, FloInt.llvmtype)


class FloStr(FloIterable):
    global_strings = {}
    llvmtype = str_t.as_pointer()

    def __init__(self, value, builder: ir.IRBuilder = None):
        self.create_uuid()
        # Check for already defined strings
        self.len_ptr = None
        if isinstance(value, str):
            assert builder != None
            str_ptr = FloStr.create_global_const(value)
            self.value = FloStr.create_new_str_val(
                builder, FloMem(str_ptr), FloInt(len(value))).value
        else:
            self.value = value

    @staticmethod
    def create_global_const(value: str):
        if(FloStr.global_strings.get(value) != None):
            return FloStr.global_strings.get(value)
        encoded = (value+'\0').encode(
            encoding="utf-8", errors="xmlcharrefreplace"
        )
        byte_array = bytearray(encoded)
        str_val = ir.Constant(
            ir.ArrayType(ir.IntType(8), len(byte_array)), byte_array
        )
        str_ptr = ir.GlobalVariable(
            Context.current_llvm_module, str_val.type, f"str.{len(FloStr.global_strings.keys())}"
        )
        str_ptr.linkage = "private"
        str_ptr.global_constant = True
        str_ptr.unnamed_addr = True
        str_ptr.initializer = str_val
        str_ptr = str_ptr.bitcast(str_t.elements[0])
        FloStr.global_strings[value] = str_ptr
        return str_ptr

    @staticmethod
    def create_new_str_val(m_builder: ir.IRBuilder, buffer: FloMem, str_len: FloInt):
        with define_or_call_method(m_builder, str_t.name+'.new', [buffer, str_len], FloStr) as (builder, ret, call):
            if builder:
                size = str_t.get_abi_size(target_data)
                i8_struct_ptr = builder.call(
                    bi.get_instrinsic("malloc"), [FloInt(size).value])
                struct_ptr = builder.bitcast(i8_struct_ptr, str_t.as_pointer())
                buffer_ptr = builder.gep(
                    struct_ptr, [FloInt.zero().value]*2, True)
                len_ptr = builder.gep(
                    struct_ptr, [FloInt.zero().value, FloInt.one().value], True)
                builder.store(buffer.value, buffer_ptr)
                builder.store(str_len.value, len_ptr)
                ret(FloStr(struct_ptr))
            return call()

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
        return FloStr.create_new_str_val(builder, FloMem(str_start_ptr), FloInt.one())

    def add(self, m_builder: ir.IRBuilder, str):
        with define_or_call_method(m_builder, str_t.name+'.concat', [self, str], FloStr) as (builder, ret, call):
            if builder:
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
                builder.call(
                    memcpy_fnc, [idx0, str1_buf_ptr, str1_len.value, false])
                builder.call(memcpy_fnc, [idx1, str2_buf_ptr, str2_len.add(
                    builder, FloInt.one()).value, false])
                ret(FloStr.create_new_str_val(
                    builder, FloMem(new_str_buf), new_str_len))
            return call()

    def cmp(self, builder: ir.IRBuilder, op, str1):
        if not isinstance(str1, FloStr) or (op != '==' and op != '!='):
            return FloBool.false()
        is_eq = self.is_eq(builder, str1)
        if op == "!=":
            return is_eq.not_(builder)
        return is_eq

    def is_eq(self, m_builder: ir.IRBuilder, str1):
        with define_or_call_method(m_builder, str_t.name+'.eq', [self, str1], FloBool) as (builder, ret, call):
            if builder:
                str_len = self.get_length(builder)
                cond = str_len.cmp(builder, '==', str1.get_length(builder))
                with builder.if_then(cond.value):
                    str_buf_1 = self.get_buffer_ptr(builder)
                    str_buf_2 = str1.get_buffer_ptr(builder)
                    v = builder.call(bi.get_instrinsic("memcmp"), [
                                     str_buf_1, str_buf_2, str_len.value])
                    ret(FloInt(v).cmp(builder, '==', FloInt.zero()))
                ret(FloBool.false())
            return call()

    def cast_to(self, builder: ir.IRBuilder, type):
        if type == FloInt:
            atoi = bi.get_instrinsic("atoi")
            int_val = builder.call(atoi, [self.get_buffer_ptr(builder)])
            return FloInt(int_val)
        elif type == FloFloat:
            atod = bi.get_instrinsic('atof')
            dbl_val = builder.call(atod, [self.get_buffer_ptr(builder)])
            return FloFloat(dbl_val)
        else:
            raise Exception(f"Unhandled type cast: bool to {type.str()}")

    def print_val(self, builder: ir.IRBuilder):
        bi.call_printf(builder, "%s", self.get_buffer_ptr(builder))

    def free_mem(self, builder: ir.IRBuilder):
        free = bi.get_instrinsic("free")
        i8_ptr_struct = builder.bitcast(self.value, free.args[0].type)
        i8_buff_ptr = self.get_buffer_ptr(builder)
        builder.call(free, [i8_buff_ptr])
        builder.call(free, [i8_ptr_struct])

    @staticmethod
    def str() -> str:
        return "str"


array_t = ir.global_context.get_identified_type("struct.arr")
array_t.set_body(FloMem.llvmtype, FloInt.llvmtype, FloInt.llvmtype)


class FloArray(FloIterable):
    print_fmt = "aa"
    llvmtype = array_t.as_pointer()

    def __init__(self, value, builder: ir.IRBuilder = None, size=None):
        self.create_uuid()
        self.size = size
        if isinstance(value, list):
            assert builder != None
            arr_len = len(value)
            self.elm_type = value[0].__class__ if value[0].__class__ != FloArray else value[0]
            arr_size = size if size else arr_len*2
            arr_buff = self.create_array_buffer(builder, value, arr_size)
            self.value = self._create_array_struct(
                builder, arr_buff, FloInt(arr_len), FloInt(arr_size)).value
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

    def get_array_buff_ptr(self, builder: ir.IRBuilder):
        return builder.gep(self.value, [FloInt.zero().value]*2)

    def get_array(self, builder: ir.IRBuilder):
        array_buff_ptr = self.get_array_buff_ptr(builder)
        return builder.bitcast(builder.load(array_buff_ptr), self.elm_type.llvmtype.as_pointer())

    def _create_array_struct(self, m_builder: ir.IRBuilder, arr_buff: FloMem, arr_len: FloInt, arr_size: FloInt):
        with define_or_call_method(m_builder, array_t.name+".new", [arr_buff, arr_len, arr_size], self) as (builder, ret, call):
            if builder:
                struct_size = array_t.get_abi_size(target_data)
                i8_struct = builder.call(bi.get_instrinsic(
                    "malloc"), [FloInt(struct_size).value])
                struct = builder.bitcast(i8_struct, array_t.as_pointer())
                arr_buff_ptr = builder.gep(struct, [FloInt.zero().value]*2)
                arr_len_ptr = builder.gep(
                    struct, [FloInt.zero().value, FloInt.one().value])
                arr_size_ptr = builder.gep(
                    struct, [FloInt.zero().value, FloInt(2).value])
                builder.store(arr_len.value, arr_len_ptr)
                builder.store(arr_size.value, arr_size_ptr)
                builder.store(arr_buff.value, arr_buff_ptr)
                ret(FloArray(struct))
            return call()

    def create_array_buffer(self, builder: ir.IRBuilder, array_values, size):
        array_buffer = builder.call(bi.get_instrinsic(
            'malloc'), [self.get_elem_ty_size().mul(builder, FloInt(size)).value])
        elm_ty_arr_buff = builder.bitcast(
            array_buffer, self.elm_type.llvmtype.as_pointer())
        for i, array_value in enumerate(array_values):
            ptr = builder.gep(elm_ty_arr_buff, [FloInt(i).value], True)
            builder.store(array_value.value, ptr)
        return FloMem(array_buffer)

    def free_mem(self, builder: ir.IRBuilder):
        free = bi.get_instrinsic("free")
        i8_ptr_struct = builder.bitcast(self.value, free.args[0].type)
        i8_buff_ptr = builder.load(self.get_array_buff_ptr(builder))
        builder.call(free, [i8_buff_ptr])
        builder.call(free, [i8_ptr_struct])

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
        array = builder.call(
            realloc, [buff_ptr, new_size.mul(builder, elem_size).value])
        array_buff_ptr = self.get_array_buff_ptr(builder)
        builder.store(array, array_buff_ptr)
        size_ptr = self.get_size_ptr(builder)
        builder.store(new_size.value, size_ptr)

    def add(self, m_builder: ir.IRBuilder, arr):
        with define_or_call_method(m_builder, array_t.name+'.concat', [self, arr], self) as (builder, ret, call):
            if builder:
                memcpy_func = bi.get_instrinsic("memcpy")
                false = FloBool.false().value
                arr1_len = self.get_length(builder)
                arr2_len = arr.get_length(builder)
                new_arr_len = arr1_len.add(builder, arr2_len)

                alloc_size = self.get_elem_ty_size().mul(builder, new_arr_len).value
                i8_arr_buffer = builder.call(
                    bi.get_instrinsic("malloc"), [alloc_size])
                new_arr_buff = builder.bitcast(
                    i8_arr_buffer, self.elm_type.llvmtype.as_pointer())
                arr1_pos_ptr = builder.gep(new_arr_buff, [FloInt.zero().value])
                arr1_pos_ptr = builder.bitcast(
                    arr1_pos_ptr, memcpy_func.args[0].type)
                arr2_pos_ptr = builder.gep(new_arr_buff, [arr1_len.value])
                arr2_pos_ptr = builder.bitcast(
                    arr2_pos_ptr, memcpy_func.args[1].type)

                arr1_ptr = builder.bitcast(self.get_array(
                    builder), memcpy_func.args[1].type)
                arr2_ptr = builder.bitcast(arr.get_array(
                    builder), memcpy_func.args[1].type)
                elem_size = self.get_elem_ty_size()
                arr1_num_of_bytes = arr1_len.mul(builder, elem_size)
                arr2_num_of_bytes = arr2_len.mul(builder, elem_size)

                builder.call(memcpy_func, [arr1_pos_ptr,
                                           arr1_ptr, arr1_num_of_bytes.value, false])
                builder.call(memcpy_func, [arr2_pos_ptr,
                                           arr2_ptr, arr2_num_of_bytes.value, false])

                new_arr_val = self._create_array_struct(
                    builder, FloMem(i8_arr_buffer), new_arr_len, new_arr_len)
                ret(new_arr_val)
            return call()

    def get_element(self, builder: ir.IRBuilder, index):
        ptr = builder.gep(self.get_array(builder), [index.value], True)
        if isinstance(self.elm_type, FloArray):
            return self.elm_type.new_array_with_val(builder.load(ptr))
        return self.elm_type(builder.load(ptr))

    def set_element(self, builder: ir.IRBuilder, index, value):
        ptr = builder.gep(self.get_array(builder), [index.value], True)
        builder.store(value.value, ptr)
        return value

    def sl(self, builder: ir.IRBuilder, value):
        len_ptr = self.get_len_ptr(builder)
        old_len = self.get_length(builder)
        current_size = self.get_size(builder)
        with builder.if_then(old_len.cmp(builder, '==', current_size).value):
            self.grow(builder)
        self.set_element(builder, old_len, value)
        builder.store(old_len.add(builder, FloInt.one()).value, len_ptr)
        return value

    def str(self) -> str:
        return f"{self.elm_type.str()}{'[]'}"

    def cmp(self, builder: ir.IRBuilder, op, arr):
        if not isinstance(arr, FloArray) or (op != '==' and op != '!='):
            return FloBool.false()
        is_eq = self.eq(builder, arr)
        if op == '!=':
            return is_eq.not_(builder)
        else:
            return is_eq

    def eq(self, m_builder: ir.IRBuilder, arr):
        if self.elm_type != arr.elm_type:
            return FloBool.false()
        elm_size = FloInt(self.elm_type.llvmtype.get_abi_size(target_data))
        with define_or_call_method(m_builder, array_t.name+'.eq', [self, arr, elm_size], FloBool) as (builder, ret, call):
            if builder:
                len_ = self.get_length(builder)
                cond = len_.cmp(builder, '!=', arr.get_length(builder))
                with builder.if_then(cond.value):
                    ret(FloBool.false())
                check_size = len_.mul(builder, FloInt(
                    builder.function.args[2])).value
                zero = FloInt.zero()
                arr_buff1 = builder.load(builder.gep(
                    builder.function.args[0], [zero.value]*2))
                arr_buff2 = builder.load(builder.gep(
                    builder.function.args[1], [zero.value]*2))
                cmp_val = builder.call(bi.get_instrinsic("memcmp"), [
                                       arr_buff1, arr_buff2, check_size])
                ret(FloInt(cmp_val).cmp(builder, '==', zero))
            return call()

    def __eq__(self, __o: object) -> bool:
        return isinstance(__o, FloArray) and self.elm_type == __o.elm_type

    def print_val(self, builder: ir.IRBuilder):
        bi.call_printf(builder, "[")
        length_minus_one = self.get_length(builder).sub(builder, FloInt.one())
        with FloIterable.foreach(self, builder, length_minus_one) as (element, _, _, _):
            element.print_val(builder)
            bi.call_printf(builder, ", ")
        self.get_element(builder, length_minus_one).print_val(builder)
        bi.call_printf(builder, "]")
        return None


# TODO: Unecessary loads (re-load only when you have stored)


class FloRef:
    active_references: dict[str, int] = {}

    def __init__(self, builder: ir.IRBuilder, value: FloType, name=''):
        self.builder = builder
        self.addr = self.builder.alloca(value.llvmtype, None, name)
        self.referee = value
        FloRef.increment_uuid(self.referee)
        self.builder.store(value.value, self.addr)

    def load(self):
        self.referee.value = self.builder.load(self.addr)
        return self.referee

    def store(self, value):
        if value.uuid != self.referee.uuid:
            FloRef.decrement_uuid(self.referee, self.builder)
        self.builder.store(value.value, self.addr)

    @staticmethod
    def increment_uuid(value):
        if value.value.type.is_pointer and not isinstance(value, FloFunc):
            if FloRef.active_references.get(value.uuid) == None:
                FloRef.active_references[value.uuid] = 1
                print('set %s new ref_count: %d ' % (
                    value.uuid, FloRef.active_references[value.uuid]))
            else:
                FloRef.active_references[value.uuid] += 1
                print('incrementing %s ref_count: %d ' % (
                    value.uuid, FloRef.active_references[value.uuid]))
    @staticmethod
    def decrement_uuid(value: FloType, builder: ir.IRBuilder):
        if FloRef.active_references.get(value.uuid) != None:
            FloRef.active_references[value.uuid] -= 1
            print('decrementing %s new ref_count %d: ' %
                  (value.uuid, FloRef.active_references[value.uuid]))
            if FloRef.active_references[value.uuid] == 0:
                FloRef.clean_ref(value, builder)
    @staticmethod
    def clean_ref(value, builder: ir.IRBuilder):
        print('cleaning up: %s' % value.uuid)
        if FloRef.active_references.get(value.uuid):
            value.free_mem(builder)
            del FloRef.active_references[value.uuid]


class FloFunc(FloType):
    defined_methods = {}
    def get_llvm_type(self):
        return ir.FunctionType(FloType.flotype_to_llvm(self.return_type), [
                               FloType.flotype_to_llvm(arg_ty) for arg_ty in self.arg_types])
    def __init__(self, arg_types=None, return_type=None, name=None):
        self.sym_tbl = None
        self.create_uuid()
        if isinstance(arg_types, FloFunc):
            self.arg_types = arg_types.arg_types
            self.llvmtype = arg_types.llvmtype
            self.return_type = arg_types.return_type
            self.sym_tbl = arg_types.sym_tbl
            self.value = return_type
        else:
            self.return_type = return_type
            self.arg_types = arg_types
            fn_type = self.get_llvm_type()
            self.llvmtype = fn_type.as_pointer()
            self.value = ir.Function(
                Context.current_llvm_module, fn_type, name)
            fn_entry_block = self.value.append_basic_block()
            self.builder = ir.IRBuilder(fn_entry_block)

    def call(self, builder: ir.IRBuilder, args):
        rt_value = builder.call(self.value, [arg.value for arg in args])
        if isinstance(self.return_type, FloArray):
            return self.return_type.new_array_with_val(rt_value)
        if self.return_type == FloVoid:
            return self.return_type()
        return self.return_type(rt_value)

    def get_symbol_table(self, arg_names: List(str)):
        self.arg_names = arg_names
        self.sym_tbl = bi.builtins_sym_tb.copy()
        for arg_name, arg_type, arg_value in zip(arg_names, self.arg_types,  self.value.args):
            if isinstance(arg_type, FloArray):
                arg_val = arg_type.new_array_with_val(arg_value)
            elif isinstance(arg_type, FloFunc):
                arg_val = arg_type.new_fnc_with_val(arg_value)
            else:
                arg_val = arg_type(arg_value)
            self.sym_tbl.set(arg_name, FloRef(self.builder, arg_val, arg_name))
        return self.sym_tbl

    def new_fnc_with_val(self, val):
        return FloFunc(self, val)

    def free_local_allocs(self, exception):
        if not self.sym_tbl: return
        for key in self.sym_tbl.symbols.keys():
            ref = self.sym_tbl.get(key)
            # Check if Ref and not excepted.
            if not isinstance(ref, FloRef): continue
            if exception != FloVoid:
                if ref.referee.uuid != exception.uuid: continue
            if ref.addr.name in self.arg_names: continue
            FloRef.clean_ref(ref.referee, self.builder)

    def ret(self, value, b=None):
        # Free Mem
        self.free_local_allocs(value)
        if value == FloVoid:
            return self.builder.ret_void()
        else:
            return self.builder.ret(value.value)

    def str(self) -> str:
        arg_list = ", ".join([arg.str() for arg in self.arg_types])
        return f"({arg_list})=>{self.return_type.str()}"

    def print_val(self, builder: ir.IRBuilder) -> str:
        bi.call_printf(builder, self.str())

    def __eq__(self, other):
        if isinstance(other, FloFunc) and len(self.arg_types) == len(other.arg_types):
            for my_arg, other_arg in zip(self.arg_types, other.arg_types):
                if my_arg != other_arg:
                    return False
            if self.return_type == other.return_type:
                return True
        return False


class FloInlineFunc(FloFunc):
    def __init__(self, call, arg_types, return_type, is_inline=True, defaults=[]):
        self.create_uuid()
        self.arg_types = arg_types
        self.return_type = return_type
        self.is_inline = is_inline
        self.defaults = defaults
        self.sym_tbl = None
        if call == None:
            fn_type = self.get_llvm_type()
            self.llvmtype = fn_type.as_pointer()
        self.call_method = call
        if return_type == FloVoid:
            self.returned = FloVoid
        else:
            self.returned = None

    def call(self, *kargs):
        returned = self.call_method(*kargs)
        if returned != None:
            return returned
        return self.returned.load() if self.returned != FloVoid else FloVoid

    def ret(self, value, builder):
        if self.returned != FloVoid:
            if self.returned == None:
                self.returned = FloRef(builder, value)
            else:
                self.returned.store(value)

# class HeapManager:
#     def alloc(size: FloInt): pass
#     def free(ptr: ir.Value): pass