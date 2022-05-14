#include <stdio.h>

struct gry
{
    long x;
};
int main(){
    struct gry g;
    g.x = 42;
    printf("%ld\n", g);
    return 0;
}
