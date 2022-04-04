#include<stdio.h>
#include<math.h>
#include<stdlib.h>


int main(int argc, char** args){
    long count=__LONG_MAX__;
    if(argc>1){
        count = atoi(args[1]);
    }
    for (long i = 0; i < count; i++)
    {
//        if(i%10000==0)
//            printf("%ld\n", i);
        sqrt(100000000001.0);
    }

    return 0;
}
