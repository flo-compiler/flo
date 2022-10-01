# Flo 
Flo is a programming language designed to be general-purpose with a natural feel when used and fast when run. Like all other programming languages, it is a tool to help programmers to write fast and efficient computer instructions. Syntactically and semantically, it resembles a lot of modern interpreted high-level languages.

## Installation
*Note*: The Installation process is undetermined since I'm working on the self-compiler

## Usage
Compile and execute file (Compilation requires gcc for linking)
```bash
flo -e helloworld.flo
./helloworld
```
## Language Goals
1. Smooth developer experience. 
2. code readability.
3. Memory Safety.
4. Thread Safety.
5. Fast Performance.

## Memory Safety
Still in progress. In the future it might be acheived by:
- [ ] Reference counting
- [ ] A borrow mechanism inspired by rust.

## Math Safety
- [ ] Integer Overflows.
- [ ] Division by zero.


## Taste of the language.
- [ ] Compile time Macros ($symbol).
- [x] Functions with no body are considered extern functions and Methods with no body make the class an abstract class.
```php
$STDOUT = 0
write($STDOUT, "ss", 2)
```
- [ ] Global Variables (static keyword). 
    - `static y: int = 4`
    - `static x: Readonly<T>` is a global const.

- [ ] Optional chaining `a?.b?.c`

## Ranges
- [x] Declaring a range
```
less_than_ten = 0..10
```
- [x] Checking if a number falls in a range
```
5 in less_than_then // true
```
- [ ] Ranges of any type
```
floats_range = 0.0..10.0
```
## Arrays
### Two types of arrays:
1. Static Arrays (On the stack, fixed size):
```
numbers: int [3] = [1, 2, 3]
// or
numbers = [1, 2, 3]
```
- [ ] Static Array size is expression an not constant.
2. Dynamic Arrays (On the heap, An object(generic) not fixed)
```
numbers: Array<int> = [1, 2, 3]
```
- [ ] Short Hand for arrays
```
a = [1..100]
```
## Classes
- [x] Basic Class support
```
class Chef {
    specialty: string
    constructor(specialty: string) {
        this.specialty = specialty
    }
    print_specialty() {
        println(this.specialty)
    }
}
```
- [x] Inheritance
- [x] Super
```
class ItalianChef(Chef) {
    specialty2: string
    constructor() {
        super("Pasta")
        this.specialty2 = "Pizza"
    }
    print_specialty_two() {
        println(this.specialty2)
    }
}
```
- [x] Polymorphism
```t
chef: Chef = new ItalianChef()
chef.print_specialty() // prints "Pizza"
```
- [ ] Access modifiers.
- [ ] Static Members.
- [ ] getters/setters.
- [ ] Object Literal Intialization. (Also should work on function return and parameter passing)
```
chef: Chef = {specialty: "cake"}
```
- [ ] Do not Allow for object creation of class with implemented methods.

- [x] Operator Overloading.
    - `__eq__` (==)
    - `__add__` (+)
    - `__sub__` (-) TODO
    - `__mul__` (*) TODO
    - `__div__` (/) TODO
    - `__or__` (or) TODO
    - `__and__` (and) TODO
    - `__getitem__` (a[b])
    - `__setitem__` (a[b] = 2)
    - `__in__` (4 in int_array)
    - `__sl__` (<<)
    - `__sr__` (>>) TODO
    - `__lt__` (<) TODO
    - `__lg__` (>) TODO
    - `__ne__` (!=) TODO
    - `__le__` (<=) TODO
    - `__ge__` (>=) TODO
    - `__pow__` (^) TODO
    - `__mod__` (%) TODO

- [ ] Operator Fall backs.
## Enums
- [x] Enums constants (Assigned as numbers at compile time)
```
enum Numbers{
    ONE
    TWO
    THREE
}
```
## Dictionaries
## Sets
## Tuples
Work in progress (Will be in the standart library)
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
- [ ] Match Expression.

## Loops
- [x] traditional for Loop
```
for i = 0; i < 10; i++ // do something
```
- [ ] For in loop
```
for x in 1..10
```
- Need Iterable support
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
fnc add(x: int, y: int = 0): int => {
    return x+y
}
add(5)
```
- [ ] Var args.
```
fnc max(...numbers: int){
    max_num = numbers[0]
    for number in numbers {
        if number > max_num {
            max_num = number
        }
    }
    return max_num
}
```
- [ ] Functions with closure(Anonymous functions).
- [ ] Named parameters for function calls 
```
double(x: 5)
```
## Generics
- [x] Generic Classes.
- [ ] Generic Functions.
    - Generic Methods in Classes.
- [ ] Built-in Generics.
    - `Readonly<T>`.

## Types
- [ ] Type Unions and Intersections (or, and).
- [ ] Optional types. 
```
    x: int?
```
- [ ]  Meta-type programming capablitites.?
    - Type restrictions.


## Type Alias
- [x] basic Type Aliasing.
```
type char = i8
type i1 = bool
```
- [ ] Better Type Aliasing.
    - Type Aliasing with Type Contraints.
    - Type Aliasing with Generics.

## Type Checking
- [x] `is` keyword.
```py
1 is int // true
2.0 is float //true
'A' is i8 // true
1 is string // false
```
## Type Casting
Type casting works with ``as`` keyword.
```ts
x = 1 as float // returns 1.0
```
Type Casting always works when converting these types to the following types.

`Safes`
(Boolean and Chars are considered int types by the compiler)
- Int of any bit size to Int of any bit size.
- Int of any bit size to Float.
- Float of acceptable bit size to Float of acceptable bit size.
- Int/Float/Objects to string.
    - Int and Float will result in the stringified Int/Float.
    - Object will return a default string.
        - This behavior can be overriden with the `__as_string__` method.

`Unsafes`
- Pointer of any type to Pointer of any type (Unsafe)
- Object of any type to Object of any type (Unsafe)
    - Safe if object the method `__as_${other_object_name}__` is implemented (Generics do not apply here)
    - Needs to be checked by the compiler and looked for any memory error.
    - Casting to pointer types on objects using type aliased names.
        - `__as_cstr__(): cstr`

This might not work
- String to Int/Float might fail if String is not an Int or Float.

This **will** not work
- Static Arrays to string shall not work.


## Error Handling
Work in progress
```ts
try {
    // unsafe code
} catch error {
    println(error)
}
```
```ts
try error_prone_fnc() catch error {
    println(error)
}
```

## Imports/External
- [x] Import Specific symbol.
```
import A, B in "module0"
```
- [x] Import All module.
```
import "module"
```
- [ ] Import renaming/ namespacing.
```
import A as C in "module"
import "module" as B
B.add(1)
```

## Errors / Bugs
- Debugger.
- Stack trace.

## Environment
- Syntax highlithing / LSP server / Snippets.
