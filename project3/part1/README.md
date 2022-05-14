1. current宏，是一个全局指针，指向当前进程的struct task_struct结构体，即表示当前进程。
current宏，是一个全局指针，指向当前进程的struct task_struct结构体，即表示当前进程。

　　例如current->pid就能得到当前进程的pid，current-comm就能得到当前进程的名称。

　　每个进程会有两个栈，一个用户栈，存在于用户空间，一个内核栈，存在于内核空间。

　　当进程在用户空间运行时，cpu堆栈指针寄存器里面的内容是用户堆栈地址，使用用户栈；

　　当进程在内核空间时，cpu堆栈指针寄存器里面的内容是内核栈空间地址，使用内核栈。

　　在陷入内核后，系统调用中也是存在函数调用和自动变量，这些都需要栈支持。、

　　当进程因为中断或者系统调用而陷入内核态时，进程所使用的堆栈也要从用户栈转到内核栈。

task_struct定义在`<linux/sched.h>`中

X86(`CONFIG_X86_64=y`)架构支持多级页表，页目录、页表等都定义在文件`pgtable_types.h`中，由`CONFIG_PGTABLE_LEVELS`来确定。

`pgd_t`, `p4d_t`, `pud_t`, `pmt_t`, `pte_t`

![image-20220514153553059](https://michael-picgo.obs.cn-east-3.myhuaweicloud.com/img/image-20220514153553059.png)

`__pa()`宏溯源，是`arch/x86/include/asm/page_64.h`中的函数

![image-20220514154614694](https://michael-picgo.obs.cn-east-3.myhuaweicloud.com/img/image-20220514154614694.png)

其中`__START_KERNEL_MAP`是`asm/page_64_types.h`中的`_AC()`宏：

![image-20220514154814985](https://michael-picgo.obs.cn-east-3.myhuaweicloud.com/img/image-20220514154814985.png)

`_AC(X,Y)`宏是`(X##Y)`. `UL`也是一个和`AC`有关的宏，最终落在一个常数，因此`__START_KERNEL_map`是一个常数。。

`phys_base`和`PAGE_OFFSET`等都是使用`EXPORT_SYMBOL`开放给全部内核模块的。



结构体和共用体的区别在于：结构体的各个成员会占用不同的内存，互相之间没有影响；而共用体的所有成员占用同一段内存，修改一个成员会影响其余所有成员。结构体占用的内存大于等于所有成员占用的内存的总和（成员之间可能会存在缝隙），共用体占用的内存等于最长的成员占用的内存。共用体使用了内存覆盖技术，同一时刻只能保存一个成员的值，如果对新的成员赋值，就会把原来成员的值覆盖掉。



![image-20220514162106836](https://michael-picgo.obs.cn-east-3.myhuaweicloud.com/img/image-20220514162106836.png)

当结构体内的成员变量只有一个long时，可以将struct当做long来使用



**获取PID**

`kernel/pid.c`中的`get_pid_task()`调用`pid_task()`函数，

mmap 15.5
后面看完15章，并总结一下