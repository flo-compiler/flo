# FLo Documentation
## Introduction
Flo is a programming language designed to be general-purpose, statically typed and compiled with a natural feel when used and fast when run. Like all other programming languages, it is a tool to help programmers to write fast and efficient computer instructions. Syntactically and semantically, it resembles a lot of modern interpreted high-level languages like python and typescript.


## Mathematical operators
```
+
-
/
*
^ # power
%
```
## Comparison operators
```
== 
>
<
>=
<=

```
## Bit-Wise operators
```
and
or
!
>>
<<
xor
```
## Types
```
b: int = 5 // statically typed int

hello: str = "hello world" // string

hello: bool = true // boolean

arr1: int[] = [1, 2, 3, 4, 5, ...] // as many elements as one wants

arr2: int[5] = [1, 2, 3, 4, 5] // fixed length of 5

arr1[0] = 0 // set value 0 to index 0 in array

/* You don't have to specify the type if you are assigning a value */
s1 = "red car" // infered type to be string

/* Variables previous bound to a type cannot be redefined (Static types) */
s1 = 5 // error since previously defined type is string
```
## Concatenation
### String concatenation
You can concatenate two or more strings by using `+`
#### ex:
```
a: str = "hello"
b: str = ", world"
c: str = a+b
print(c) // prints "hello, world"
print(a+b+"!") // prints "hello, world!"
```
### Array concatenation
You can concatenate two or more arrays of the **same type** by using `+`
numbers1: int [] = [1, 2]
numbers2: int [] = [3, 4]
all_numbers = numbers1 + numbers2
println(all_numbers) // prints [1, 2, 3, 4]
```
```
## Conditionals 
### if, else
```
if a > b {
    // DO SOMETHING
} else if  b > c {
    // DO SOMETHING
} else {
    // DO SOMETHING
}
```
## Loops 

### for
```
for i: int = 0; i < 5; i++ {
    println(i)
}
```
### foreach
```
// looping though an array using values
array = [1, 2, 3]
foreach elem in array {
    println(elem)
}
/* looping though each character in string.
Flo Doesn't have a character type so each character is just a string of length 1.
*/
string = "abc"
foreach char in string {
    println(char)
}

```
### while
```
while true {
 // do something
}
```

## functions
```
// function returns the value passed as parameter times 2
double = (x: int): int => x*2

// adds two intbers and returns their sum
fnc add(x: int, y: int): int {
    return x+y
}
double_sum = (x: int, y: int): int => double(sum(x, y))
```
## Type Operators
### is
```
5 is int // true
"hello" is str // true
[4, 5] is int [] // true
5 is bool // false
```
### as
Used for type conversion.
Possible conversions are:

- string to int
- string to float
- float to string
- int to string
- int to float
- float to int
```
3.4 as int // 3
"5" as int // 5
"3.5" as float // 3.5
89 as int // "89"
```
### in
```
array = [1, 2, 3, 4, 5]
5 in array // prints true
hello = "hello"
"llo" in hello // prints true
```
