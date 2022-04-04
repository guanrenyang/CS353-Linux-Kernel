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

![result1-1](/home/guanrenyang/353/project2/result1-1.png)

可见，nice值为0的5个进程约占用70% CPU，nice值为4的5个进程约占用30%CPU。

使用如下指令创建一个实时进程

```shell
nice -n -20 taskset -c 11 ./task1 &
```

结果如下：

![reusult1-2](/home/guanrenyang/353/project2/reusult1-2.png)

可以看到实施进程抢占了绝大部分CPU资源。

## Task 2

![task2-1](/home/guanrenyang/353/project2/task2-1.png)

![task2-2](/home/guanrenyang/353/project2/task2-2.png)

![task2-3](/home/guanrenyang/353/project2/task2-3.png)

![task2-4](/home/guanrenyang/353/project2/task2-4.png)

