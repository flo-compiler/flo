# FLo Documentation
## Introduction
Flo is a programming language designed to be general-purpose with a natural feel when used and fast when run. Like all other programming languages, it is a tool to help programmers to write fast and efficient computer instructions. Syntactically and semantically, it resembles a lot of modern interpreted high-level languages, and this vision will show in a lot of design decisions made in the language production.


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
FIVE = 5 // constant; can't be changed through code execution

b: num = 5 // statically typed number

hello: str = "hello world" // string

hello: bool = true // boolean

arr2: num[] = [1, 2, 3, 4, 5, ...] // as many elements as one wants

arr2: num[5] = [1, 2, 3, 4, 5] // fixed length of 5

dic: {num} = {"one": 1, "two": 2} // dictionary of numbers

dic["three"] = 3 // assign

print(5 in arr2) // prints true

print("llo" in hello) // prints true

arr1[0] = 0 // set value 0 to index 0 in array

s1 = "red car" // infered type to be string

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
```
```

## Conditionals 
### if, else
```
if a > b {
    // DO SOMETHING
} else 
if  b > c {
    // DO SOMETHING
} else {
    // DO SOMETHING
}
```
## Loops 

### for
```
for i: num = 0; i < 5; i++ {

}
```
### foreach
```
// looping though an array using values
foreach elem in array {

}
```
```
// looping through a dictionary
foreach key in dict {

}
```
### while
```
while 1 {
 // do something
}
```

## functions
```
// function returns the value passed as parameter times 2
fnc double(x: num): num => x*2

// adds two numbers and returns their sum
fnc add(x: num, y: num): num => {
    return x+y
}
fnc double_sum (x: num, y: num): num => double(sum(x, y))
```
## Type Operators
```
is
```
