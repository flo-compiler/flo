# Flo 
A new programming language.
An attempt to create my own programming language but in python. 
Syntax ressembles typescript with a tint of python.

## Next Todo/Immediate Bugs
- xor
- and=, or=, <<=, >>=, xor= Operators
- Introduce the is keyword
- Fix bug with function return types, and definitions
- Automatic return type induction for functions
- Default paramaters for functions
- Generic Types
- Introduce String Literals
- Refactor

## Todo (No priority)
- [x] Interpreter
- [x] Comments
- [x] Constants
- [x] Statically typed variables
- [x] Arithmetic operations
- [x] Logical operations
- [x] Turing complete
- [x] Functions
- [x] Strings
- [x] Boolean
- [x] Arrays
- [x] Dictionaries
- [x] Conditionals
- [x] For loop
- [x] Foreach loop / In Keyword
- [x] Dynamic type casting
- [x] While loop
- [ ] Generic Types
- [ ] Compiler
- [ ] Object oriented / user defined types
- [ ] Operator overloading
- [ ] Error Handling
- [ ] JS style setters and getters
- [ ] Make String and arrays iterable types 
- [ ] Self-Hosting


## Run
```console
$ ./flo.py
```
## Warning
- The compiler module requires llvmpy which inturn requires llvm3.3
    - Check [llvmpy](https://github.com/llvmpy/llvmpy) for info.
    - I recommend Ubuntu if you want to install llvmpy. 
    - You can comment/remove all compiler references in flo.py if you want to work with the interpreter. ie ` line 5 ` and ` line 89-91 `
## Documentation and Examples
[Draft of existing features](docs/concepts.md)

