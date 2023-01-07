# Flo 
Flo is a programming language designed to be general-purpose with a natural feel when used and fast when run. Like all other programming languages, it is a tool to help programmers to write fast and efficient computer instructions. Syntactically and semantically, it resembles a lot of modern interpreted high-level languages.

## Installation
*Note*: The Installation process is undetermined since I'm working on the self-compiler

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
Still in progress. In the future it might be acheived by:
- [ ] Reference counting
- [ ] A borrow mechanism inspired by rust.

## Math Safety
- [ ] Integer Overflows.
- [ ] Division by zero.


## Taste of the language.
- [x] Functions with no body are considered extern functions and Methods with no body make the class an abstract class.
- [ ] Optional chaining `a?.b?.c`
- [ ] Multiple assignemt/destructing
```
let (a, b, c) = (5, 6, 7)
// or
let [a, b, c] = [5, 6, 7]
```



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
let names: string[] = ["paul", "john", "xavier"]
```
- [ ] Short Hand for arrays
```
let a = [1..100]
```
## Classes
- [x] Basic Class support
```
class Chef {
    specialty: string
    constructor(this, specialty: string) {
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
- [ ] Object Literal Intialization. (Also should work on function return and parameter passing)
```
chef: Chef = {specialty: "cake"}
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
    - `__and__` (and)
    - `__adda__` (+=)
    - `__suba__` (-=)
    - `__mula__` (*=)
    - `__diva__` (/=)
    - `__ora__` (or=)
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
    - `__pow__` (^)
    - `__mod__` (%)
    - `__pow__` (^=)
    - `__mod__` (%=)

- [x] Operator Fall backs.
    -   Overloads for `==` and `!=` have fallbacks other operators don't and need to be implemented in order to use those in an object.
## Enums
- [x] Enums constants (Assigned as numbers at compile time)
```
enum Numbers {
    ONE
    TWO
    THREE
}
```
## Dictionaries
## Sets
## Tuples
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
```
match test {
    expr1 => result1
    expr2 => result2
    expr3 => result3
    _ => default_result
}
```

## Loops
- [x] traditional for Loop
```
for let i = 0; i < 10; i++ // do something
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
- [ ] Functions with closure (Anonymous functions).
```
fnc main(){
    let add = (x: int, y: int) => x + y
}
```
- [ ] Named parameters for function calls 
```
let result = sum(y: 6, x: 5)
```
## Generics
- [x] Generic Classes.
    - Items to test:
        - Generic Methods in Classes.
        - Generic Classes inheritance
```
class GenericNumber<T> {
  value: T
  __add__ (this, y: T){
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
- [ ] Any type 
```
let x: any
x = 7
x = 8.0
```
- [ ] Type Union
```
type Numeric = int or float
fnc main(){
    let n: Numeric = 5
    match n {
        int => println("int!")
        float => println("float!")
    }
}
```
### Type Alias
- [x] basic Type Aliasing.
```
type char = i8
type i1 = bool
```
- [ ] Better Type Aliasing.
    - Type Aliasing with Type Contraints.
    - Type Aliasing with Generics.
    - Types as first class? (inspired by TT).

### Type Casting
Type casting works with ``as`` keyword.
```
let x = 1 as float // returns 1.0
```
Type Casting always works when converting these types to the following types.

`Safes`
- Boolean to int/float.
- Any type to boolean.
    - Does a null comparason.
- Int of any bit size to Int of any bit size.
- Int of any bit size to Float.
- Any float type to any float type.
- Any type to string.
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
- Static Arrays to string shall not work. (Working on it)
- Any type cast not mentionned above.


## Error Handling
- [ ] Using destructing
```
let (result, error) = io_operation()
```
- [ ] Using Optional chaining
```
let result = io_operation()?
```
- [ ] Using Nullish coalescing
```
let result = io_operation() ?? null
```
- [ ] Using match
```
let result = match io_operation() {
    error(e) => println("An error occured")
    success(r) => r
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
- [ ] Import renaming/ namespacing.
```
import A as C in "module"
import "module" as B
B.add(1)
```

## Debugger
- Working to add debugging information to generated code and see if I can integrate that into IDEs.

## Environment
- Syntax highlithing / LSP server / Snippets.
