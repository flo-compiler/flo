# FLo Documentation
- Basics
## keywords
```
num
str
void
bool
break
continue
and
as
or
xor
fnc
in
is
if
else
for
foreach
while
return
pub
priv
class
```
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
