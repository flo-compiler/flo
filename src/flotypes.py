from ast import List
import contextlib
import inspect
import uuid
import builtIns as bi
from context import Context, SymbolTable
from llvmlite import ir, binding

array_t = ir.global_context.get_identified_type("struct.arr")
array_t.set_body(bi.i8_ptr_ty, bi.i32_ty, bi.i32_ty)

va_list_t = ir.global_context.get_identified_type("struct.va_list")
va_list_t.set_body(bi.i8_ptr_ty)


class FloType:
    llvmtype = None
    value: ir.Value

    def __init__(self, value) -> None:
        self.value = value

    def cast_to():
        raise Exception("undefined cast")

    @staticmethod
    def str():
        return "any"

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
        i_ref = FloRef(builder, FloInt(0))
        if len == None:
            len = self.get_length(builder)
        builder.branch(loop)
        builder.position_at_start(loop)
        index = i_ref.load()
        inr_index = index.add(builder, FloInt(1))
        i_ref.store(inr_index)
        cond = inr_index.cmp(builder, '<', len)
        exit = builder.append_basic_block('foreach.exit')
        yield self.get_element(builder, index), index, loop, exit
        builder.cbranch(cond.value, loop, exit)
        builder.position_at_start(exit)


class FloVoid(FloType):
    llvmtype = ir.VoidType()

    def print_val(builder):
        bi.call_printf(builder, "null")

    @staticmethod
    def str() -> str:
        return "void"


class FloInt(FloType):
    llvmtype = bi.i32_ty

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
            sprintf = bi.get_instrinsic("sprintf")
            log10 = bi.get_instrinsic("log10")
            float_val = self.cast_to(builder, FloFloat)
            str_len = FloFloat(builder.call(log10, [float_val.value]))
            str_len = str_len.cast_to(
                builder, FloInt).add(builder, FloInt.one())
            str_leni = str_len.add(builder, FloInt.one())
            str_buff = FloMem.halloc_size(builder, str_leni)
            fmt = FloStr.create_global_const("%d")
            builder.call(sprintf, [str_buff.value, fmt, self.value])
            return FloStr(str_buff)
        else:
            raise Exception(f"Unhandled type cast: int to {type.str()}")

    @staticmethod
    def str() -> str:
        return "int"


class FloFloat(FloType):
    llvmtype = ir.DoubleType()

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
            sprintf = bi.get_instrinsic("sprintf")
            str_buff = FloMem.halloc_size(builder, FloInt(1))
            fmt = FloStr.create_global_const("%g")
            builder.call(sprintf, [str_buff.value, fmt, self.value])
            return FloStr(str_buff)
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

    def __eq__(self, other):
        return isinstance(other, FloBool) or other == FloBool

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
    heap_allocations = {}
    stack_allocations = {}
    llvmtype = bi.i8_ptr_ty

    def __init__(self, value):
        self.value = value
        self.uuid = str(uuid.uuid1())
        self.references = set()
        assert not isinstance(value, FloMem)

    def get_pointer_at_index(self, builder: ir.IRBuilder, *indices: FloInt):
        if len(list(indices)) == 0:
            return self
        ir_indices = [index.value for index in indices]
        return FloMem(builder.gep(self.value, ir_indices, True))

    def store_at_index(self, builder: ir.IRBuilder, floval: FloType, *indices: FloInt):
        idx_ptr = self.get_pointer_at_index(builder, *indices)
        if isinstance(floval, FloMem):
            self.references.add(floval.uuid)
        builder.store(floval.value, idx_ptr.value)

    def load_at_index(self, builder: ir.IRBuilder, *indices: FloInt):
        ptr = self.get_pointer_at_index(builder, *indices)
        loaded_value = builder.load(ptr.value)
        if loaded_value.type.is_pointer:
            return FloMem(loaded_value)
        return loaded_value

    def cmp(self, builder: ir.IRBuilder, mem2, size: FloInt):
        args = [self.value, mem2.value, size.value]
        res = builder.call(bi.get_instrinsic("memcmp"), args)
        return FloInt(res).cmp(builder, "==", FloInt(0))

    def copy_to(self, builder: ir.IRBuilder, dest, size: FloInt):
        args = [dest.value, self.value,  size.value, FloBool.false().value]
        builder.call(bi.get_instrinsic("memcpy"), args)

    def free(self, builder: ir.IRBuilder):
        i8_ptr = builder.bitcast(self.value, bi.i8_ptr_ty)
        builder.call(bi.get_instrinsic("free"), i8_ptr)

    @staticmethod
    def bitcast(builder: ir.IRBuilder, mem, ir_type: ir.Type):
        new_mem = FloMem(builder.bitcast(mem.value, ir_type))
        new_mem.uuid = mem.uuid
        return new_mem

    @staticmethod
    def halloc_size(builder: ir.IRBuilder, size: FloInt):
        malloc_fnc = bi.get_instrinsic("malloc")
        mem_obj = FloMem(builder.call(malloc_fnc, [size.value]))
        FloMem.heap_allocations[mem_obj.uuid] = mem_obj
        return mem_obj

    @staticmethod
    def halloc(builder: ir.IRBuilder, ir_type: ir.Type):
        size = FloInt(ir_type.get_abi_size(bi.target_data))
        mem_obj = FloMem.halloc_size(builder, size)
        mem_obj = FloMem.bitcast(builder, mem_obj, ir_type.as_pointer())
        return mem_obj

    @staticmethod
    def salloc(builder: ir.IRBuilder, ir_type: ir.Type):
        ty_ptr = builder.alloca(ir_type)
        mem_obj = FloMem(ty_ptr)
        FloMem.stack_allocations[mem_obj.uuid] = mem_obj
        return mem_obj

    @staticmethod
    def realloc(builder: ir.IRBuilder, mem, size: FloInt):
        realloc = bi.get_instrinsic("realloc")
        old_mem = FloMem.bitcast(builder, mem, bi.i8_ptr_ty).value
        new_mem = builder.call(realloc, [old_mem, size.value])
        new_mem = FloMem(new_mem)
        new_mem.uuid = mem.uuid
        FloMem.heap_allocations[mem.uuid] = new_mem
        return new_mem


class FloConst(FloType):
    # TODO be careful with arrays and strings
    def __init__(self, value: FloMem, flotype) -> None:
        assert isinstance(value, FloMem)
        self.flotype = flotype
        self.value = value

    def load(self, builder: ir.IRBuilder):
        val = self.value.load_at_index(builder)
        return self.flotype(val)

    @staticmethod
    def make_constant(builder: ir.IRBuilder, name: str, value: FloType) -> None:
        if isinstance(value, FloStr):
            return value
        const_val = ir.GlobalVariable(
            Context.current_llvm_module, value.llvmtype, name)
        const_val.initializer = value.value
        const_val.global_constant = True
        return FloConst(FloMem(const_val), value.__class__)


class FloStr(FloIterable):
    global_strings = {}
    llvmtype = bi.i8_ptr_ty

    def __init__(self, value: str | FloMem):
        self.len = None
        if isinstance(value, str):
            self.mem = FloMem(FloStr.create_global_const(value))
            self.len = FloInt(len(value))
            assert isinstance(self.mem, FloMem)
        else:
            self.mem = value
            assert isinstance(self.mem, FloMem)

    @staticmethod
    def create_global_const(value: str):
        if(FloStr.global_strings.get(value) != None):
            return FloStr.global_strings.get(value)
        encoded = (value+'\0').encode(
            encoding="utf-8", errors="xmlcharrefreplace"
        )
        byte_array = bytearray(encoded)
        str_val = ir.Constant(
            ir.ArrayType(bi.byte_ty, len(byte_array)), byte_array
        )
        str_ptr = ir.GlobalVariable(
            Context.current_llvm_module, str_val.type, f"str.{len(FloStr.global_strings.keys())}"
        )
        str_ptr.linkage = "private"
        str_ptr.global_constant = True
        str_ptr.unnamed_addr = True
        str_ptr.initializer = str_val
        str_ptr = str_ptr.bitcast(bi.i8_ptr_ty)
        FloStr.global_strings[value] = str_ptr
        return str_ptr

    def get_length(self, builder: ir.IRBuilder):
        if self.len == None:
            strlen = bi.get_instrinsic("strlen")
            ir_val = builder.call(strlen, [self.value])
            self.len = FloInt(ir_val)
        return self.len

    def get_element(self, builder: ir.IRBuilder, index: FloInt):
        val = self.mem.load_at_index(builder, index)
        arr_ptr = FloMem.salloc(builder, ir.ArrayType(bi.byte_ty, 2))
        arr_ptr = FloMem.bitcast(builder, arr_ptr, bi.i8_ptr_ty)
        arr_ptr.store_at_index(builder, FloType(val), FloInt(0))
        term_char = FloType(ir.Constant(bi.byte_ty, 0))
        arr_ptr.store_at_index(builder, term_char, FloInt(1))
        return FloStr(arr_ptr)

    def add(self, builder: ir.IRBuilder, str):
        str1_len = self.get_length(builder)
        str2_len = str.get_length(builder)
        new_str_len = str1_len.add(builder, str2_len)
        new_str_size = new_str_len.add(builder, FloInt(1))
        new_str_buff = FloMem.halloc_size(builder, new_str_size)
        pos1_ptr = new_str_buff.get_pointer_at_index(builder, FloInt(0))
        pos2_ptr = new_str_buff.get_pointer_at_index(builder, str1_len)
        str2_size = str2_len.add(builder, FloInt.one())
        self.mem.copy_to(builder, pos1_ptr, str1_len)
        str.mem.copy_to(builder, pos2_ptr, str2_size)
        return FloStr(new_str_buff)

    def cmp(self, builder: ir.IRBuilder, op, str1):
        if not isinstance(str1, FloStr) or (op != '==' and op != '!='):
            return FloBool.false()
        is_eq = self.is_eq(builder, str1)
        if op == "!=":
            return is_eq.not_(builder)
        return is_eq

    def is_eq(self, builder: ir.IRBuilder, str1):
        str_len = self.get_length(builder)
        cond = str_len.cmp(builder, '==', str1.get_length(builder))
        answer = FloMem.salloc(builder, FloBool.llvmtype)
        answer.store_at_index(builder, cond)
        with builder.if_then(cond.value):
            cmp_res = self.mem.cmp(builder, str1.mem, str_len)
            answer.store_at_index(builder, cmp_res)
        return FloBool(answer.load_at_index(builder))

    def cast_to(self, builder: ir.IRBuilder, type):
        if type == FloInt:
            atoi = bi.get_instrinsic("atoi")
            int_val = builder.call(atoi, [self.value])
            return FloInt(int_val)
        elif type == FloFloat:
            atod = bi.get_instrinsic('atof')
            dbl_val = builder.call(atod, [self.value])
            return FloFloat(dbl_val)
        else:
            raise Exception(f"Unhandled type cast: bool to {type.str()}")

    def print_val(self, builder: ir.IRBuilder):
        bi.call_printf(builder, "%s", self.value)

    @property
    def value(self):
        return self.mem.value

    @value.setter
    def value(self, new_mem):
        self.mem = new_mem
        self.len = None

    @staticmethod
    def str() -> str:
        return "str"


class FloArray(FloIterable):
    llvmtype = array_t.as_pointer()

    def __init__(self, value: FloMem | list[FloType], builder: ir.IRBuilder = None, size=None):
        self.size = size
        if isinstance(value, list):
            assert builder != None
            arr_len = len(value)
            self.elm_type = value[0].__class__ if value[0].__class__ != FloArray and value[0].__class__ != FloFunc else value[0]
            arr_size = FloInt(size if size else arr_len*2)
            arr_len = FloInt(arr_len)
            arr_buff = self.create_array_buffer(builder, value, arr_size)
            self.mem = FloArray.create_array_struct(
                builder, arr_buff, arr_len, arr_size)
        else:
            self.mem = value
        assert isinstance(self.mem, FloMem) or self.mem == None

    def get_len_ptr(self, builder: ir.IRBuilder):
        return self.mem.get_pointer_at_index(builder, FloInt(0), FloInt(1))

    def get_length(self, builder: ir.IRBuilder):
        len_val = self.get_len_ptr(builder).load_at_index(builder)
        return FloInt(len_val)

    def get_size_ptr(self, builder: ir.IRBuilder):
        return self.mem.get_pointer_at_index(builder, FloInt(0), FloInt(2))

    def get_size(self, builder: ir.IRBuilder):
        size_val = self.get_size_ptr(builder).load_at_index(builder)
        return FloInt(size_val)

    def get_array_buff_ptr(self, builder: ir.IRBuilder):
        return self.mem.get_pointer_at_index(builder, FloInt(0), FloInt(0))

    def get_array(self, builder: ir.IRBuilder):
        array_buff = self.get_array_buff_ptr(builder).load_at_index(builder)
        return FloMem.bitcast(builder, array_buff, self.elm_type.llvmtype.as_pointer())

    @staticmethod
    def create_array_struct(builder: ir.IRBuilder, arr_buff: FloMem, arr_len: FloInt, arr_size: FloInt):
        array_mem = FloMem.halloc(builder, array_t)
        array_mem.store_at_index(builder, arr_buff, FloInt(0), FloInt(0))
        array_mem.store_at_index(builder, arr_len, FloInt(0), FloInt(1))
        array_mem.store_at_index(builder, arr_size, FloInt(0), FloInt(2))
        return array_mem

    def create_array_buffer(self, builder: ir.IRBuilder, array_values: list[FloType], size: FloInt):
        array_size = self.get_elem_ty_size().mul(builder, size)
        i8_ptr = FloMem.halloc_size(builder, array_size)
        elem_ty = self.elm_type.llvmtype
        arr_ptr = FloMem.bitcast(builder, i8_ptr, elem_ty.as_pointer())
        for i, array_value in enumerate(array_values):
            arr_ptr.store_at_index(builder, array_value, FloInt(i))
        return i8_ptr

    def new(self, value):
        # For Functions
        array = FloArray(value)
        array.elm_type = self.elm_type
        return array

    def get_elem_ty_size(self):
        return FloInt(self.elm_type.llvmtype.get_abi_size(bi.target_data))

    def grow(self, builder: ir.IRBuilder):
        old_size = self.get_size(builder)
        elem_size = self.get_elem_ty_size()
        new_size = old_size.mul(builder, FloInt(2)).mul(builder, elem_size)
        arr_ptr = self.get_array_buff_ptr(builder)
        old_arr = arr_ptr.load_at_index(builder)
        new_arr = FloMem.realloc(builder, old_arr, new_size)
        arr_ptr.store_at_index(builder, new_arr)
        self.get_size_ptr(builder).store_at_index(builder, new_size)

    def add(self, builder: ir.IRBuilder, arr):
        arr1_len = self.get_length(builder)
        arr2_len = arr.get_length(builder)
        new_arr_len = arr1_len.add(builder, arr2_len)
        elem_size = self.get_elem_ty_size()
        new_arr_size = elem_size.mul(builder, new_arr_len)
        i8_arr_buff = FloMem.halloc_size(builder, new_arr_size)
        start_offset = arr1_len.mul(builder, elem_size)
        pos1_ptr = i8_arr_buff.get_pointer_at_index(builder, FloInt(0))
        pos2_ptr = i8_arr_buff.get_pointer_at_index(builder, start_offset)

        arr1_buff = self.get_array_buff_ptr(builder).load_at_index(builder)
        arr2_buff = arr.get_array_buff_ptr(builder).load_at_index(builder)
        arr1_num_of_bytes = arr1_len.mul(builder, elem_size)
        arr2_num_of_bytes = arr2_len.mul(builder, elem_size)
        arr1_buff.copy_to(builder, pos1_ptr, arr1_num_of_bytes)
        arr2_buff.copy_to(builder, pos2_ptr, arr2_num_of_bytes)

        new_arr_mem = FloArray.create_array_struct(
            builder, i8_arr_buff, new_arr_len, new_arr_len)
        return self.new(new_arr_mem)

    @property
    def value(self):
        return self.mem.value

    @value.setter
    def value(self, new_mem):
        self.mem = new_mem

    def get_element(self, builder: ir.IRBuilder, index):
        value = self.get_array(builder).load_at_index(builder, index)
        if inspect.isclass(self.elm_type):
            return self.elm_type(value)
        return self.elm_type.new(value)

    def set_element(self, builder: ir.IRBuilder, index, value):
        self.get_array(builder).store_at_index(builder, value, index)
        return value

    def sl(self, builder: ir.IRBuilder, value):
        len_ptr = self.get_len_ptr(builder)
        old_len = self.get_length(builder)
        current_size = self.get_size(builder)
        with builder.if_then(old_len.cmp(builder, '==', current_size).value):
            self.grow(builder)
        self.set_element(builder, old_len, value)
        len_ptr.store_at_index(builder, old_len.add(builder, FloInt.one()))
        return self

    def str(self) -> str:
        return f"{self.elm_type.str()}{'[]'}"

    def cmp(self, builder: ir.IRBuilder, op, arr):
        if not isinstance(arr, FloArray) or (op != '==' and op != '!='):
            return FloBool.false()
        is_eq = FloBool(self.eq(builder, arr).load_at_index(builder))
        if op == '!=':
            return is_eq.not_(builder)
        else:
            return is_eq

    def eq(self, builder: ir.IRBuilder, arr):
        result = FloMem.salloc(builder, FloBool.llvmtype)
        len_ = self.get_length(builder)
        cond = len_.cmp(builder, '==', arr.get_length(builder))
        result.store_at_index(builder, cond)
        with FloIterable.foreach(self, builder, len_) as (value, index, _, break_block):
            elm = arr.get_element(builder, index)
            new_check = value.cmp(builder, "==", elm)
            prev_check = FloBool(result.load_at_index(builder))
            new_check = new_check.and_(builder, prev_check)
            result.store_at_index(builder, new_check)
            with builder.if_then(new_check.not_(builder).value):
                builder.branch(break_block)
        return result

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

is_64_bit = binding.targets.get_host_cpu_features()['64bit']
class FloArgArray(FloArray):
    def __init__(self, value: FloMem | list[FloType], builder: ir.IRBuilder = None, size=None):
        super().__init__(value, builder, size)
        self.should_offset = None
    def get_element(self, builder: ir.IRBuilder, index):
        if self.should_offset == None:
            self.should_offset = is_64_bit and self.elm_type.llvmtype.get_abi_size(bi.target_data) < 8
        if self.should_offset:
            array_buff = self.get_array_buff_ptr(builder).load_at_index(builder)
            buff_ptr = FloMem.bitcast(builder, array_buff, ir.IntType(64).as_pointer()) 
        else:
            buff_ptr = self.get_array(builder)
        value = buff_ptr.load_at_index(builder, index)
        if self.should_offset:
            value = builder.trunc(value, self.elm_type.llvmtype)
        if inspect.isclass(self.elm_type):
            return self.elm_type(value)
        return self.elm_type.new(value)



class FloRef:
    def __init__(self, builder: ir.IRBuilder, referee: FloType, name='', is_constant=False):
        self.builder = builder
        self.referee = referee
        if not is_constant:
            self.addr = FloMem.salloc(builder, referee.llvmtype)
            self.store(referee)
        else:
            self.addr = name

    def load(self):
        self.referee.value = self.addr.load_at_index(self.builder)
        return self.referee

    def store(self, referee: FloType):
        self.addr.store_at_index(self.builder, referee)


class FloFunc(FloType):
    defined_methods = {}

    def get_llvm_type(self):
        arg_types = [arg_ty.llvmtype for arg_ty in self.arg_types]
        if self.var_args:
            arg_types.append(FloInt.llvmtype)
        return ir.FunctionType(self.return_type.llvmtype, arg_types, var_arg=self.var_args)

    def __init__(self, arg_types: List, return_type, name, var_args=False):
        self.sym_tbl = None
        self.return_type = return_type
        self.var_args = False
        if var_args:
            self.var_arg_ty = arg_types.pop()
            self.var_args = True
        self.arg_types = arg_types
        fn_type = self.get_llvm_type()
        self.llvmtype = fn_type.as_pointer()
        if name:
            current_module = Context.current_llvm_module
            value = ir.Function(current_module, fn_type, name)
            self.mem = FloMem(value)
            fn_entry_block = value.append_basic_block()
            self.builder = ir.IRBuilder(fn_entry_block)

    def call(self, builder: ir.IRBuilder, args):
        passed_args = [arg.value for arg in args]
        if self.var_args:
            passed_args.insert(
                0, FloInt(len(passed_args)-len(self.value.args)+1).value)
        rt_value = builder.call(self.mem.value, passed_args)
        if self.return_type == FloVoid:
            return FloVoid
        return self.to_flo(self.return_type, rt_value)

    def to_flo(self, val_type, value):
        if inspect.isclass(val_type):
            if value.type.is_pointer:
                value = FloMem(value)
            return val_type(value)
        else:
            return val_type.new(FloMem(value))

    # TODO: Get rid of this block.
    def get_symbol_table(self, parent_symbol_table: SymbolTable, arg_names: List(str)):
        va_name = None
        if self.var_args:
            va_name = arg_names.pop()
        self.arg_names = arg_names
        self.sym_tbl = parent_symbol_table.copy()
        for arg_name, arg_type, arg_value in zip(arg_names, self.arg_types, self.mem.value.args):
            arg_val = self.to_flo(arg_type, arg_value)
            self.sym_tbl.set(arg_name, FloRef(self.builder, arg_val, arg_name))
        if va_name != None:
            va_args_mem = FloMem.salloc(self.builder, va_list_t)
            self.va_arg = FloMem.bitcast(
                self.builder, va_args_mem, bi.i8_ptr_ty)
            self.builder.call(bi.get_instrinsic(
                "va_start"), [self.va_arg.value])
            va_mem = va_args_mem.load_at_index(self.builder, FloInt(0), FloInt(0))
            if self.value.name == "main":
                va_mem = FloMem.bitcast(self.builder, va_mem, bi.i8_ptr_ty.as_pointer()).load_at_index(self.builder)
            length = FloInt(self.value.args[0])
            va_mem = FloArray.create_array_struct(
                self.builder, va_mem, length, length)
            va_list = FloArgArray(va_mem)
            va_list.elm_type = self.var_arg_ty
            self.sym_tbl.set(va_name, va_list)

        return self.sym_tbl

    def new(self, val):
        new_fnc = FloFunc(self.arg_types, self.return_type, None)
        new_fnc.value = val
        return new_fnc

    def ret(self, value, b=None):
        if self.var_args:
            self.builder.call(bi.get_instrinsic("va_end"), [self.va_arg.value])
        if value == FloVoid:
            return self.builder.ret_void()
        else:
            return self.builder.ret(value.value)

    @property
    def value(self):
        return self.mem.value

    @value.setter
    def value(self, new_mem):
        self.mem = new_mem

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
    def __init__(self, call, arg_types, return_type, var_args=False, defaults=[]):
        self.arg_types = arg_types
        self.return_type = return_type
        self.var_args = var_args
        self.defaults = defaults
        self.sym_tbl = None
        self.llvmtype = self.get_llvm_type().as_pointer()
        self.call_method = call
        if return_type == FloVoid:
            self.returned = FloVoid
        else:
            self.returned = None

    def call(self, *kargs):
        if self.call_method:
            returned = self.call_method(*kargs)
            if returned != None:
                return returned
        else:
            return FloVoid
        return self.returned.load() if self.returned != FloVoid else FloVoid

    def ret(self, value, builder):
        if self.returned != FloVoid:
            if self.returned == None:
                self.returned = FloRef(builder, value)
            else:
                self.returned.store(value)
