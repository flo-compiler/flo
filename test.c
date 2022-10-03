#include <stddef.h>
float main(){
    int a  = 121;
    float b = 0.5;
    int c = NULL;
    b = b - a;
    if (c == NULL ){
        b = b + 1;
    } else {
        b = b + c;
    }
    return b;
}