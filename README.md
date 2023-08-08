# Flo 
Flo is a programming language designed to be general-purpose with a natural feel when used and fast when run. Like all other programming languages, it is a tool to help programmers to write fast and efficient computer instructions. Syntactically and Semantically, it resembles a lot of modern interpreted high-level languages.

## Installation
> **WARNING**:  Requires `llvm` installed.
1. Clone the repo
```bash
git clone https://github.com/flo-compiler/flo
```
2. Build the compiler
```bash
cd flo
mkdir build
cd build
cmake ..
cmake --build .
```
3. To be able to run `flo` from anywhere you want to add it to your path via .bashrc
```bash
export PATH=$PATH:path/where/you/have/build/flo
```
## Usage
```bash
flo -h
```
## Language Goals
1. Smooth developer experience. 
2. Code readability.
3. Memory Safety.
4. Thread Safety.
5. Fast Performance.

## Memory Safety
Allowing programmers to opt in between:
- [ ] Garbage collection.
- [x] Manual memory management with `del` keyword.

## Math Safety
- [ ] Integer Overflows.
- [ ] Division by zero.


## Taste of the language.
- [x] Type Inference
```
let y = 5 
```
instead of
```
let y: int = 5
```
- [x] Type Annotations affect the resulting type
```
let y: i8 = 5 // becomes an i8 instead of int
```
- Similarly if you had a function
```
fnc addTwo(x: i8, y: i8): i8 {
    return x + y
}
addTwo(8, 7) 
```
The type of 8 and 7 are infered as `i8` using the type inference at function call.
## Strings
### Two types of strings:
1. C-String (null terminated string)
```
let message: u8* = "Hello, world!"
```
2. String object
```
let message: String = "Hello, world!"
// or
let message = "Hello, world!"
```
### Formated strings:
(Heap string)
```
let x = 33
let y = 36
let message = "$x + $y = $(x+y)" // 33 + 36 = 69
// or as a cstring
let message2: u8* = "$x + $y = $(x+y)" // 33 + 36 = 69
```
Automatically converts format parameters to string and includes then in the formatted string.
## Ranges
- [x] Declaring a range
```
let less_than_ten = 0..10
```
- [x] Checking if a number falls in a range
```
5 in less_than_then // true
```
- [ ] Ranges of other types
```
floats_range = 0.0..10.0
```
## Arrays
### Two types of arrays:
1. Static Arrays (On the stack, fixed size). Since it is on the stack the size has to be a constant.
```
let numbers: int[3] = [1, 2, 3]
```
2. Dynamic Arrays (On the heap)
```
let numbers: Array<int> = [1, 2, 3]
//or
let names: String[] = ["paul", "john", "xavier"]
```
- Indexing arrays
```
let number = numbers[0] // paul
```
- [x] Adding to dynamic arrays
```
names << "Josh"
```
## Maps
- [x] Intialization
```
let map: Map<String, int> = new Map<String, int>()
// or
let map: [String: int] = new [String: int]()
```

- [x] Adding to map
```
map["anny"] = 70
```
- [x] Getting from map (returns null if value was not found)
```
let age = map["bar"]
```
## Conditionals
- [x] `if`/`else`
```
if a >= b {
// DO SOMETHING
} else 
if a in 0..11 {
// DO SOMETHING
} else // DO SOMETHING
```
- [x] Basic Match Expression.
```
match test {
    expr1: result1
    expr2: result2
    expr3: result3
    else: default_result
}
```

## Loops
- [x] For
```
for x in 1..10
```
- Object has to an iterable that is it must have an `__iter__` method that returns an iterator object with the following properties:
    - done: `bool` for when the iterator is done with iteration.
    - next: `any` which returns the next element in the iteration loop.
- The iterator object in the loop is automatically cleaned up at the end of the loop.
- Other examples of where you can use the the for/in loop:
```
// iterating over an array.
for element in [1, 2, 3, 4] {
    println("$element")
}
```
```
// iterating over a map.
for entry in map { 
    println("$(entry.key): $(entry.value)")
}
```
- [x] While loop
```
while 1 // do something 
// or
while true // do something
```
## Functions
- Functions are first class so can be passed as an argument or assigned to vars.
- [x] Base Function
```
fnc double(x: int): int {
    return x*2
} 
```
- [x] Function with default args
```
// adds two numbers and returns their sum
fnc add(x: int, y: int = 0): int {
    return x+y
}
add(5)
```
- [ ] Functions with closure (Anonymous functions).
```
fnc main(){
    let add = (x: int, y: int) -> x + y
}
```
- [ ] Named parameters for function calls 
```
let result = sum(y: 6, x: 5)
```
## Tuples
- [x] Creating tuples
```
let items: (int, f32, bool) = (1, 1.0, true)
// or 
let items = (1, 1.0, true)
```
- [x] Accessing tuples
```
items[0] // 1
```
Index **must** be a constant unsigned integer since resulting type is evaluated at compile time.

## Enums
- [x] Enums constants (Assigned as numbers at compile time) values are all of type `int` by default
```
enum Currencies {
    USD
    EUR
    CAD
}
```
- [x] Enum constraints (limited only to integer types (`i4`, `i8`, `i16`, `i32`, `i64`, `i128`, `int`, `u4`, `u8`, `u16`, `u32`, `u64`, `u128`, `uint`))
```
/*
The values of the members of the Months enum are all of type i4 
*/
enum Months(i4) {
    JANUARY,
    FEBUARY,
    MARCH,
    ...
}
```
- [x] Accessing enum elements
```
let jan = Months.JANUARY
```

## Classes
- [x] Basic Class support
```
class Chef {
    specialty: String
    constructor(this, specialty: String) {
        this.specialty = specialty
    }
    print_specialty(this) {
        println(this.specialty)
    }
}
```
- [x] Object constructor on stack
```
let chef: Chef("Cake")
```
- [x] Object constructor on heap
```
let chef = new Chef("Cake")
```
- [x] Inheritance
- [x] Super
```
class ItalianChef(Chef) {
    constructor(this) {
        this.super("Pasta")
    }
}
```
- [x] Polymorphism
```
let chef: Chef = new ItalianChef()
chef.print_specialty() // prints "Pizza"
```
- [x] Access modifiers. Through `private`, `public` and `protected` keywords as in java. Default modifier is `public`.
```
const CURRENT_YEAR = 2023
class Person {
    private yob: int
    constructor(this, yob: int){
        this.yob = yob
    }
    public getAge(this): int {
        return CURRENT_YEAR - this.yob
    }
}
```
- [x] Static Members. Avoided the use of the static keyword so the absence of `this` argument on methods specify a static method and assignment on field declaration. Static members are not inherited and can only be used through the classname (ie. `Number.ZERO`)
```
class Number {
    ZERO: int = 0 // static field
    public max(i1: int, i2: int): int { // static method
        return i1 > i2 ? i1 : i2
    }
}
```
- [x] Class containing methods without body are considered an abstract class/interface (Objects of that class cannot be created but other classes can inherit that class and implement those methods).
```
class ICMP {
    protected __cmp__(this, other: ICMP): int
    public __eq__(this, other: Int): bool {
        return this.__cmp__(other) == 0
    }
    public __ne__(this, other: ICMP): bool {
        return this.__cmp__(other) != 0
    }
    public __lt__(this, other: ICMP): bool {
        return this.__cmp__(other) < 0
    }
    public __gt__(this, other: ICMP): bool {
        return this.__cmp__(other) > 0
    }
    public __le__(this, other: ICMP): bool {
        return this.__cmp__(other) <= 0
    }
    public __ge__(this, other: ICMP): bool {
        return this.__cmp__(other) >= 0
    }
}
class Int(ICMP) {
    private value: int
    constructor(this, value: int){
        this.value = value
    }
    potected __cmp__(this, other: Int): int {
        return this.value - other.value
    }
}
```
- [x] Operator Overloading.
    - `__eq__` (==)
    - `__add__` (+)
    - `__sub__` (-)
    - `__mul__` (*)
    - `__div__` (/)
    - `__or__` (or)
    - `__xor__` (^)
    - `__and__` (and)
    - `__adda__` (+=)
    - `__suba__` (-=)
    - `__mula__` (*=)
    - `__diva__` (/=)
    - `__ora__` (or=)
    - `__xora__` (^=)
    - `__anda__` (and=)
    - `__getitem__` (a[b])
    - `__setitem__` (a[b] = 2)
    - `__in__` (4 in int_array)
    - `__sl__` (<<)
    - `__sr__` (>>)
    - `__sla__` (<<=)
    - `__sra__` (>>=)
    - `__lt__` (<)
    - `__lg__` (>)
    - `__ne__` (!=)
    - `__le__` (<=)
    - `__ge__` (>=)
    - `__pow__` (**)
    - `__mod__` (%)
    - `__powa__` (**=)
    - `__moda__` (%=)
    - `__del__` (del object; this will be called before deallocating objects memory)

- [x] Operator Fall backs.
    -   Overloads for `==` and `!=` have fallbacks other operators don't and need to be implemented in order to use those in an object.
## Generics
- [x] Generic Classes.
    - Items to test:
        - Generic Methods in Classes.
        - Generic Classes inheritance
```
class GenericNumber<T> {
  value: T
  __add__ (this, y: GenericNumber<T>){
    return this.value + y.value
  }
}
```
- [ ] Generic Functions.
```
fnc identity<T>(arg: T): T {
  return arg
}
```

## Types
- [ ] Optional types. 
```
let x: int?
```
- [ ] Type Union
```
type Numeric = int or f32
fnc main(){
    let n: Numeric = 5
    match n {
        int: println("int!")
        f32: println("f32!")
    }
}
```
### Type Alias
- [x] basic Type Aliasing.
```
type char = u8
type i1 = bool
```
- [ ] Better Type Aliasing.
    - Type Aliasing with Type Contraints.
    - Type Aliasing with Generics.
    - Types as first class? (inspired by TT).

### Type Casting
Type casting works with ``as`` keyword.
```
let x = 1 as f32 // returns 1.0
```
Type Casting always works when converting these types to the following types.

`Safes`
- Boolean to int/float types.
- Any type to boolean.
    - Does a null comparason.
- Int of any bit size to Int of any bit size.
- Int of any bit size to Float.
- Any float type to any float type.
- Any type to String.
    - Int and Float will result in the stringified Int/Float.
    - Object will return a default string representation of the object.
- Enums to ints.
    - returns the value of the enum.

`Unsafes`
- Pointer of any type to Pointer of any type (Unsafe)
- Object of any type to Object of any type (Unsafe)
- Int to enum (Unsafe)
- Any pointer to any pointer (Unsafe)
- Int to pointer (Unsafe)

This might not work
- String to Int/Float might fail if String is not an Int or Float.

These **will** not work
- Static Arrays to String shall not work. (Working on it)
- Any type cast not mentionned above.


## Error Handling
- [ ] Using match
```
let result = match io_operation() {
    Error(e): println("An error occured")
    _(result): result
}
```

## Imports
- [x] Import Specific symbol.
```
import A, B in "module"
```
- [x] Import All module.
```
import "module"
```
- [x] Import renaming
```
import A as C in "module"
```
- [x] import module namespace.
```
import "module" as B
```

## Debugger
- Working to add debugging information to generated code and see if I can integrate that into IDEs.

## Environment
- Syntax highlithing / LSP server / Snippets.
