# Flo 
Flo is a programming language designed to be general-purpose with a natural feel when used and fast when run. Like all other programming languages, it is a tool to help programmers to write fast and efficient computer instructions. Syntactically and semantically, it resembles a lot of modern interpreted high-level languages, and this vision will show in a lot of design decisions made in the language production.

## Documentation
Consult the [lang docs](./docs)

## Installation
In order to install flo you will need
-  [git](https://git-scm.com/downloads)
-  [python>=3.8](https://www.python.org/downloads/)
-  [pip](https://pip.pypa.io/en/stable/installation/) and
-  [gcc](https://gcc.gnu.org/install/download.html) (Optional can use another program for linking object file)

Clone the repo
```bash
git clone https://github.com/vanelk/flo.git
```

Move into the directory
```bash
cd flo
```

Install
```bash
pip install -r requirements.txt
./install.py
```

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
[] Reference counting
[] A borrow mechanism inspired by rust.

## Math Safety
[] Integer Overflows.
[] Division by zero.

## Code Readablity and ease of use
[] A null
[] Argument labels `foo(bar: 3)`
[] Optional chaining `a?.b?.c`

## Ranges
[x] Declaring a range
```
less_than_ten = 0..10
```
[x] Checking if a number falls in a range
```
5 in less_than_then // true
```
[] Ranges of any type
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
[] Static Array size is expression an not constant.
2. Dynamic Arrays (On the heap, An object(generic) not fixed)
```
numbers: Array<int> = [1, 2, 3]
```
[] Short Hand for arrays
```
a = [1..100]
```
## Classes
[x] Basic Class support
```ts
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
[x] Inheritance
[x] Super
```ts
class ItalianChef extends Chef {
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
[x] Polymorphism
```ts
chef: Chef = new ItalianChef()
chef.print_specialty() // prints "Pizza"
```
[] Access modifiers.
[] Static Members.
[] Null initialization of uninitialized class members.
[] Object Literal Intialization. (Also should work on function return and parameter passing)
```ts
chef: Chef = {specialty: "cake"}
```
[] Do not Allow for object creation of class with implemented methods.

[x] Operator Overloading.
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
## Enums
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
Work in progress
## Conditionals
```
if a >= b {
// DO SOMETHING
} else 
if a in 0..11 {
// DO SOMETHING
} else // DO SOMETHING
```
## Loops
[x] traditional for Loop
- Optional parts doesn't work
```
for i = 0; i < 10; i++ // do something
```
[] For in loop
```
for x in 1..10
```
- Need Iterable support
[x] While loop
```
while 1 // do something 
// or
while true // do something
```
## Functions
[x] Base Function
```
fnc double(x: int): int {
    return x*2
} 
```
[x] Function with default args
```
// adds two numbers and returns their sum
fnc add(x: int, y: int = 0): int => {
    return x+y
}
add(5)
```
[] Var args.
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
[] Functions with closure(Anonymous functions).
[] Generic Functions.
[] JS style setters and getters.
[] Parameter Labels on functions.
```
double(x: 5)
```
## Type Alias
```
type char = i8
type i1 = bool
```
## Type Checking
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

Static Arrays to string shall not work.
String to Int/Float might fail if String is not an Int or Float.

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
- Stack trace.

## Environment
- Syntax highlithing / LSP server / Snippets.
- Debugger.

## Future
- Think about global variables.
- Think about module renaming.
```ts
import A as C from 'module1'
import 'module2' as B
```
- Testing.