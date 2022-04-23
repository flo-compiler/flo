from ast import List
import contextlib
import inspect
import uuid
import builtIns as bi
from context import Context, SymbolTable
from llvmlite import ir, binding
from typing import Union
from lexer import Token


va_list_t = ir.global_context.get_identified_type("struct.va_list")
va_list_t.set_body(bi.byteptr_ty)


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
        elif str == "bool":
            return FloBool
        elif str == "void":
            return FloVoid
        elif str == "byte":
            return FloByte

    @staticmethod
    def to_flo_ty(val_type, value):
        if not isinstance(value, FloMem) and value.type.is_pointer:
            value = FloMem(value)
        if inspect.isclass(val_type):
            return val_type(value)
        else:
            return val_type.new(value)


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


class FloConst(FloType):
    # TODO be careful with arrays and strings
    str_constants = {}

    def __init__(self, value, flotype) -> None:
        assert isinstance(value, FloMem)
        self.flotype = flotype
        self.value = value

    def load(self, builder: ir.IRBuilder):
        value = self.value.load_at_index(builder)
        if isinstance(self.flotype, FloObject):
            ptr_val = FloMem.salloc(builder, self.flotype.referer.value)
            ptr_val.store_at_index(builder, FloType(value))
            value = ptr_val
        return FloType.to_flo_ty(self.flotype, value)

    @staticmethod
    def make_constant(builder: ir.IRBuilder, name: str, value: FloType) -> None:
        initializer = value.value
        const_val = ir.GlobalVariable(
            Context.current_llvm_module, initializer.type, name)
        const_val.initializer = initializer
        const_val.global_constant = True
        flotype = value if hasattr(value, 'new') else value.__class__
        return FloConst(FloMem(const_val), flotype)

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
        flo_ptr = FloPointer(FloMem(str_ptr), FloByte)
        return flo_ptr

    def __eq__(self, other):
        if isinstance(other, FloConst):
            return self.flotype == other.flotype    
        return self.flotype == other
    def str(self):
        return self.flotype.str()


def is_string_object(type):
    return isinstance(type, FloObject) and type.referer.name == 'string'

def create_string_object(builder, args):
    return FloClass.classes.get("string").new(builder, args)

class FloInt(FloType):
    llvmtype = bi.i32_ty

    def __init__(self, value: int):
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
        if type == FloFloat:
            return self.to_float(builder)
        elif type == FloBool:
            return self.cmp(builder, "!=", FloInt.zero())
        elif type == FloByte:
            return FloByte(builder.trunc(self.value, FloByte.llvmtype))
        elif is_string_object(type):
            return self.to_string(builder)
        else:
            raise Exception(f"Unhandled type cast: int to {type.str()}")

    def to_string(self, builder: ir.IRBuilder):
        sprintf = bi.get_instrinsic("sprintf")
        str_buff = FloMem.halloc_size(builder, FloInt(10))
        fmt = FloConst.create_global_str("%d")
        strlen = FloInt(builder.call(sprintf, [str_buff.value, fmt.value, self.value]))
        return create_string_object(builder, [str_buff, strlen])

    @staticmethod
    def str() -> str:
        return "int"


class FloFloat(FloType):
    llvmtype = ir.DoubleType()

    def __init__(self, value: Union[float, ir.Constant]):
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

    def pow(self, builder, num):
        v = builder.call(bi.get_instrinsic("pow"), [self.value, num.value])
        return FloFloat(v)

    def neg(self, builder: ir.IRBuilder):
        self.value = builder.fneg(self.value)
        return self

    def cast_to(self, builder: ir.IRBuilder, type):
        if type == FloInt:
            return self.to_int(builder)
        elif type == FloBool:
            return self.cmp(builder, "!=", FloFloat.zero())
        elif is_string_object(type):
            return self.to_string(builder)
        else:
            raise Exception(f"Unhandled type cast: float to {type.str()}")

    def to_string(self, builder: ir.IRBuilder):
        sprintf = bi.get_instrinsic("sprintf")
        str_buff = FloMem.halloc_size(builder, FloInt(1))
        fmt = FloConst.create_global_str("%g")
        length = builder.call(sprintf, [str_buff.value, fmt.value, self.value])
        return create_string_object(builder, [str_buff, FloInt(length)])
    
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

    def cast_to(self, builder: ir.IRBuilder, type):
        if type == FloInt:
            return FloInt(builder.zext(self.value, FloInt.llvmtype))
        elif type == FloFloat:
            return self.cast_to(builder, FloInt).to_float(builder)
        elif is_string_object(type):
            return self.to_string(builder)
        else:
            raise Exception(f"Unhandled type cast: bool to {type.str()}")

    def to_string(self, builder):
        value = builder.select(self.value, FloConst.create_global_str(
        "true\0").value, FloConst.create_global_str("false\0").value)
        lenval =  builder.select(self.value, FloInt(4).value, FloInt(5).value)
        return create_string_object(builder, [FloMem(value), FloInt(lenval)])

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


class FloByte:
    llvmtype = bi.byte_ty

    def __init__(self, value) -> None:
        if isinstance(value, int):
            self.value = ir.Constant(ir.IntType(8), value)
        else:
            self.value = value
        assert self.value != None

    @staticmethod
    def str():
        return 'byte'

    def cmp(self, builder: ir.IRBuilder, op, other):
        bool_val = builder.icmp_unsigned(op, self.value, other.value)
        return FloBool(bool_val)

    def cast_to(self, builder: ir.IRBuilder, type):
        if type == FloInt:
            return FloInt(builder.zext(self.value, FloInt.llvmtype))
        elif is_string_object(type):
            return self.cast_to(builder, FloInt).to_string(builder)
        else:
            raise Exception(f"Unhandled type cast: bool to {type.str()}")

    def print_val(self, builder: ir.IRBuilder):
        bi.call_printf(builder, "%d", self.value)


class FloMem(FloType):
    heap_allocations = {}
    stack_allocations = {}
    llvmtype = bi.byteptr_ty

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
        i8_ptr = builder.bitcast(self.value, bi.byteptr_ty)
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
    def halloc(builder: ir.IRBuilder, ir_type: ir.Type, name=''):
        size = FloInt(ir_type.get_abi_size(bi.target_data))
        mem_obj = FloMem.halloc_size(builder, size)
        mem_obj = FloMem.bitcast(builder, mem_obj, ir_type.as_pointer())
        return mem_obj

    @staticmethod
    def salloc(builder: ir.IRBuilder, ir_type: ir.Type, name=''):
        ty_ptr = builder.alloca(ir_type, name=name)
        mem_obj = FloMem(ty_ptr)
        FloMem.stack_allocations[mem_obj.uuid] = mem_obj
        return mem_obj

    @staticmethod
    def realloc(builder: ir.IRBuilder, mem, size: FloInt):
        realloc = bi.get_instrinsic("realloc")
        old_mem = FloMem.bitcast(builder, mem, bi.byteptr_ty).value
        new_mem = builder.call(realloc, [old_mem, size.value])
        new_mem = FloMem(new_mem)
        new_mem.uuid = mem.uuid
        FloMem.heap_allocations[mem.uuid] = new_mem
        return new_mem


class FloPointer(FloType):
    def __init__(self, value: FloMem, flotype: FloType) -> None:
        self.mem = value
        self.elm_type = flotype
        if value != None:
            assert isinstance(self.mem, FloMem)

    @property
    def llvmtype(self):
        return self.elm_type.llvmtype.as_pointer()

    @llvmtype.setter
    def llvmtype(self, ty):
        self.elm_type.llvmtype = ty.pointee

    @property
    def value(self):
        return self.mem.value

    @value.setter
    def value(self, new_mem):
        self.mem = new_mem

    def get_element(self, builder: ir.IRBuilder, index: FloInt):
        value = self.mem.load_at_index(builder, index)
        return FloType.to_flo_ty(self.elm_type, value)

    def add(self, builder: ir.IRBuilder, increment: FloInt):
        return self.new(self.mem.get_pointer_at_index(builder, increment))

    def sub(self, builder: ir.IRBuilder, increment: FloInt):
        return self.new(self.mem.get_pointer_at_index(builder, increment.neg(builder)))

    def set_element(self, builder: ir.IRBuilder, index: FloInt, value: FloType):
        self.mem.store_at_index(builder, value, index)
        return value

    def new(self, value: FloMem):
        return FloPointer(value, self.elm_type)

    def __eq__(self, __o: object) -> bool:
        return isinstance(__o, FloPointer) and self.elm_type == __o.elm_type

    def cast_to(self, builder: ir.IRBuilder, type):
        if not isinstance(type, FloPointer):
            raise Exception("Cannot cast")
        else:
            return FloPointer(FloMem.bitcast(builder, self.mem, type.llvmtype), type.elm_type)

    def str(self):
        return f"{self.elm_type.str()}*"

    def print_val(self, builder: ir.IRBuilder):
        fmt = "%s" if self.elm_type == FloByte else "%p"
        bi.call_printf(builder, fmt, self.value)


class FloArray:
    def __init__(self, values, arr_len = None, builder: ir.IRBuilder = None):
        if isinstance(values, list):
            assert builder != None
            self.len = arr_len or len(values)
            self.elm_type = values[0] if hasattr(values[0], 'new') else values[0].__class__
            llvmtype = ir.ArrayType(self.elm_type.llvmtype, arr_len)
            self.mem = FloMem.salloc(builder, llvmtype)
            self.llvmtype = llvmtype.as_pointer()
            for i, array_value in enumerate(values):
                self.mem.store_at_index(builder, array_value, FloInt(0), FloInt(i))
        else:
            self.len = arr_len
            self.mem = values
        assert isinstance(self.mem, FloMem) or self.mem == None


    def new(self, value):
        # For Functions
        array = FloArray(value, self.len)
        array.elm_type = self.elm_type
        return array

    @property
    def value(self):
        return self.mem.value

    @value.setter
    def value(self, new_mem):
        self.mem = new_mem

    def get_element(self, builder: ir.IRBuilder, index):
        value = self.mem.load_at_index(builder, FloInt(0), index)
        if inspect.isclass(self.elm_type):
            return self.elm_type(value)
        return self.elm_type.new(value)

    def set_element(self, builder: ir.IRBuilder, index, value):
        self.mem.store_at_index(builder, value, FloInt(0), index)
        return value

    def str(self) -> str:
        return f"{self.elm_type.str()}{'[]'}"

    def __eq__(self, __o: object) -> bool:
        return isinstance(__o, FloArray) and self.elm_type == __o.elm_type


is_64_bit = binding.targets.get_host_cpu_features()['64bit']


class FloArgArray(FloArray):
    def __init__(self, value, builder: ir.IRBuilder = None, size=None):
        super().__init__(value, builder, size)
        self.should_offset = None

    def get_element(self, builder: ir.IRBuilder, index):
        if self.should_offset == None:
            self.should_offset = is_64_bit and self.elm_type.llvmtype.get_abi_size(
                bi.target_data) < 8
        if self.should_offset:
            array_buff = self.mem.load_at_index(builder)
            buff_ptr = FloMem.bitcast(builder, array_buff, ir.IntType(64).as_pointer())
        else:
            buff_ptr = self.mem
        value = buff_ptr.load_at_index(builder, index)
        if self.should_offset:
            value = builder.trunc(value, self.elm_type.llvmtype)
        if inspect.isclass(self.elm_type):
            return self.elm_type(value)
        return self.elm_type.new(value)


class FloRef:
    def __init__(self, builder: ir.IRBuilder, referee: FloType, name=None):
        self.builder = builder
        self.referee = referee
        if referee:
            self.addr = FloMem.salloc(builder, referee.llvmtype, name)
            self.store(referee)

    @staticmethod
    def alloc(builder: ir.IRBuilder, reftype: FloType, name=''):
        refobject = FloRef(builder, None, name)
        refobject.addr = FloMem.salloc(builder, reftype.llvmtype, name)
        if not inspect.isclass(reftype):
            refobject.referee = reftype
        return refobject

    def load(self):
        self.referee.value = self.addr.load_at_index(self.builder)
        return self.referee

    def store(self, referee: FloType):
        if self.referee == None:
            self.referee = referee
        self.addr.store_at_index(self.builder, referee)


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
        fn_type = self.get_llvm_type()
        self.llvmtype = fn_type.as_pointer()
        if name:
            current_module = Context.current_llvm_module
            value = ir.Function(current_module, fn_type, name)
            self.mem = FloMem(value)
            fn_entry_block = self.value.append_basic_block()
            self.builder = ir.IRBuilder(fn_entry_block)

    @staticmethod
    def declare(arg_types: List, return_type, name, var_args=False):
        n_arg_types = [arg_ty.llvmtype for arg_ty in arg_types]
        fn_ty = ir.FunctionType(return_type.llvmtype,
                                n_arg_types, var_arg=var_args)
        val = Context.current_llvm_module.declare_intrinsic(name, (), fn_ty)
        new_fnc = FloFunc(arg_types, return_type, None)
        new_fnc.value = FloMem(val)
        return new_fnc

    def call(self, builder: ir.IRBuilder, args):
        passed_args = [arg.value for arg in args]
        # if self.var_args:
        #     passed_args.insert(
        #         0, FloInt(len(passed_args)-len(self.value.args)+1).value)
        rt_value = builder.call(self.mem.value, passed_args)
        if self.return_type == FloVoid:
            return FloVoid
        return FloType.to_flo_ty(self.return_type, rt_value)

    def get_local_ctx(self, parent_ctx: Context, arg_names: List(str)):
        self.arg_names = arg_names
        local_ctx = parent_ctx.create_child(self.value.name)
        for arg_name, arg_type, arg_value in zip(arg_names, self.arg_types, self.mem.value.args):
            arg_val = FloType.to_flo_ty(arg_type, arg_value)
            local_ctx.set(arg_name, FloRef(self.builder, arg_val, arg_name))
        return local_ctx
        # va_name = None
        # if self.var_args:
        #     va_name = arg_names.pop()
        # if va_name != None:
        #     va_args_mem = FloMem.salloc(self.builder, va_list_t)
        #     self.va_arg = FloMem.bitcast(
        #         self.builder, va_args_mem, bi.byteptr_ty)
        #     self.builder.call(bi.get_instrinsic(
        #         "va_start"), [self.va_arg.value])
        #     va_mem = va_args_mem.load_at_index(
        #         self.builder, FloInt(0), FloInt(0))
        #     if self.value.name == "main":
        #         va_mem = FloMem.bitcast(
        #             self.builder, va_mem, bi.byteptr_ty.as_pointer()).load_at_index(self.builder)
        #     length = FloInt(self.value.args[0])
        #     va_mem = FloArray.create_array_struct(
        #         self.builder, va_mem, length, length)
        #     va_list = FloArgArray(va_mem)
        #     va_list.elm_type = self.var_arg_ty
        #     self.sym_tbl.set(va_name, va_list)

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
    def value(self) -> ir.Function:
        return self.mem.value

    @value.setter
    def value(self, new_mem):
        self.mem = new_mem

    def str(self) -> str:
        arg_list = ", ".join([arg.str() for arg in self.arg_types])
        return f"({arg_list})=>{self.return_type.str()}"

    def __eq__(self, other):
        if isinstance(other, FloFunc) and len(self.arg_types) == len(other.arg_types):
            for my_arg, other_arg in zip(self.arg_types, other.arg_types):
                if my_arg != other_arg:
                    return False
            if self.return_type == other.return_type:
                return True
        return False


class FloClass(FloType):
    classes = {}
    def __init__(self, name) -> None:
        self.name = name
        self.methods: dict[str, FloType] = {}
        self.properties: dict[str, FloType] = {}
        self.value = ir.global_context.get_identified_type(name)
        self.constructor = None
        self.processed = False
        FloClass.classes[name] = self

    def add_method(self, fnc: FloFunc):
        # prepend this in args
        assert isinstance(fnc, FloMethod)
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

    def new(self, builder: ir.IRBuilder, args):
        value = FloMem.halloc(builder, self.value)
        object_ = FloObject(value, self)
        if self.constructor:
            self.constructor.current_object = object_
            self.constructor.call(builder, args)
        return object_

    def constant_init(self, builder: ir.IRBuilder, args):
        if builder:
            ptr_value = FloMem.salloc(builder, self.value)
            for index, arg in enumerate(args):
                ptr_value.store_at_index(
                    builder, arg, FloInt(0), FloInt(index))
        else:
            const_value = ir.Constant(self.value, [arg.value for arg in args])
            ptr_value = FloMem(const_value)
        return FloObject(ptr_value, self)


class FloMethod(FloFunc):
    def __init__(self, arg_types: List, return_type, name, var_args=False, class_: FloClass = None):
        if class_:
            name = class_.name + "_" + name
            arg_types.insert(0, FloObject(None, class_))
            self.class_ = class_
        self.current_object = None
        super().__init__(arg_types, return_type, name, var_args)

    def call(self, builder: ir.IRBuilder, args):
        return super().call(builder, [self.current_object]+args)

    def get_local_ctx(self, parent_ctx: Context, arg_names: List(str)):
        return super().get_local_ctx(parent_ctx, ["this"]+arg_names)


class FloObject:
    def __init__(self, mem: FloMem, referer: FloClass) -> None:
        self.referer = referer
        if not isinstance(referer.value, str):
            self.llvmtype = referer.value.as_pointer()
        else:
            self.llvmtype = None
        self.mem = mem

    def get_property(self, builder: ir.IRBuilder, name):
        try:
            property_index = list(self.referer.properties.keys()).index(name)
        except Exception as e:
            return self.get_method(name)

        property_value = self.referer.properties.get(name)
        val = self.mem.load_at_index(
            builder, FloInt(0), FloInt(property_index))
        return FloType.to_flo_ty(property_value, val)

    def get_method(self, name) -> Union[FloMethod, None]:
        assert isinstance(self.referer, FloClass)
        name = self.referer.name + "_" + name
        method = self.referer.methods.get(name)
        if method:
            method.current_object = self
            return method

    def set_property(self, builder: ir.IRBuilder, name: str, value: FloType):
        property_index = list(self.referer.properties.keys()).index(name)
        property_value = self.referer.properties.get(name)
        val = self.mem.store_at_index(
            builder, value, FloInt(0), FloInt(property_index))
        property_value.value = val
        return property_value

    def new(self, value):
        # For Functions
        return FloObject(value, self.referer)

    @property
    def value(self):
        return self.mem.value

    @value.setter
    def value(self, new_mem):
        self.mem = new_mem

    def str(self) -> str:
        return self.referer.name if isinstance(self.referer, FloClass) else self.referer.value

    def __eq__(self, other: object) -> bool:
        if not other:
            return False
        self_classname = None
        other_classname = None
        if not isinstance(other, FloObject): return False
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
                return FloBool.false()
            if eq_method.arg_types[0] == other:
                return eq_method.call(builder, [other])
            else:
                return FloBool.false()

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
        self.sym_tbl = None
        if call:
            self.llvmtype = self.get_llvm_type().as_pointer()
            self.call_method = call
        if return_type == FloVoid:
            self.returned = FloVoid
        else:
            self.returned = None

    def call(self, *kargs):
        returned = self.call_method(*kargs)
        if returned != None:
            return returned
        else:
            return FloVoid
