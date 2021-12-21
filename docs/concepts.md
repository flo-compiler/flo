# Drafted features
## keywords
```
num
str
break
continue
and
bool
or
xor
fnc
in
if
else
for
foreach
while
return
null
noob
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
## Types
```
FIVE: const = 5 // constant
b: num = 5 // statically typed number
hello: str = "hello world" // string
hello: bool = true // boolean
hello: noob = true // dynamic variable
arr2: num[] = [1, 2, 3, 4, 5, ...] // as many elements as one wants
arr2: num[5] = [1, 2, 3, 4, 5]
arr1[0] = 0 // set value 0 to index 0 in array

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
// looping through a map
foreach key, value in map {

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
// assigning a new variable to an anonymous function
double_sum = fnc (x: num, y: num): num => double(sum(x, y))
```