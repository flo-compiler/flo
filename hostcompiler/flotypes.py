from typing import List
import builtIns as bi
from context import Context
from llvmlite import ir
from typing import Union


def create_array_buffer(builder: ir.IRBuilder, elems):
    elm_ty = elems[0].llvmtype
    mem = FloMem.halloc(builder, elm_ty, FloInt(len(elems)))
    for index, elem in enumerate(elems):
        mem.store_at_index(builder, elem, FloInt(index, 32))
    return mem

def strict_mem_compare(builder: ir.IRBuilder, o1, o2):    
    my_int = FloInt(builder.ptrtoint(o1.mem.value, ir.IntType(32)), 32)
    other_int = FloInt(builder.ptrtoint(o2.mem.value, ir.IntType(32)), 32)
    return my_int.cmp(builder, "==", other_int)

def is_string_object(type):
    return isinstance(type, FloObject) and type.referer.name == 'string'

# TODO
def str_to_int(builder: ir.IRBuilder, str_obj, bits):
    val = builder.call(bi.get_instrinsic("atoi"), [str_obj.cval(builder)])
    return FloInt(val, 32).cast_to(builder, FloInt(None, bits))

def str_to_float(builder, str_obj, bits):
    val = builder.call(bi.get_instrinsic("atof"), [str_obj.cval(builder)])
    return FloFloat(val, 64).cast_to(builder, FloFloat(None, bits))
    

def create_string_object(builder, args):
    str_class = FloClass.classes.get("string")
    return FloObject(str_class).construct(builder, args)


class FloType:
    llvmtype: ir.Type = None
    value: ir.Value

    def __init__(self, value) -> None:
        self.fmt = "%s"
        self.value = value

    def cast_to():
        raise Exception("undefined cast")

    @staticmethod
    def str():
        return "any"

    def store_value_to_ref(self, ref):
        if not ref.mem:
            ref.mem = FloMem.salloc(ref.builder, self.llvmtype, name= ref.name)
        ref.mem.store_at_index(ref.builder, self)

    def load_value_from_ref(self, ref):
        return self.__class__(ref.mem.load_at_index(ref.builder))

    def construct(self, builder: ir.IRBuilder, args):
        ptr = FloPointer(self)
        ptr.mem = FloMem.halloc(builder, self.llvmtype, args[0])
        return ptr
    
    def cval(self, _):
        return self.value

class FloNull(FloType):
    def __init__(self, base_type: FloType) -> None:
        if base_type:
            self.llvmtype = base_type.llvmtype
        self.base_type = base_type
        zero = ir.Constant(ir.IntType(32), 0)
        if isinstance(base_type, FloInt):
            self.floval = FloInt(0, base_type.bits)
        elif isinstance(base_type, FloFloat):
            self.floval = FloFloat(0.0, base_type.bits)
        elif isinstance(base_type, FloPointer) or isinstance(base_type, FloObject) or isinstance(base_type, FloFunc):
            self.floval = base_type.new_with_val(zero.inttoptr(base_type.llvmtype))

    @property
    def value(self):
        return self.floval.value
    def store_value_to_ref(self, ref):
        return self.floval.store_value_to_ref(ref)

    def load_value_from_ref(self, ref):
        return self.floval.load_value_from_ref(ref)
    
    def __eq__(self, __o: object) -> bool:
        return self.floval.__eq__(__o)
    


class FloVoid(FloType):
    llvmtype = ir.VoidType()

    def to_string(builder):
        mem = FloConst.create_global_str("null")
        length = FloInt(4)
        return create_string_object(builder, [mem, length])

    def str(self) -> str:
        return "void"

    def cast_to(self, builder, new_ty):
        if is_string_object(new_ty):
            return self.to_string(builder)
        else:
            raise Exception("undefined case")
    
    def cval(self, _):
        return FloConst.create_global_str("null").value

    def __eq__(self, __o: object) -> bool:
        return isinstance(__o, FloVoid)


class FloConst:
    # TODO be careful with arrays and strings
    str_constants = {}

    def __init__(self, value) -> None:
        self.value = value

    def load(self, visitor):
        return visitor.visit(self.value)

    @staticmethod
    def create_global_str(value: str):
        if(FloConst.str_constants.get(value) != None):
            str_ptr = FloConst.str_constants.get(value)
        else:
            encoded = (value+'\0').encode(
                encoding="utf-8", errors="xmlcharrefreplace"
            )
            byte_array = bytearray(encoded)
            str_val = ir.Constant(
                ir.ArrayType(bi.byte_ty, len(byte_array)), byte_array
            )
            name = f"str.{len(FloConst.str_constants.keys())}"
            str_ptr = ir.GlobalVariable(
                Context.current_llvm_module, str_val.type, name
            )
            str_ptr.linkage = "private"
            str_ptr.global_constant = True
            str_ptr.unnamed_addr = True
            str_ptr.initializer = str_val
            str_ptr = str_ptr.bitcast(bi.byteptr_ty)
            FloConst.str_constants[value] = str_ptr
        flo_ptr = FloMem(str_ptr)
        flo_ptr.is_constant = True
        return flo_ptr


class FloInt(FloType):
    def __init__(self, value: int, bits=bi.machine_word_size):
        assert bits > 0 and bits < 128
        self.bits = bits
        if isinstance(value, int):
            self.value = ir.Constant(self.llvmtype, int(value))
        else:
            if isinstance(value, ir.Value):
                self.bits = value.type.width
            self.value = value
    
    def new_with_val(self, value):
        return FloInt(value, self.bits)

    @property
    def fmt(self):
        return "%s" if self.bits == 1 else "%d"

    def cval(self, builder):
        return self.value if self.bits != 1 else self.bool_value(builder)

    @property
    def llvmtype(self):
        return ir.IntType(self.bits)

    @property
    def is_constant(self):
        return isinstance(self.value, ir.Constant) and self.value.constant

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
            return FloInt(0, 1)
        return FloInt(builder.icmp_signed(op, self.value, num.value), 1)

    def neg(self, builder: ir.IRBuilder):
        self.value = builder.neg(self.value)
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
        if isinstance(type, FloInt):
            return self.bitcast(builder, type.bits)
        elif isinstance(type, FloFloat):
            return FloFloat(builder.sitofp(self.value, type.llvmtype))
        elif is_string_object(type):
            return self.to_string(builder)
        else:
            raise Exception(f"Unhandled type cast: int to {type.str()}")

    def bitcast(self, builder: ir.IRBuilder, bits: int):
        llvmtype = ir.IntType(bits)
        if bits != self.bits:
            if self.is_constant:
                return FloInt(self.value.constant, bits)
            cast_fnc = builder.trunc if bits < self.bits else builder.zext
            return FloInt(cast_fnc(self.value, llvmtype), bits)
        else:
            return self

    def bool_value(self, builder: ir.IRBuilder):
        return builder.select(self.value, FloConst.create_global_str(
            "true").value, FloConst.create_global_str("false").value)

    def to_bool_string(self, builder: ir.IRBuilder):
        value = self.bool_value(builder)
        lenval = builder.select(self.value, FloInt(4).value, FloInt(5).value)
        mem = FloMem(value)
        return create_string_object(builder, [mem, FloInt(lenval)])

    def to_string(self, builder: ir.IRBuilder):
        if self.bits == 1:
            return self.to_bool_string(builder)
        sprintf = bi.get_instrinsic("sprintf")
        str_buff = FloMem.halloc_size(builder, FloInt(10))
        fmt = FloConst.create_global_str(self.fmt)
        strlen = FloInt(builder.call(
            sprintf, [str_buff.value, fmt.value, self.value]))
        return create_string_object(builder, [str_buff, strlen])

    def str(self) -> str:
        if self.bits == 1:
            return "bool"
        elif self.bits == bi.machine_word_size:
            return "int"
        else:
            return f"i{self.bits}"

    def __eq__(self, __o: object) -> bool:
        if isinstance(__o, FloNull):
            return __o == self
        return isinstance(__o, FloInt) and __o.bits == self.bits

    def new(self, value):
        return FloInt(value, self.bits)


class FloFloat(FloType):
    def __init__(self, value: Union[float, ir.Constant], bits=bi.machine_word_size):
        assert bits == 16 or bits == 32 or bits == 64
        self.bits = bits
        self.fmt = "%.1lf"
        if isinstance(value, float):
            self.value = ir.Constant(self.llvmtype, value)
        else:
            self.value = value

    def new_with_val(self, value):
        return FloFloat(value, self.bits)

    def cval(self, _):
        return self.value

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
            return FloInt(0, 1)
        return FloInt(builder.fcmp_ordered(op, self.value, num.value), 1)

    def mod(self, builder: ir.IRBuilder, num):
        return FloFloat(builder.frem(self.value, num.value))

    def pow(self, builder: ir.IRBuilder, num):
        v = builder.call(bi.get_instrinsic("pow"), [self.value, num.value])
        return FloFloat(v)

    def neg(self, builder: ir.IRBuilder):
        self.value = builder.fneg(self.value)
        return self

    def cast_to(self, builder: ir.IRBuilder, type):
        if isinstance(type, FloInt):
            return FloInt(builder.fptosi(self.value, type.llvmtype))
        if isinstance(type, FloFloat) and type.bits == self.bits:
            return self
        elif isinstance(type, FloFloat) and type.bits != self.bits:
            return FloFloat(builder.bitcast(self.value, type.llvmtype), type.bits)
        elif is_string_object(type):
            return self.to_string(builder)
        else:
            raise Exception(f"Unhandled type cast: float to {type.str()}")

    def __eq__(self, __o: object) -> bool:
        if isinstance(__o, FloNull):
            return __o == self
        return isinstance(__o, FloFloat) and __o.bits == self.bits

    def to_string(self, builder: ir.IRBuilder):
        sprintf = bi.get_instrinsic("sprintf")
        str_buff = FloMem.halloc_size(builder, FloInt(1))
        fmt = FloConst.create_global_str(self.fmt)
        length = builder.call(sprintf, [str_buff.value, fmt.value, self.value])
        return create_string_object(builder, [str_buff, FloInt(length)])

    def new(self, value):
        return FloFloat(value, self.bits)

    def str(self) -> str:
        if self.bits == bi.machine_word_size:
            return "float"
        else:
            return f"float{self.bits}"

    @property
    def is_constant(self):
        return isinstance(self.value, ir.Constant)

    @property
    def llvmtype(self):
        if self.bits == 16:
            return ir.HalfType()
        elif self.bits == 32:
            return ir.FloatType()
        else:
            return ir.DoubleType()


class FloMem:
    def __init__(self, value):
        assert not isinstance(value, FloMem)
        if value:
            assert isinstance(value.type, ir.PointerType) or isinstance(
                value.type, ir.ArrayType)
        self.is_constant = False
        self.value = value

    def get_pointer_at_index(self, builder: ir.IRBuilder, *indices: FloInt):
        if len(list(indices)) == 0:
            return self
        ir_indices = [index.value for index in indices]
        return FloMem(builder.gep(self.value, ir_indices, True))

    def store_at_index(self, builder: ir.IRBuilder, floval: FloType, *indices: FloInt):
        idx_ptr = self
        if indices:
            idx_ptr = self.get_pointer_at_index(builder, *indices)
        builder.store(floval.value, idx_ptr.value)

    def load_at_index(self, builder: ir.IRBuilder, *indices: FloInt):
        ptr = self
        if indices:
            ptr = self.get_pointer_at_index(builder, *indices)
        loaded_value = builder.load(ptr.value)
        if loaded_value.type.is_pointer or isinstance(loaded_value.type, ir.ArrayType):
            return FloMem(loaded_value)
        return loaded_value

    def cmp(self, builder: ir.IRBuilder, mem2, size: FloInt):
        args = [self.value, mem2.value, size.value]
        res = builder.call(bi.get_instrinsic("memcmp"), args)
        return FloInt(res).cmp(builder, "==", FloInt(0))

    def copy_to(self, builder: ir.IRBuilder, dest, size: FloInt):
        args = [dest.value, self.value,  size.value, FloInt(0, 1).value]
        builder.call(bi.get_instrinsic("memcpy"), args)

    def free(self, builder: ir.IRBuilder):
        if FloMem.heap_allocations.get(self.uuid) != None:
            i8_ptr = builder.bitcast(self.value, bi.byteptr_ty)
            builder.call(bi.get_instrinsic("free"), [i8_ptr])

    @staticmethod
    def bitcast(builder: ir.IRBuilder, mem, ir_type: ir.Type):
        return FloMem(builder.bitcast(mem.value, ir_type))

    @staticmethod
    def halloc_size(builder: ir.IRBuilder, size: FloInt, name=''):
        malloc_fnc = bi.get_instrinsic("malloc")
        return FloMem(builder.call(malloc_fnc, [size.value], name))

    @staticmethod
    def halloc(builder: ir.IRBuilder, ir_type: ir.Type, size: FloInt = None, name=''):
        abi_size = FloInt(ir_type.get_abi_size(bi.target_data))
        if size:
            size = size.mul(builder, abi_size)
        else:
            size = abi_size
        mem_obj = FloMem.halloc_size(builder, size, name)
        return FloMem.bitcast(builder, mem_obj, ir_type.as_pointer())

    @staticmethod
    def salloc(builder: ir.IRBuilder, ir_type: ir.Type, size: FloInt = None, name=''):
        size_value = size.value if size else None
        ty_ptr = builder.alloca(ir_type, size=size_value, name=name)
        return FloMem(ty_ptr)

    @staticmethod
    def realloc(builder: ir.IRBuilder, mem, size: FloInt):
        realloc = bi.get_instrinsic("realloc")
        size  = size.mul(builder, FloInt(mem.value.type.get_abi_size(bi.target_data)))
        old_mem = FloMem.bitcast(builder, mem, bi.byteptr_ty).value
        new_mem = builder.call(realloc, [old_mem, size.value])
        return FloMem.bitcast(builder, FloMem(new_mem), mem.value.type)


class FloPointer(FloType):
    def __init__(self, flotype: FloType) -> None:
        self.is_constant = False
        self.elm_type = flotype
        self.mem = None
        self.methods = {}
        self.init_methods()
        self.fmt = "%X"

    def new_with_val(self, value):
        return self.new(FloMem(value))

    def init_methods(self):
        resize_call = lambda builder, args: self.new(FloMem.realloc(builder, self.mem, args[0]))
        resize_fnc = FloInlineFunc(resize_call, [FloInt(None)], self)
        self.methods["resize"] = resize_fnc

    @property
    def value(self):
        return self.mem.value

    @value.setter
    def value(self, n_val):
        self.mem = FloMem(n_val)

    @property
    def llvmtype(self):
        return self.elm_type.llvmtype.as_pointer()

    def store_value_to_ref(self, ref):
        if not ref.mem:
            ref.mem = FloMem.salloc(ref.builder, self.llvmtype, name=ref.name)
        if self.mem:
            ref.mem.store_at_index(ref.builder, self)

    def load_value_from_ref(self, ref):
        return self.new(ref.mem.load_at_index(ref.builder))

    def new(self, mem):
        ptr = FloPointer(self.elm_type)
        ptr.mem = mem
        return ptr

    def get_element(self, builder: ir.IRBuilder, index: FloInt):
        mem = self.mem.get_pointer_at_index(builder, index)
        return self.elm_type.load_value_from_ref(FloRef(builder, self.elm_type, '', mem))

    def add(self, builder: ir.IRBuilder, increment: FloInt):
        return self.new(self.mem.get_pointer_at_index(builder, increment))

    def sub(self, builder: ir.IRBuilder, increment: FloInt):
        return self.new(self.mem.get_pointer_at_index(builder, increment.neg(builder)))

    def set_element(self, builder: ir.IRBuilder, index: FloInt, value: FloType):
        self.mem.store_at_index(builder, value, index)
        return value

    def __eq__(self, __o: object) -> bool:
        if isinstance(__o, FloNull):
            return __o == self
        return isinstance(__o, FloPointer) and self.elm_type == __o.elm_type

    def get_pointer_at_index(self, builder: ir.IRBuilder, index: FloInt):
        return self.new(self.mem.get_pointer_at_index(builder, index))

    def cast_to(self, builder: ir.IRBuilder, type):
        if isinstance(type, FloObject):
            return type.new_with_val(FloMem.bitcast(builder, self.mem, type.llvmtype).value)
        if isinstance(type, FloFunc):
            return type.new_with_val(FloMem.bitcast(builder, self.mem, type.llvmtype).value)
        if not isinstance(type, FloPointer):
            raise Exception("Cannot cast")
        else:
            return FloPointer(type.elm_type).new(FloMem.bitcast(builder, self.mem, type.llvmtype))

    def str(self):
        return f"{self.elm_type.str()}*"
    

class FloArray:
    def __init__(self, values, arr_len=None):
        self.mem = None
        if isinstance(values, list):
            self.is_constant = True
            self.elm_type = values[0] if len(values) > 0 else None
            self.is_constant = FloArray.is_constant(values)
            self.elems = values
            self.len = FloInt(len(values)) if arr_len == None else arr_len
        else:
            self.len: FloInt = arr_len
            self.elems = values
            self.is_constant = False

    def new_with_val(self, value):
        arr = FloArray(self.value, self.len)
        arr.value = value
        return arr

    @staticmethod
    def is_constant(values):
        for v in values:
            if not v.is_constant:
                return False
        return True

    def cmp(self, builder, op, other):
        if isinstance(other, FloArray):
            #TODO:
            return FloInt(0, 1)
        else:
            return FloInt(0, 1)

    @property
    def value(self):
        if self.mem:
            return self.mem.value
        if self.elems:
            return ir.Constant(self.llvmtype.pointee, [elm.value for elm in self.elems])
        return None


    @value.setter
    def value(self, new_value):
        assert new_value
        self.mem = FloMem(new_value)
    
    def get_index(self, idx: FloInt):
        return [FloInt(0, idx.bits), idx] if not self.mem or isinstance(self.mem.value.type, ir.ArrayType) else [idx]

    def store_value_to_ref(self, ref):
        builder: ir.IRBuilder = ref.builder
        if not ref.mem and not self.mem:
            if self.len.is_constant:
                ty = ir.ArrayType(self.elm_type.llvmtype, self.len.value.constant)
                ref.mem = FloMem.salloc(builder, ty, name=ref.name)
            else:
                # call stacksave and stackrestore at the end of function call.
                self.mem = FloMem.salloc(builder, self.llvmtype.pointee, self.len, ref.name)
        if self.is_constant and self.len.is_constant and self.value:
            ref.mem.store_at_index(builder, FloType(self.value), FloInt(0))
        elif self.elems and len(self.elems) > 0:
            next_idx = self.get_index(FloInt(0, 32))
            tmp_mem = self.mem or ref.mem
            for floval in self.elems:
                tmp_mem = tmp_mem.get_pointer_at_index(builder, *next_idx)
                next_idx = [FloInt(1, 32)]
                floval.store_value_to_ref(
                    FloRef(builder, floval, '', tmp_mem))

    @property
    def llvmtype(self):
        return self.elm_type.llvmtype.as_pointer()

    def load_value_from_ref(self, ref):
        loaded_array = FloArray(self.elems, self.len)
        if ref.mem:
            if ref.mem.value.type.pointee.is_pointer:
                loaded_array.mem = ref.mem.load_at_index(ref.builder, FloInt(0, 32))
            else:
                loaded_array.mem = ref.mem.get_pointer_at_index(ref.builder, *self.get_index(FloInt(0, 32)))
        elif not ref.mem:
            loaded_array.mem = self.mem
        loaded_array.elm_type = self.elm_type
        return loaded_array

    def get_element(self, builder: ir.IRBuilder, index: FloInt):
        value = self.mem.get_pointer_at_index(builder, *self.get_index(index))
        return self.elm_type.load_value_from_ref(FloRef(builder, self.elm_type, '', value))

    def set_element(self, builder: ir.IRBuilder, index, value):
        self.mem.store_at_index(builder, value, *self.get_index(index))
        return value

    def get_pointer_at_index(self, builder: ir.IRBuilder, index):
        mem = self.mem.get_pointer_at_index(builder, *self.get_index(index))
        return FloPointer(self.elm_type).new(mem)

    def str(self) -> str:
        return f"{self.elm_type.str()}[]"

    def __eq__(self, __o: object) -> bool:
        if isinstance(__o, FloNull):
            return __o == self
        return isinstance(__o, FloArray) and self.elm_type == __o.elm_type


class FloRef:
    def __init__(self, builder: ir.IRBuilder, referee: FloType, name='', mem=None):
        self.builder = builder
        self.name = name
        self.mem = mem
        if not mem:
            self.store(referee)
        self.referee = referee

    def load(self):
        return self.referee.load_value_from_ref(self)

    def store(self, referee: FloType):
        referee.store_value_to_ref(self)


class FloFunc(FloType):
    defined_methods = {}

    def get_llvm_type(self):
        arg_types = [arg_ty.llvmtype for arg_ty in self.arg_types]
        if self.var_args:
            arg_types.append(FloInt.llvmtype)
        return ir.FunctionType(self.return_type.llvmtype, arg_types, var_arg=self.var_args)
        
    def cval(self, builder):
        return FloConst.create_global_str(self.str()).value

    def new_with_val(self, value):
        fnc = FloFunc(self.arg_types, self.return_type, self.name)
        fnc.value = value
        return fnc

    def __init__(self, arg_types: List, return_type, name, var_args=False):
        self.fmt = "%s"
        self.return_type = return_type
        self.var_args = False
        if var_args:
            self.var_arg_ty = arg_types.pop()
            self.var_args = True
        self.arg_types = arg_types
        if name:
            self.context = None
            current_module = Context.current_llvm_module
            self.value = ir.Function(
                current_module, self.get_llvm_type(), name)
            fn_entry_block = self.value.append_basic_block()
            self.builder = ir.IRBuilder(fn_entry_block)

    @staticmethod
    def declare(arg_types: List, return_type, name, var_args=False):
        n_arg_types = [arg_ty.llvmtype for arg_ty in arg_types]
        fn_ty = ir.FunctionType(return_type.llvmtype,
                                n_arg_types, var_arg=var_args)
        val = Context.current_llvm_module.declare_intrinsic(name, (), fn_ty)
        new_fnc = FloFunc(arg_types, return_type, None)
        new_fnc.value = val
        return new_fnc

    def call(self, builder: ir.IRBuilder, args):
        passed_args = [arg.value for arg in args]
        rt_value = builder.call(self.value, passed_args)
        if isinstance(self.return_type, FloVoid):
            return FloVoid(rt_value)
        return self.return_type.new_with_val(rt_value)
        

    def __eq__(self, __o: object) -> bool:
        if isinstance(__o, FloNull):
            return __o == self
        if not isinstance(__o, FloFunc):
            return False
        if self.return_type != __o.return_type:
            return False
        if len(self.arg_types) != len(__o.arg_types):
            return False
        for argty1, argty2 in zip(self.arg_types, __o.arg_types):
            if argty1 != argty2:
                return False
        return True

    def get_local_ctx(self, parent_ctx: Context, arg_names: List[str]):
        self.arg_names = arg_names
        local_ctx = parent_ctx.create_child(self.value.name)
        for arg_name, arg_type, arg_value in zip(arg_names, self.arg_types, self.value.args):
            if isinstance(arg_type, FloFunc):
                arg_type = FloFunc(
                    arg_type.arg_types, arg_type.return_type, None, arg_type.var_args)
            arg_type.value = arg_value
            local_ctx.set(arg_name, FloRef(self.builder, arg_type, arg_name))
        self.context = local_ctx
        return local_ctx

    def ret(self, value):
        if isinstance(value, FloVoid):
            self.builder.ret_void()
        else:
            self.builder.ret(value.value)

    @property
    def llvmtype(self):
        return self.get_llvm_type().as_pointer()

    def load_value_from_ref(self, ref):
        loaded_func = FloFunc(
            self.arg_types, self.return_type, None, self.var_args)
        loaded_func.value = ref.mem.load_at_index(ref.builder).value
        return loaded_func

    def str(self) -> str:
        arg_list = ", ".join([arg.str() for arg in self.arg_types])
        return f"({arg_list}) => {self.return_type.str()}"


vtable_offset = 1


class FloClass:
    classes = {}

    def __init__(self, name, parent=None, init_body=True) -> None:
        self.name = name
        self.methods: dict[str, FloMethod] = {}
        self.properties: dict[str, FloType] = {}
        self.value = ir.global_context.get_identified_type(name)
        self.constructor = None
        self.vtable_ty = None
        self.vtable_data = None
        self.parent = parent
        if parent:
            self.properties.update(parent.properties)
            if init_body: self.methods.update(self.parent.methods)
        if init_body:
            FloClass.classes[name] = self

    def get_method(self, method_name: str):
        current = self
        while current.methods.get(method_name) == None and current.parent:
            current = current.parent
        return current.methods.get(method_name)
    

    def add_method(self, fnc: FloFunc):
        # prepend this in args
        assert isinstance(fnc, FloMethod)
        assert fnc.value
        if fnc.value.name == self.name+'_constructor':
            self.constructor = fnc
        else:
            self.methods[fnc.original_name] = fnc

    def add_property(self, name, value):
        self.properties[name] = value

    @property
    def llvmtype(self):
        return self.value.as_pointer()

    @staticmethod
    def get_methods(flo_class):
        if flo_class == None:
            return {}
        methods = FloClass.get_methods(flo_class.parent)
        for key in flo_class.methods:
            func = flo_class.methods.get(key)
            methods[key] = FloInlineFunc(
                None, [flo_class]+func.arg_types, func.return_type, func.var_args, func.defaults)
        return methods

    def init_value(self):
        self.vtable_ty = ir.global_context.get_identified_type(
            f"{self.name}_vtable_ty")
        vtable_tys = [method.llvmtype for method in self.methods.values()]
        self.vtable_ty.set_body(*vtable_tys)
        fields = [value.llvmtype for value in self.properties.values()]
        fields.insert(0, self.vtable_ty.as_pointer())
        self.value.set_body(*fields)
        self.vtable_data = ir.GlobalVariable(
            Context.current_llvm_module, self.vtable_ty, f"{self.name}_vtable_data")
        self.vtable_data.initializer = ir.Constant(
            self.vtable_ty, [func.value for func in self.methods.values()])

    def constant_init(self, builder: ir.IRBuilder, args):
        # TODO: Decide when to allocate on the heap
        ptr_value = FloMem.halloc(builder, self.value)
        is_constant = FloArray.is_constant(args)
        if is_constant:
            constant = ir.Constant(self.value, [self.vtable_data]+[arg.value for arg in args])
            ptr_value.store_at_index(builder, FloType(constant))
        else:
            self.set_vtable_data(builder, ptr_value)
            for index, arg in enumerate(args):
                ptr_value.store_at_index(
                    builder, arg, FloInt(0, 32), FloInt(index + vtable_offset, 32))
        obj = FloObject(self)
        obj.mem = ptr_value
        return obj

    def set_vtable_data(self, builder: ir.IRBuilder, mem: FloMem):
        mem.store_at_index(
            builder, FloType(self.vtable_data), FloInt(0, 32), FloInt(0, 32))

    def has_parent(self, other):
        current = self
        while current.parent:
            if current.parent.name == other.name:
                return True
            current = current.parent
        return False


class FloMethod(FloFunc):
    def __init__(self, arg_types: List, return_type, name, var_args=False, class_: FloClass = None):
        if name:
            if class_:
                self.original_name = name
                name = class_.name + "_" + name
                arg_types.insert(0, FloObject(class_))
                self.class_ = class_
            self.current_object = None
        else:
            self.value = var_args
            var_args = None
        super().__init__(arg_types, return_type, name, var_args)
    
    @staticmethod
    def declare(arg_types: List, return_type, name, var_args, class_):
        n_arg_types = [FloObject(class_).llvmtype]+[arg_ty.llvmtype for arg_ty in arg_types]
        name = class_.name + "_" + name
        fn_ty = ir.FunctionType(return_type.llvmtype,
                                n_arg_types, var_arg=var_args)
        val = Context.current_llvm_module.declare_intrinsic(name, (), fn_ty)
        new_fnc = FloMethod(arg_types, return_type, None, val, class_)
        return new_fnc

    def call(self, builder: ir.IRBuilder, args):
        return super().call(builder, [self.current_object] + args)

    def get_local_ctx(self, parent_ctx: Context, arg_names: List[str]):
        local_ctx = super().get_local_ctx(parent_ctx, ["this"] + arg_names)
        if self.class_ and self.class_.parent:
            parent_constructor = self.class_.parent.constructor
            if parent_constructor:
                parent_constructor.current_object = local_ctx.get("this").load().cast_to(
                    self.builder, FloObject(self.class_.parent))
                local_ctx.set("super", parent_constructor)
        return local_ctx

    def load_value_from_ref(self, ref):
        loaded_func = FloMethod(
            self.arg_types, self.return_type, None, ref.mem.load_at_index(ref.builder).value, None)
        loaded_func.current_object = self.current_object
        return loaded_func


class FloObject(FloType):
    def __init__(self, referer: FloClass) -> None:
        self.fmt = "%s"
        self.referer = referer
        self.is_constant = False
        self.mem = None
        assert (referer)
        if not isinstance(referer.value, str):
            self.llvmtype = referer.value.as_pointer()
    
    
    def new_with_val(self, value):
        obj = FloObject(self.referer)
        obj.mem = FloMem(value)
        return obj


    def store_value_to_ref(self, ref):
        if not ref.mem:
            ref.mem = FloMem.salloc(ref.builder, self.llvmtype, name=ref.name)
        if self.mem:
            ref.mem.store_at_index(ref.builder, self)

    def load_value_from_ref(self, ref):
        loaded_object = FloObject(self.referer)
        loaded_object.mem = ref.mem.load_at_index(ref.builder)
        return loaded_object
    
    def in_(self, builder: ir.IRBuilder, member):
        in_method = self.get_method("__in__", builder)
        return in_method.call(builder, [member])

    @property
    def value(self):
        return self.mem.value

    @value.setter
    def value(self, n_val):
        self.mem = FloMem(n_val)

    def get_property_mem(self, builder: ir.IRBuilder, name):
        property_index = list(self.referer.properties.keys()).index(name)
        return self.mem.get_pointer_at_index(
            builder, FloInt(0, 32), FloInt(property_index + vtable_offset, 32))

    def get_property(self, builder: ir.IRBuilder, name):
        try:
            mem = self.get_property_mem(builder, name)
        except Exception:
            return self.get_method(name, builder)
        property_value: FloType = self.referer.properties.get(name)
        return property_value.load_value_from_ref(FloRef(builder, property_value, '', mem))

    def get_method(self, name, builder: ir.IRBuilder) -> Union[FloMethod, None]:
        assert isinstance(self.referer, FloClass)
        method_index = -1
        current = self.referer
        while current:
            method = current.methods.get(name)
            if method != None:
                method_index = list(self.referer.methods.keys()).index(name)
                break
            else:
                current = current.parent
        method_value: FloType = self.referer.methods.get(name)
        if method_value == None:
            # 1: Find where this goes wrong
            self.referer = FloClass.classes.get(self.referer.name)
            current = self.referer
            method_value = current.methods.get(name)
            if method_value == None: return None
            # 1: Fix it.
            method_index = list(current.methods.keys()).index(name)

        vtable_ptr = self.mem.load_at_index(
            builder, FloInt(0, 32), FloInt(0, 32)
        )
        method_mem = vtable_ptr.get_pointer_at_index(
            builder, FloInt(0, 32), FloInt(method_index, 32))
        flomethod = method_value.load_value_from_ref(
            FloRef(builder, method_value, '', method_mem))
        flomethod.current_object = self.cast_to(builder, FloObject(
            current)) if self.referer != current else self
        return flomethod

    def sl(self, builder: ir.IRBuilder, other: FloType):
        return self.get_method("__sl__", builder).call(builder, [other])

    def set_property(self, builder: ir.IRBuilder, name: str, value: FloType):
        property_index = list(self.referer.properties.keys()).index(name)
        mem = self.mem.get_pointer_at_index(
            builder, FloInt(0, 32), FloInt(property_index + vtable_offset, 32))
        value.store_value_to_ref(FloRef(builder, value, '', mem))
        return value

    def construct(self, builder: ir.IRBuilder, args):
        self.mem = FloMem.halloc(builder, self.referer.value)
        self.referer.set_vtable_data(builder, self.mem)
        if self.referer.constructor:
            self.referer.constructor.current_object = self
            self.referer.constructor.call(builder, args)
        return self

    def str(self) -> str:
        return self.referer.name if isinstance(self.referer, FloClass) else self.referer.value

    def __eq__(self, other: object) -> bool:
        if isinstance(other, FloNull):
            return other == self
        if not other:
            return False
        if not isinstance(other, FloObject):
            return False
        self_classname = self.referer.name
        other_classname = other.referer.name
        return self_classname == other_classname

    def add(self, builder: ir.IRBuilder, other):
        method = self.get_method("__add__", builder)
        return method.call(builder, [other])

    def cmp(self, builder: ir.IRBuilder, op, other):
        should_not = op == "!="
        if isinstance(other, FloNull):
            value = strict_mem_compare(builder, self, other.floval)
            return value.not_(builder) if should_not else value
        if not isinstance(other, FloObject):
            return FloInt(0, 1)
        if op == "==" or op == "!=":
            eq_method = self.get_method("__eq__", builder)
            other_object: FloObject = other
            if eq_method:
                if len(eq_method.arg_types) > 0 and other_object.referer.has_parent(eq_method.arg_types[0].referer):
                    other_object = other_object.cast_to(builder, eq_method.arg_types[0])
                value = eq_method.call(builder, [other_object])
            else:
                value = strict_mem_compare(builder, self, other_object)
            return value.not_(builder) if should_not else value

    def get_cast_method(self, type, builder):
        name = "__as_"+type.str()+"__"
        return self.get_method(name, builder)

    def cast_to(self, builder: ir.IRBuilder, type):
        if is_string_object(type):
            if is_string_object(self):
                return self
            if self.get_method('__as_string__', builder) == None:
                string = f"@{self.referer.name}"
                return create_string_object(builder, [FloConst.create_global_str(string), FloInt(len(string))])
        elif is_string_object(self):
            if isinstance(type, FloInt):
                return str_to_int(builder, self, type.bits)
            elif isinstance(type, FloFloat):
                return str_to_float(builder, self, type.bits)
        if isinstance(type, FloObject):
            # if(self.referer.has_parent(type.referer)): (Possibly unsafe with check on this line)
            casted_mem = FloMem.bitcast(builder, self.mem, type.llvmtype)
            newObj = FloObject(type.referer)
            newObj.mem = casted_mem
            return newObj
        method: FloMethod = self.get_cast_method(type, builder)
        if method != None:
            return method.call(builder, [])
        else:
            raise Exception("Cannot cast")

    def cval(self, builder: ir.IRBuilder):
        v = self.cast_to(builder, FloObject(FloClass.classes.get("string"))).get_method("to_cstring", builder).call(builder, []).value
        return v

class FloGeneric(FloObject):
    def __init__(self, referer: FloClass, constraints: List[FloType]) -> None:
        self.name = referer.value
        self.constraints = constraints
        super().__init__(referer)
    
    def str(self):
        if isinstance(self.referer, FloClass):
            return self.referer.name
        return self.name +"<"+", ".join([constraint.str() for constraint in self.constraints])+">"


class FloEnum(FloType):
    def __init__(self, elements: List[str]):
        self.elements = elements
        self.global_offset = 0

    def get_property(self, name: str) -> FloInt:
        index = self.elements.index(name)+self.global_offset
        return FloInt(index)

    def str(self):
        return "Enum"


class FloInlineFunc(FloFunc):
    def __init__(self, call, arg_types, return_type, var_args=False, defaults=[]):
        self.arg_types = arg_types
        self.name = ""
        self.return_type = return_type
        self.var_args = var_args
        self.defaults = defaults
        self.call_method = call

    def call(self, *kargs):
        assert self.call_method
        returned = self.call_method(*kargs)
        if returned != None:
            return returned
        else:
            return FloVoid(None)
