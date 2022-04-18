# Project 2

## Task 1

### 预备知识

#### CPU-Bound任务设计

**循环开根号**：不需要访问磁盘和内存，是计算密集型任务。

```c
long count=__LONG_MAX__;
for (long i = 0; i < count; i++)
{
    if(i%10000==0)
        printf("%ld\n", i);
    sqrt(100000000001.0);
}
printf("Done.\n");
return 0;
```

#### 设置进程优先级

**启动时: nice**

```shell
nice -n <Priority> <Command>
```

#### CPU绑定

1. 查看可以运行某一进程的CPU

   ```shell
   taskset -c -p <PID>
   ```

2. 在启动时将进程绑定至一（组）CPU

   ```shell
   taskset -c <CPU_List_,_Sep> <Command>
   ```


### 实验过程与结果

任务一的第一部分使用以下脚本来启动十个进程：设置5个进程的nice值为0，5个进程的nice值为4，这10个进程都绑定在逻辑核`11`上。

```shell
#!/bin/bash
gcc -o task1 task1.c
if [ $? -eq 0 ]; then
        for i in {1..5}
        do
                nice -n 0 taskset -c 11 ./task1 &
        done    
        for i in {6..10}
        do      
                nice -n 4 taskset -c 11 ./task1 &
        done
fi
```

使用 `htop -s Command` 指令可以得到以下结果

![result1-1](https://michael-picgo.obs.cn-east-3.myhuaweicloud.com/result1-1.png)

可见，nice值为0的5个进程约占用70% CPU，nice值为4的5个进程约占用30%CPU。

使用如下指令创建一个实时进程

```shell
nice -n -20 taskset -c 11 ./task1 &
```

结果如下：

![reusult1-2](https://michael-picgo.obs.cn-east-3.myhuaweicloud.com/reusult1-2.png)

可以看到实时进程抢占了绝大部分CPU资源。

## Task 2

### 进程管理

内核把进程的列表存放再任务队列这个双向循环链表中，链表的每一个结点的类型都是*进程描述符* `task_struct`结构，它定义在`linux/sched.h`文件中。进程描述符中包含进程所有信息，因此任务2中要实现的`ctx`属性就应该被添加在`task_struct`中。

![task2-1](https://michael-picgo.obs.cn-east-3.myhuaweicloud.com/task2-1.png)

*用户定义的内容最好添加在`task_struct`的推荐区域中*。

### 进程创建

Linux的进程创建被分解到了`fork()`和`exec()`两个函数中——`fork()`通过拷贝当前进程创建一个子进程，`exec()`读取可执行文件并将其载入地址空间开始运行。Linux通过`clone()`系统调用去实现`fork()`，`clone()`又调用`copy_process()`完成了拷贝父进程并创建子进程的工作。`copy_process()`在进程的创建时被调用，被定义在`kernel/fork.c`中，任务2需要在这个函数中初始化`ctx`。

![task2-2](https://michael-picgo.obs.cn-east-3.myhuaweicloud.com/task2-2.png)

### 进程调度

Linux中`schedule()`函数负责进程调度。`schedule()`函数执行`pick_next_task()`函数选择最该被调度的那个进程。换言之，当一个进程被`pick_next_task()`函数选中时，他就会被调度，因此需要在`pick_next_task()`函数返回前执行`ctx++`。`schedule()`和`pick_next_task()`都被定义在`kernel/sched/core.c`中。

![task2-3](https://michael-picgo.obs.cn-east-3.myhuaweicloud.com/task2-3.png)

### 文件系统目录创建

文件系统的目录项在`fs/proc/base.c`中“注册”，具体是在数组`tgid_base_stuff[]`中，数组元素的类型是`pid_entry`。“注册”方式如图所示，`ONE`是Linux定义的宏，表示要注册的是*文件*（`DIR`表示文件夹）。`ctx`是文件名，`S_IRUGO` 表示 *可以被所有用户读取, 但是不能改变* 的文件权限，`proc_tgid_ctx`则是相应函数，当`ctx`被读取时被执行。

![task2-4](https://michael-picgo.obs.cn-east-3.myhuaweicloud.com/task2-4.png)

### 编译内核

内核编译主要参考[How To Compile And Install Kernel On Ubuntu](https://itsubuntu.com/how-to-compile-and-install-kernel-on-ubuntu/)，遇到的问题在***心得体会*** 部分详述。

### 结果分析

测试中执行Task 1中定义的计算密集型应用。

![task2-5](https://michael-picgo.obs.cn-east-3.myhuaweicloud.com/task2-5.png)

访问进程的`/proc/<PID>/ctx`文件可以看到进程被调度的次数。

## 心得体会

通过本次项目我最大的体会就是我对Linux的设计实现的理解极大提高了，这是我第一次阅读如此庞大的底层代码项目。相较于上课时学的设计思路，代码的庞杂让我起初摸不着头脑。

为此我详细阅读了《Linux内核设计与实现》这本书的对应章节，并结合内核源码进行理解。这次项目让我对《操作系统》课程上学习到的各种抽象的内容融会贯通，是不可多得的一次宝贵的项目经历。

实际上，对我来说本次实践最大的难点在于Linux内核的编译安装。由于我直接尝试在主机Linux系统上进行安装，主机系统面临和各种设备驱动直接交互，而且在我长期的使用中可能已经后来对内核模块进行过许多更改，因此内核编译遇到了许多问题。

在编译过程中的问题主要是`CONFIG_X86_X32`和`CONFIG_DEBUG_INFO_BTF`缺乏对应的支持，必须设位`n`。更大的问题出现在安装阶段，由于缺少对应的模块，新的内核无法读取到固态硬盘。

<img src="https://michael-picgo.obs.cn-east-3.myhuaweicloud.com/337988481551927597.jpg" alt="337988481551927597" style="zoom: 33%;" />

**在与 ash shell 挣扎、更改linux启动硬盘的uuid、更改BIOS的SATA兼容性未果后，在新创建的虚拟机上完成了实践。但是这一过程大大增加了我对机器启动过程的理解。**

<img src="https://michael-picgo.obs.cn-east-3.myhuaweicloud.com/image-20220418224352698.png" alt="image-20220418224352698" style="zoom:33%;" />

<img src="https://michael-picgo.obs.cn-east-3.myhuaweicloud.com/image-20220418224433390.png" alt="image-20220418224433390" style="zoom: 50%;" />
