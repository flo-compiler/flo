from ast import List
import builtIns as bi
from context import Context
from llvmlite import ir
from typing import Union
from lexer import Token


def create_array_buffer(builder: ir.IRBuilder, elems):
    elm_ty = elems[0].llvmtype
    mem = FloMem.halloc(builder, elm_ty, FloInt(len(elems)))
    for index, elem in enumerate(elems):
        mem.store_at_index(builder, elem, FloInt(index, 32))
    return mem


def is_string_object(type):
    return isinstance(type, FloObject) and type.referer.name == 'string'


def create_string_object(builder, args):
    str_class = FloClass.classes.get("string")
    return FloObject(str_class).construct(builder, args)


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

    def store_value_to_ref(self, ref):
        if not ref.mem:
            ref.mem = FloMem.salloc(ref.builder, self.llvmtype, ref.name)
        ref.mem.store_at_index(ref.builder, self)

    def load_value_from_ref(self, ref):
        return self.__class__(ref.mem.load_at_index(ref.builder))

    def construct(self, builder: ir.IRBuilder, args):
        ptr = FloPointer(self)
        ptr.mem = FloMem.halloc(builder, self.llvmtype, args[0])
        return ptr


class FloVoid(FloType):
    llvmtype = ir.VoidType()

    def to_string(builder):
        mem = FloConst.create_global_str("null")
        length = FloInt(4)
        return create_string_object(builder, [mem, length])

    def str() -> str:
        return "void"

    def cast_to(self, builder, new_ty):
        if is_string_object(new_ty):
            return self.to_string(builder)
        else:
            raise Exception("undefined case")

    def __eq__(self, __o: object) -> bool:
        return isinstance(__o, FloVoid)


class FloConst(FloType):
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
        return flo_ptr


class FloInt(FloType):
    def __init__(self, value: int, bits=bi.machine_word_size):
        assert bits > 0 and bits < 128
        self.bits = bits
        if isinstance(value, int):
            self.value = ir.Constant(self.llvmtype, int(value))
        else:
            self.value = value

    @property
    def llvmtype(self):
        return ir.IntType(self.bits)

    @property
    def is_constant(self):
        return isinstance(self.value, ir.Constant)

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
            cast_fnc = builder.trunc if bits < self.bits else builder.zext
            return FloInt(cast_fnc(self.value, llvmtype), bits)
        else:
            return self

    def to_bool_string(self, builder: ir.IRBuilder):
        value = builder.select(self.value, FloConst.create_global_str(
            "true").value, FloConst.create_global_str("false").value)
        lenval = builder.select(self.value, FloInt(4).value, FloInt(5).value)
        mem = FloMem(value)
        return create_string_object(builder, [mem, FloInt(lenval)])

    def to_string(self, builder: ir.IRBuilder):
        if self.bits == 1:
            return self.to_bool_string(builder)
        sprintf = bi.get_instrinsic("sprintf")
        str_buff = FloMem.halloc_size(builder, FloInt(10))
        fmt = FloConst.create_global_str("%d")
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
        return isinstance(__o, FloInt) and __o.bits == self.bits

    def new(self, value):
        return FloInt(value, self.bits)


class FloFloat(FloType):
    def __init__(self, value: Union[float, ir.Constant], bits=bi.machine_word_size):
        assert bits == 16 or bits == 32 or bits == 64
        self.bits = bits
        if isinstance(value, float):
            self.value = ir.Constant(self.llvmtype, value)
        else:
            self.value = value

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
        elif is_string_object(type):
            return self.to_string(builder)
        else:
            raise Exception(f"Unhandled type cast: float to {type.str()}")

    def __eq__(self, __o: object) -> bool:
        return isinstance(__o, FloFloat) and __o.bits == self.bits

    def to_string(self, builder: ir.IRBuilder):
        sprintf = bi.get_instrinsic("sprintf")
        str_buff = FloMem.halloc_size(builder, FloInt(1))
        fmt = FloConst.create_global_str("%.1lf")
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
        self.value = value

    def get_pointer_at_index(self, builder: ir.IRBuilder, *indices: FloInt):
        if len(list(indices)) == 0:
            return self
        ir_indices = [index.value for index in indices]
        mem = FloMem(builder.gep(self.value, ir_indices, True))
        return mem

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
        new_mem = FloMem(builder.bitcast(mem.value, ir_type))
        return new_mem

    @staticmethod
    def halloc_size(builder: ir.IRBuilder, size: FloInt, name=''):
        malloc_fnc = bi.get_instrinsic("malloc")
        mem_obj = FloMem(builder.call(malloc_fnc, [size.value], name))
        return mem_obj

    @staticmethod
    def halloc(builder: ir.IRBuilder, ir_type: ir.Type, size: FloInt = None, name=''):
        abi_size = FloInt(ir_type.get_abi_size(bi.target_data))
        if size:
            size = size.mul(builder, abi_size)
        else:
            size = abi_size
        mem_obj = FloMem.halloc_size(builder, size, name)
        mem_obj = FloMem.bitcast(builder, mem_obj, ir_type.as_pointer())
        return mem_obj

    @staticmethod
    def salloc(builder: ir.IRBuilder, ir_type: ir.Type, name=''):
        ty_ptr = builder.alloca(ir_type, name=name)
        mem_obj = FloMem(ty_ptr)
        return mem_obj

    @staticmethod
    def realloc(builder: ir.IRBuilder, mem, size: FloInt):
        realloc = bi.get_instrinsic("realloc")
        old_mem = FloMem.bitcast(builder, mem, bi.byteptr_ty).value
        new_mem = builder.call(realloc, [old_mem, size.value])
        new_mem = FloMem(new_mem)
        return new_mem


class FloPointer(FloType):
    def __init__(self, flotype: FloType) -> None:
        self.is_constant = False
        self.elm_type = flotype
        self.mem = None

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
            ref.mem = FloMem.salloc(ref.builder, self.llvmtype, ref.name)
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
        return isinstance(__o, FloPointer) and self.elm_type == __o.elm_type

    def cast_to(self, builder: ir.IRBuilder, type):
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
            self.elm_type = values[0]
            for v in values:
                if not v.is_constant:
                    self.is_constant = False
                    break
            self.elems = values
            self.len = len(values)
        else:
            self.len = arr_len
            self.elems = values
            self.is_constant = False

    @property
    def value(self):
        if self.elems:
            return [elm.value for elm in self.elems]

    def store_value_to_ref(self, ref):
        if not ref.mem:
            ref.mem = FloMem.salloc(ref.builder, self.llvmtype, ref.name)
        if self.is_constant:
            ref.mem.store_at_index(ref.builder, FloType(
                ir.Constant(self.llvmtype, self.value)), FloInt(0))
        elif self.elems and len(self.elems) > 0:
            next_idx = [FloInt(0, 32), FloInt(0, 32)]
            tmp_mem = ref.mem
            for floval in self.elems:
                tmp_mem = tmp_mem.get_pointer_at_index(ref.builder, *next_idx)
                next_idx = [FloInt(1, 32)]
                floval.store_value_to_ref(
                    FloRef(ref.builder, floval, '', tmp_mem))

    @property
    def llvmtype(self):
        return ir.ArrayType(self.elm_type.llvmtype, self.len)

    def load_value_from_ref(self, ref):
        loaded_array = FloArray(self.elems, self.len)
        loaded_array.mem = ref.mem
        loaded_array.elm_type = self.elm_type
        return loaded_array

    def get_element(self, builder: ir.IRBuilder, index: FloInt):
        value = self.mem.get_pointer_at_index(builder, FloInt(0, 32), index)
        return self.elm_type.load_value_from_ref(FloRef(builder, self.elm_type, '', value))

    def set_element(self, builder: ir.IRBuilder, index, value):
        self.mem.store_at_index(builder, value, FloInt(0, 32), index)
        return value

    def get_pointer_at_index(self, builder: ir.IRBuilder, index):
        mem = self.mem.get_pointer_at_index(builder, FloInt(0, 32), index)
        return FloPointer(self.elm_type).new(mem)

    def str(self) -> str:
        return f"{self.elm_type.str()}[{self.len}]"

    def __eq__(self, __o: object) -> bool:
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

    def __init__(self, arg_types: List, return_type, name, var_args=False):
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
        if self.return_type == FloVoid:
            return FloVoid
        self.return_type.value = rt_value
        return self.return_type

    def get_local_ctx(self, parent_ctx: Context, arg_names: List(str)):
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
        if value == FloVoid:
            self.builder.ret_void()
        else:
            self.builder.ret(value.value)

    @property
    def llvmtype(self):
        return self.get_llvm_type().as_pointer()

    def load_value_from_ref(self, ref):
        loaded_func = FloFunc(self.arg_types, self.return_type, None, self.var_args)
        loaded_func.value = ref.mem.load_at_index(ref.builder).value
        return loaded_func

    def str(self) -> str:
        arg_list = ", ".join([arg.str() for arg in self.arg_types])
        return f"({arg_list})=>{self.return_type.str()}"

    def __eq__(self, other):
        if isinstance(other, FloFunc) and len(self.arg_types) == len(other.arg_types) and self.return_type != other.return_type:
            for my_arg, other_arg in zip(self.arg_types, other.arg_types):
                if my_arg != other_arg:
                    return False
            return True
        return False


class FloClass(FloType):
    classes = {}

    def __init__(self, name) -> None:
        self.name = name
        self.methods: dict[str, FloMethod] = {}
        self.properties: dict[str, FloType] = {}
        self.value = ir.global_context.get_identified_type(name)
        self.constructor = None
        self.processed = False
        FloClass.classes[name] = self

    def add_method(self, fnc: FloFunc):
        # prepend this in args
        assert isinstance(fnc, FloMethod)
        assert fnc.value
        if fnc.value.name == self.name+'_constructor':
            self.constructor = fnc
        else:
            self.methods[fnc.value.name] = fnc

    def add_property(self, name, value):
        self.properties[name] = value

    def process(self):
        if not self.processed:
            body = [val.llvmtype for val in self.properties.values()]
            self.value.set_body(*body)
            self.processed = True

    def constant_init(self, builder: ir.IRBuilder, args):
        ptr_value = FloMem.salloc(builder, self.value)
        for index, arg in enumerate(args):
            ptr_value.store_at_index(
                builder, arg, FloInt(0, 32), FloInt(index, 32))
        obj = FloObject(self)
        obj.mem = ptr_value
        return obj


class FloMethod(FloFunc):
    def __init__(self, arg_types: List, return_type, name, var_args=False, class_: FloClass = None):
        if class_:
            name = class_.name + "_" + name
            arg_types.insert(0, FloObject(class_))
            self.class_ = class_
        self.current_object = None
        super().__init__(arg_types, return_type, name, var_args)

    def call(self, builder: ir.IRBuilder, args):
        return super().call(builder, [self.current_object]+args)

    def get_local_ctx(self, parent_ctx: Context, arg_names: List(str)):
        return super().get_local_ctx(parent_ctx, ["this"]+arg_names)


class FloObject:
    def __init__(self, referer: FloClass) -> None:
        self.referer = referer
        self.mem = None
        assert (referer)
        if not isinstance(referer.value, str):
            self.llvmtype = referer.value.as_pointer()

    def store_value_to_ref(self, ref):
        if not ref.mem:
            ref.mem = FloMem.salloc(ref.builder, self.llvmtype, ref.name)
        if self.mem:
            ref.mem.store_at_index(ref.builder, self)

    def load_value_from_ref(self, ref):
        loaded_object = FloObject(self.referer)
        loaded_object.mem = ref.mem.load_at_index(ref.builder)
        return loaded_object

    @property
    def value(self):
        return self.mem.value

    @value.setter
    def value(self, n_val):
        self.mem = FloMem(n_val)

    def get_property(self, builder: ir.IRBuilder, name):
        try:
            property_index = list(self.referer.properties.keys()).index(name)
        except Exception:
            return self.get_method(name)
        property_value: FloType = self.referer.properties.get(name)
        mem = self.mem.get_pointer_at_index(
            builder, FloInt(0, 32), FloInt(property_index, 32))
        return property_value.load_value_from_ref(FloRef(builder, property_value, '', mem))

    def get_method(self, name) -> Union[FloMethod, None]:
        assert isinstance(self.referer, FloClass)
        name = self.referer.name + "_" + name
        method = self.referer.methods.get(name)
        if method:
            method.current_object = self
            return method

    def set_property(self, builder: ir.IRBuilder, name: str, value: FloType):
        property_index = list(self.referer.properties.keys()).index(name)
        mem = self.mem.get_pointer_at_index(
            builder, FloInt(0, 32), FloInt(property_index, 32))
        value.store_value_to_ref(FloRef(builder, value, '', mem))
        return value

    def construct(self, builder: ir.IRBuilder, args):
        self.mem = FloMem.halloc(builder, self.referer.value)
        if self.referer.constructor:
            self.referer.constructor.current_object = self
            self.referer.constructor.call(builder, args)
        return self

    def str(self) -> str:
        return self.referer.name if isinstance(self.referer, FloClass) else self.referer.value

    def __eq__(self, other: object) -> bool:
        if not other:
            return False
        self_classname = None
        other_classname = None
        if not isinstance(other, FloObject):
            return False
        if isinstance(self.referer, FloClass):
            self_classname = self.referer.name
        elif isinstance(self.referer, Token):
            self_classname = self.referer.value
        if isinstance(other.referer, FloClass):
            other_classname = other.referer.name
        elif isinstance(other.referer, Token):
            other_classname = other.referer.value
        return self_classname == other_classname

    def add(self, builder: ir.IRBuilder, other):
        method = self.get_method("__add__")
        return method.call(builder, [other])

    def cmp(self, builder: ir.IRBuilder, op, other):
        if op == "==":
            eq_method = self.get_method("__eq__")
            if eq_method == None:
                return FloInt(0, 1)
            if eq_method.arg_types[0] == other:
                return eq_method.call(builder, [other])
            else:
                return FloInt(0, 1)

    def get_cast_method(self, type):
        name = "__as_"+type.str().replace("*", "_ptr")+"__"
        return self.get_method(name)

    def cast_to(self, builder: ir.IRBuilder, type):
        if is_string_object(type):
            if is_string_object(self):
                return self
            if self.get_method('__as_string__') == None:
                string = f"@{self.referer.name}"
                return create_string_object(builder, [FloConst.create_global_str(string), FloInt(len(string))])
        method: FloMethod = self.get_cast_method(type)
        if method != None:
            return method.call(builder, [])
        else:
            raise Exception("Cannot cast")


class FloInlineFunc(FloFunc):
    def __init__(self, call, arg_types, return_type, var_args=False, defaults=[]):
        self.arg_types = arg_types
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
            return FloVoid()
