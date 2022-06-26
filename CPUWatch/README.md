# CPUWatch

## 简介

CPUWatch是监控应用程序的计算访存量的一个实用工具。

<img src="https://michael-picgo.obs.cn-east-3.myhuaweicloud.com/image-20220623205748430.png" alt="image-20220623205748430" style="zoom:67%;" />

计算机程序可以分为计算密集型和访存密集型两种，计算密集型指CPU计算占据主导地位的程序，相比于内存访问来说，计算密集型程序需要占据大量CPU资源；访存密集型程序则相反，需要进行大量内存读写，这对CPU与内存之间的总线带宽提出了较高要求。

现代计算机的计算与访存速度之间存在极大差异。CPU计算时一般使用片上寄存器来进行临时变量的存储，寄存器的访问速度与CPU的计算速度相当；而CPU与内存之间一般使用PCIe总线相连，它的速度比CPU计算速度低了数个数量级，因此访存会严重地影响计算速度。当内存访问量较少时，多级缓存策略可以在一定程度上缓解这个问题，而当内存访问量变大后，访存速度则成为了程序的性能瓶颈。

计算密集型和访存密集型程序有着截然不同的优化瓶颈，因此识别一个程序是计算密集型还是访存密集型则有着重要意义，CPUWatch性能检测程序也就应运而生。CPUWatch支持Linux系统上的任意用户态程序，通过监控程序执行时间、CPU运行时间、内存页访问量来判断应用程序是计算、访存密集度。CPUWatch采用定周期采样的方式获取应用进程的相关信息，用户可以执行采样周期。为方便用户进行程序数据分析，CPUWatch还支持逐周期数据导出、动态图标绘制的功能。

## 测试原理

### 计算访存比

CPU计算速度与访存速度具有较大差异，最能够发挥计算机性能的程序就是能够充分利用CPU计算能力与访存带宽的程序，这也就需要程序的计算与访存量满足一定的比例。计算机的理论计算访存比是它的计算量与访存量的比值，单位分别为每秒可计算的浮点数（FLOPS）与字节数（Byte）。实际的计算访存比可以通过对程序的分析的来。
$$
(Computation/Memory)_{Peak} = \frac{Peak\ computing\ capability}{Memory\ Bandwidth}
$$

$$
Computation/Memory = \frac{Amount\ of\ calculation\ in\ 'Flops'}{Memory\ Fetching(including\ cache)\ in \ 'Bytes'}
$$

#### 计算密集型与访存密集型

当实际计算访存比低于峰值计算访存比时，那么计算就必须等待访存，程序速度会被访存拖慢；当实际计算访存比高于峰值计算访存比时，内存带宽的使用率则不足。从计算访存比出发，可以分析出一个应用程序的性能瓶颈是计算还是访存，它是也计算密集型程序与访存密集型程序的区分指标：

**计算密集型**：$Computation/Memory>(Computation/Memory)_{Peak}$

**访存密集型**：$Computation/Memory<(Computation/Memory)_{Peak}$

#### 计算访存比的缺陷

使用计算访存比来衡量计算与访存对程序性能的影响有一些缺陷，对于计算来说，计算访存比无法刻画一个程序对CPU的利用率，也就无法判断程序负载相对于CPU性能来说是重是轻；对于访存来说，计算访存比无法刻画程序访问内存的绝对大小。计算访存比只能从理论上分析程序的计算于访存的相对影响。

### CPU利用率

CPU利用率用以衡量程序所占用的CPU资源，表示为一段时间内程序设计占用的CPU时间与CPU运行时间的比值。
$$
CPU\ Usage\ Ratio\ =\ \frac{utime_1-utime_0}{uCputime_1 - uCputime_0}
$$

其中，$utime_i$为从开机到第$i$个时间点程序在用户态占用CPU的总时间，$uCputime_j$为从开机到第$j$个时间点CPU在用户态的实际运行时间。

在Linux系统中，一个程序通常包含多个进程，在统计时$utime$不仅包含主线程在用户态的执行时间 $utime$，还包括它的所有子进程在用户态的执行时间$cutime$。
$$
utime = utime+cutime
$$

### 内存页访问量

在操作系统中内存是以页为单位组织起来的，每页的大小固定，通常是4KB一页。CPUWatch统计一个进程在给定的时间间隔内访问页的个数来刻画进程的内存使用情况。

## 架构设计

CPUWatch分为内核模块（Kernel Module）与用户程序（User Program）两部分，分别称作CPUWatch-K和CPUWatch-U。

内核模块CPUWatch-K运行在系统内核态，具有对操作系统内核数据结构的访问权限。CPUWatch-K通过Linux操作系统的proc文件系统与用户程序交互。它在被安装时创建文件`/proc/watch`，用户程序向`/proc/watch`文件写入被监测进程的PID（Process Identifier）、读取`/proc/watch`文件以获取被监测程序在此次读取与上次读取之间的运行时间与内存页访问量等统计信息（写入`/proc/watch`可以理解为第0次读取）。

用户程序CPUWatch-U运行在用户态，用户必须在CPUWatch-U中输入Shell指令以启动待测试程序。CPUWatch-U通过周期性读取`/proc/watch`文件以获得原始统计量，使用原始统计计算得到CPU利用率等相关统计量，并将瞬时数据与统计图表显示在界面上。

CPUWatch-U内含三个线程：UI线程、Watch线程、Timer线程，他们依次具有继承关系（后者是前者的子线程）。三个线程间通过Qt框架中基于消息队列的“信号与槽”（Signal and Slot）机制通信。

## 内核模块设计

计算CPU占有率需要获取进程的执行时间：`utime`（用户态执行时间）、`stime`（内核态执行时间）、`cutime`（所有子进程在用户态的执行时间）、`cstime`（所有子进程在内核态的执行时间），这四个变量可以通过`/proc/<pid>/stat`文件获得，`/proc/<pid>/stat`文件中第14-17个变量（从1开始）就分别是上述`utime`、`stime`、`cutime`、`cstime`，单位为*jiffies*。

> ***jiffies***
>
> jiffies变量记录了Linux系统启动以来经过的时钟节拍总数（tick），节拍之间的时间就是两次定时器中断时间的时间间隔，数值上等于系统频率的倒数。

CPUWatch-K模拟内核中`/proc/<pid>/stat`文件的实现方式，使用不加锁的方式读取进程的`task_struct`结构体中的相关变量，这么以损失一定统计精度为代价提高了统计效率。Linux内核中使用定义在`<fs/proc/array.c>`中的`do_task_stat()`函数写`/proc/<pid>/stat`文件，这个函数的逻辑将在下一部分进行分析。*CPU运行时间使用CPUWatch-U读取`/proc/stat`文件获得，在此部分不再赘述。*

作为独立于被测程序的第三方监测程序，CPUWatch无法在不改动内核数据结构的情况下获取被测程序的内存读写量。因此CPUWatch采用定周期查询的方式监测被测程序在一个周期内的内存访问量。Linux系统使用页式内存管理方式，每个页都有一个标志位`young`来标记页访问情况，CPUWatch通过这一标志位进行页访问情况查询。具体方式在后文详细阐述。

### CPUWatch-K使用的`task_struct`成员变量

```c
struct task_struct {
	// ...
	struct mm_struct                *mm;
	// ...
	/* Signal handlers: */
	struct signal_struct		   *signal;
	struct sighand_struct __rcu	    *sighand;
	// ...
	u64				               utime;
	u64			 	               stime;
}
```

### 进程执行时间

#### Linux内核`do_task_stat`函数解析

Linux内核中负责写入`/proc/<pid>/stat`文件的函数是`do_task_stat()`，它需要负责除了时间统计量以外的许多其他统计量。`do_task_stat()`函数中与时间统计量相关的部分汇总如下，它可以被拆分为5个部分（注释中Part1-Part5），在后文我会详细分析这五个部分。

```C
static int do_task_stat(struct seq_file *m, struct pid_namespace *ns,
			struct pid *pid, struct task_struct *task, int whole)
{
    // Definition of other statistical variables
    // ... 
    /* Part 1 Definition*/
	u64 cutime, cstime, utime, stime;
    // ...
    // Initialization
	cutime = cstime = utime = stime = 0;
	
    /* Part 2 sighand lock */
	if (lock_task_sighand(task, &flags)) {
		struct signal_struct *sig = task->signal;
        // ...
		cutime = sig->cutime;
		cstime = sig->cstime;
		/* add up live thread stats at the group level */
    /* Part 3 statistics of thread group */
		if (whole) { // pid==tgid
			struct task_struct *t = task;
			thread_group_cputime_adjusted(task, &utime, &stime);
		}
		unlock_task_sighand(task, &flags);
	}

	// ...
    /* Part 4 statistics of single thread */
	if (!whole) { // pid!=tgid
		task_cputime_adjusted(task, &utime, &stime);
	}
    // ...
    /* Part 5 Write into /proc/<pid>/stat */
	seq_put_decimal_ull(m, " ", nsec_to_clock_t(utime));
	seq_put_decimal_ull(m, " ", nsec_to_clock_t(stime));
	seq_put_decimal_ll(m, " ", nsec_to_clock_t(cutime));
	seq_put_decimal_ll(m, " ", nsec_to_clock_t(cstime));
	// ...
	return 0;
}
```

**Part 1 Definition & Initialization：**定义`utime`, `ctime`, `cutime`, `cstime`分别表示当前进程在用户态的执行时间、内核态执行时间、当前进程的子进程在用户态执行时间、内核态执行时间。四个变量在定义以后初始化为0，这也许是因为C99标准不允许在定义时初始化变量。

**Part 2 Sighand Lock：**对`task_struct`中的`signal_struct`类型变量`signal`加锁。Linux使用信号机制进行进程间通信，信号是通过`signal_struct`结构体实现的。在`signal`中可以获取子进程的`cutime`与`cstime`。为了精确获取子进程运行时间，必须要在读取`task->signal->cutime`与`task->signal->cstime`时阻止其他进程改动此变量，因此需要使用`lock_task_sighand()`函数对`signal`上锁。

**Part 3 Statistics of thread group：**当进程是进程组的Leader进程时（`pid=tgid`），`whole=1`，调用`thread_group_cputime_adjusted()`函数获取进程执行时间，这个函数在`CONFIG_VIRT_CPU_ACCOUNTING_NATIVE=y`时的实现如下所示

```c
void thread_group_cputime_adjusted(struct task_struct *p, u64 *ut, u64 *st) {
	struct task_cputime cputime;
	thread_group_cputime(p, &cputime);
	*ut = cputime.utime;
	*st = cputime.stime;
}
```

`thread_group_cputime`读取一个进程的所有子进程的执行时间，实现如下。***这里列出的实际上就是CPUWatch中的实现方式，没有使用RCU锁。***

```c
void thread_group_cputime(struct task_struct *tsk, struct task_cputime *times)
{
	struct signal_struct *sig = tsk->signal;
	u64 utime, stime;
	struct task_struct *t;
    
    times->utime = sig->utime;
    times->stime = sig->stime;

    for_each_thread(tsk, t) {
        times->utime += t->utime;
        times->stime += t->stime;
    }
}
```

**Part 4 Statistics of single thread：**当进程没有子线程时（`pid!=tgit`），`whole=0`，直接读取`task_struct`中的`utime`和`stime`这两个变量

```c
void task_cputime_adjusted(struct task_struct *p, u64 *ut, u64 *st) {
	*ut = p->utime;
	*st = p->stime;
}
```

**Part 5 Write into `/proc/<pid>/stat`：**将读取到的时间变量写入`/proc/<pid>/stat`，`nsec_to_clock_t()`函数将以*纳秒* 为单位的`[us]time`转化为以CPU节拍数(10ms)为单位。***CPUWatch中直接读取以纳秒为单位的数据***。

#### CPUWatch读取进程执行时间

CPUWatch读取进程执行时间的方式完全模拟`do_task_stat`函数，除了没有使用*sighand* 锁与*RCU* 锁。此外，为获取精确的时间统计，选择内核配置项`CONFIG_VIRT_CPU_ACCOUNTING_NATIVE=y`。

**CONFIG_VIRT_CPU_ACCOUNTING_NATIVE**：此内核选项可以在3.9以上版本的内核中找到。选择此选项可启用更准确的任务和CPU时间统计，同时对性能的影响很小。`do_task_stat`函数所调用的`thread_group_cputime_adjusted`和`task_cputime_adjusted`函数在CONFIG\_VIRT\_CPU\_ACCOUNTING\_NATIVE选择与否时的实现有所差异。

### 内存读写量

#### task_struct → mm_struct → vm_area_struct → page

内核除了管理本身的内存以外，还需要管理用户空间中进程的内存，这就是进程地址空间，也就是系统中每个用户所能看到的内存。对于每一个进程都有一个唯一的地址空间，在每个进程的`task_struct`结构体中也必须有一个成员变量用于描述进程的地址空间，这个变量就是“内存描述符”`mm_struct`，定义在`<linux/sched.h>`中。进程地址空间的所有相关信息都保存在`mm_struct`结构体中。

```c
struct task_struct {
	// ...
	struct mm_struct *mm;
}
```

一个进程的地址空间不是连续的，而是有多个连续的内存区域组成。内存区域由`vm_area_struct`结构体描述，又被称作虚拟内存区域（virtual memory area）。`vm_area_struct`结构体指定了地址空间内连续区间上的一个独立内存范围。内核将每个内存区域作为一个单独的内存对象管理，每个内存区域的属性都一致。进程的地址空间内包含多个虚拟内存区域，具体到内核代码中，进程地址空间中的虚拟内存区域使用链表组织在一起，头结点保存在`mm_struct`结构体中：

```c
struct mm_struct {
    struct vm_area_struct *mmap;
    // ...
}
```

虚拟内存区域（`vm_area_struct`）描述了进程虚拟内存空间上的连续区域，区域的首尾地址保存在`vm_area_struct`结构体的`vm_start`和`vm_end`变量中，再结合`mm_struct`结构体中保存的全局页目录入口，就可以索引到一个虚拟地址所对应的物理页。

```c
struct vm_area_struct {
    struct mm_struct *vm_mm;
    unsigned long vm_start;
    unsigned long vm_end;
    struct vm_area_struct *vm_next;
}
```

从`mm_struct`可以通过遍历链表得到`vm_area_struct`对象，从`vm_area_struct`也可以通过`vm_mm`成员变量反向索引到这个虚拟内存区域隶属的地址空间`mm_struct`对象。

`task_struct`、`mm_struct`、`vm_area_struct`的相互索引关系如下所示：

<img src="https://michael-picgo.obs.cn-east-3.myhuaweicloud.com/image-20220625140416745.png" alt="image-20220625140416745" style="zoom:80%;" />

#### `young`标志位

⻚⽬录项中有⼀个标志位 young ， CPU通过`ptep_test_and_clear_young()`函数在每次访问该⻚时会将该标志位置为1，该函数在x86平台的实现如下所示：

```C
int ptep_test_and_clear_young(struct vm_area_struct *vma,
			      unsigned long addr, pte_t *ptep)
{
	int ret = 0;

	if (pte_young(*ptep))
		ret = test_and_clear_bit(_PAGE_BIT_ACCESSED,
					 (unsigned long *) &ptep->pte);

	return ret;
}
```

`ret`变量保存`young`位值。如果它等于1，则将其清空为0。CPUWatch的实现`test_and_clear_bit`函数完全参考[</tools/include/linux/bitmap.h>]([bitmap.h - tools/include/linux/bitmap.h - Linux source code (v5.15.48) - Bootlin](https://elixir.bootlin.com/linux/v5.15.48/source/tools/include/linux/bitmap.h#L101))文件中的不加锁版本，详细内容可见`watch.c`。

#### 获取页读写量

CPUWatch采用周期性轮询进程内存空间中所有页的方式获取页访问情况。

```c
while (vmap!=NULL) // traverse the linked array
{
    // find all pages in a VMA (a for loop with step `PAGE_SIZE`(4096))
    for (addr = vmap->vm_start; addr < vmap->vm_end; addr += PAGE_SIZE)
    {
        // transform `addr`(unsigned int) to `pte`(pte_t)
        ptep = find_pte_from_address(vmap, addr);
        // read the `young` bit and set it to 0
        res = my_ptep_test_and_clear_young(ptep);
        // count 
        sum+=res;
  		// ... other codes for debugging
    }
    vmap = vmap->vm_next;
}
```

CPUWatch使用页为单位进行内存访问计数，而且只能采用被动探测而非主动获取的方式获取数据，这不可避免地带来了一系列问题，例如统计粒度过大使得分析困难、难以应对高频集中的内存访问等。在*性能测试* 章节，我将会具体阐释CPUWatch统计方法的问题。

## 用户程序设计

![image-20220626202545160](https://michael-picgo.obs.cn-east-3.myhuaweicloud.com/image-20220626202545160.png)

CPUWatch-U使用了四个类、三个线程组建起用户程序，类间调用关系如上时序图所示。四个类指的是 `WatchUI`、`CPUWatchController`、`CPUWatchWorker`、`Timer`，三个线程指的是*UI线程、Worker线程* 与*Timer线程* 。

* `WatchUI`：运行在主线程，负责UI组件的初始化、解析用户输入、相应用户操作、创建“测试控制器”。
* `CPUWatchController`：运行在主线程，负责创建Testbench线程、创建Timer线程、建立线程间通信机制。
* `CPUWatchWorker`：运行在Testbench线程，负责根据用户输入的Shell指令创建testbench进程并监控进程状态、周期性读取`/proc/watch`文件。
* `Timer`：运行在Timer线程，负责定时发送信号给CPUWatchWorker使其读取'/proc/watch'文件。

**为什么使用独立的Timer线程而非sleep()函数？**为了能够在Testbench进程的结束时，安全地中止Testbench线程。Timer在计时时依然可以接收其他线程的信号，当被测进程终止时，Testbench线程向Timer线程发送信号，Timer则在本周期运行过程中安全地退出；而sleep()函数启动后当前线程会被完全阻塞住，无法接收来自其他线程的信号，从而造成安全隐患。

## 功能验证

### 直接写入、读取内核模块

`/proc/watch`文件返回的并不是进程从开机开始的执行时间，而是在两次连续的访问之间的进程执行时间。下图显示，当将进程号写入`/proc/watch`文件后立刻读取，则返回值都是0；当隔一段时间再进行读取时，读到有效数据。

![image-20220626002914405](https://michael-picgo.obs.cn-east-3.myhuaweicloud.com/image-20220626002914405.png)

### 数据正确性（误差分析）

<img src="https://michael-picgo.obs.cn-east-3.myhuaweicloud.com/%E6%95%B0%E6%8D%AE%E6%AD%A3%E7%A1%AE%E6%80%A7.png" alt="数据正确性" style="zoom: 67%;" />

CPUWatch在用户程序中在读取`/proc/watch`的同时读取`/proc/<pid>/stat`文件，以供用户进行时间据精确性的对比，详细的对比图表如下图所示

<img src="https://michael-picgo.obs.cn-east-3.myhuaweicloud.com/image-20220626013744000.png" alt="image-20220626013744000" style="zoom:70%;" />

<img src="https://michael-picgo.obs.cn-east-3.myhuaweicloud.com/image-20220626014911512.png" alt="image-20220626014911512" style="zoom:70%;" />

从图中可以看出，虽然utime的相对误差最多达到56.5%，但是超30%的仅有几个屈指可数的数据点。绝对误差均值为0.06ms，相对误差均值2%。绝大多数数据点的相对误差在20%以内。误差异常点倾向于为正值，即$utime_{/proc/watch}>utime_{/proc/<pid>/stat}$。

|      统计量      |   值    |
| :--------------: | :-----: |
|    误差最大值    | 62.2 ms |
|     误差均值     | 0.06ms  |
| 误差百分比最大值 |  56.5%  |
|  平均误差百分比  |   2%    |

## 性能测试

本项目在X86架构的Ubuntu系统进行测试，选用的Testbench程序为*sysbench*，测试时间均为100秒，CPUWatch采样频率为100HZ，绘图频率为10HZ。使用`sysbench cpu`测试“计算”密集型程序，使用`sysbench memory`测试“访存”密集型程序，***但是一个程序具体是计算密集型还是访存密集型是通过数据分析得出的。***

**为什么一定要使用高频采样？**这与CPUWatch读取内存访问情况的方式有关。CPUWatch采取被动监测页访问情况的策略，它只能知道在两次监测之间一个页是否被访问，但无法获悉确切的访问次数，因此采样频率必须高于被检测程序的页访问频率才可以获得准确的访存统计。

### 指令分析

#### 计算密集型

计算密集型程序使用`sysbench cpu --threads=<threads> run`指令，这是sysbench进行cpu性能测试的默认指令。

#### 访存密集型

访存密集型程序使用`sysbench memory --threads=<threads> --memory-block-size=4G --memory-access-mode=rnd run`。

值得一提的是配置项`--memory-block-size`和`--memory-access-mode`。CPUWatch采用被动询问页访问呢情况的策略，这需要被测程序所访问的页的分布尽可能分散，且被测程序不能高频率访问同一个页。`--memory-block-size`设置被测程序所访问的内存空间的大小，4G已是本项目所在的实验平台所能开出的最大空间；`--memory-access-mode=rnd`使被测程序随机地访问内存空间，这使得内存页分布尽可能分散。

### 计算与访存特性对比

#### CPU利用率

<img src="https://michael-picgo.obs.cn-east-3.myhuaweicloud.com/Figure.png" alt="Figure" style="zoom:67%;" />

**“密集”是相对的：**上图显示*sysbench memory* 和*sysbench cpu* 在不同线程负载下的CPU利用率，从图中可以看出在线程数=1，2，4，8，16时*sysbench memory* 对CPU的要求甚至多于*sysbench cpu* 对CPU的要求。

**猜想：** 在线程数=1，2，4，8，16时CPU*sysbench memory*和*sysbench cpu*对CPU需求相当的原因是，在线程数较少时单线程负载较高，CPU既无法满足CPU测试我也无法满足访存测试，因此CPU利用率都较高。

**验证：**当线程数为64和128时，并行度以几何级数增长。*sysbench cpu*给每个线程分配一个计算密集型任务，而非大量线程并行处理一个任务，线程增多，任务量随之增大，CPU利用率也随之增大；而*sysbench memory* 是所有线程完成一个访存密集型任务（向`--memory-block-size`大小的内存区域以`--memory-access-mode`的方式写入`--memory-total-size`大小的数据），因此线程数增多，并行度增大，CPU利用率随之减小。

**为何CPU只有8核，而CPU利用率在线程数>64时大幅下降？**从理论上说，8核计算机最多只有8个线程在同时运行（超线程技术使得16个线程可以同时运行），那么当线程数大于16时CPU利用率应该收敛。即使存在调度开销，也不应该有入此大幅度的下降。

**原因分析：**操作系统中不仅有testbench线程（本段中线程用以指代所有线程与进程），还有若干其他线程。Linux系统采用基于进程优先级的轮询（Round-Robin）调度策略，当*sysbench memory*的线程数增多，每个线程的负载都减小，它们的优先级也随之降低了。在固定的时间间隔内CPU更少地将testbench线程调度到CPU上，更多地将其他线程调度到CPU上，因此CPU利用率大幅降低。

#### 内存页访问量

*sysbench cpu* 和*sysbench memory* 在不同线程数量下的内存页访问量如下图所示。由图中可以看出，虽然*sysbench cpu* 和*sysbench memory* 在线程数=1，2，4，8，16时CPU利用率相当，但是内存访问量呈现明显差异，这也验证了*sysbench memory*时访存密集型任务，CPU只负责控制、起到辅助作用，而*sysbench cpu* 是计算密集型任务，几乎不涉及内存访问。

<img src="https://michael-picgo.obs.cn-east-3.myhuaweicloud.com/%E5%86%85%E5%AD%98%E9%A1%B5%E4%BD%BF%E7%94%A8%E9%87%8F.png" alt="内存页使用量" style="zoom: 67%;" />



### 计算密集型程序测试

![image-20220626145626211](https://michael-picgo.obs.cn-east-3.myhuaweicloud.com/image-20220626145626211.png)

计算密集型程序在不同线程数下的CPU利用率和内存访问量随时间变化如上图所示。随着线程数指数增加，内存页访问量几乎恒定（相对于指数而言）。

各个线程数下平均CPU利用率如下表所示：

| 线程数 | 平均CPU利用率 |
| ------ | ------------- |
| 1      | 27.5%         |
| 4      | 65.5%         |
| 8      | 76.1%         |
| 64     | 97.8%         |
| 128    | 100.16%       |

在线程负载恒定的条件下，随着线程数增多，CPU利用率不断提高，直到收敛于100%。

### 访存密集型程序测试

![image-20220626155455756](https://michael-picgo.obs.cn-east-3.myhuaweicloud.com/image-20220626155455756.png)

访存密集型程序在不同线程数下的CPU利用率和内存访问量随时间变化如上图所示。平均CPU利用率在*计算与访存特性对比* 一节已有详尽分析。由于*sysbench memory*性能测试的负载是时序均匀的，因此CPU利用率与内存页访问量都较为恒定。

## 思考题

1. ⼤多数 benchmark 是多线程或者是多进程的，你的程序中有考虑这种情况吗？若没有，应该怎么解决？  

   本项目中考虑了多线程的情况。当进程是进程组的leader，即pid=tgid时，遍历进程组的所有进程以获取所有子进程的执行时间。遍历方式如下所示：

   ```C
   void thread_group_cputime(struct task_struct *tsk, struct task_cputime *times)
   {
   	struct signal_struct *sig = tsk->signal;
   	u64 utime, stime;
   	struct task_struct *t;
       
       times->utime = sig->utime;
       times->stime = sig->stime;
   
       for_each_thread(tsk, t) {
           times->utime += t->utime;
           times->stime += t->stime;
       }
   }
   ```

2. utime 表示程序的什么时间？ /proc/[pid]/stat 还有⼀个参数为 stime ，它表示什么？你觉得在这个实验⾥⾯适合使⽤它吗？  

   `utime`表示进程在用户态的执行时间，`stime`表示进程在内核态的执行时间。在这个实验里不适合使用`stime`，原因有二：

   1. testbench进程中无论是计算密集型任务还是访存密集型任务都运行在用户态。
   2. CPUWatch对于内存访问量的统计是通过遍历VMA进行的，而VMA代表进程的用户态的地址空间中的区域。为了与这个统计量相匹配，必须使用用户态执行时间。

   因此，本次实验中所取的时间为$utime+cutime$。*事实上，由实验中得到的结果来看，stime远小于utime，这是因为sysbench特意在用户态运行高负载任务所致*。

3. 你觉得当前实验中以页为单位统计进程的内存读写合适吗？如果合适，原因是什么？如果不合适，有没有更好的⽅法？

   以页为单位统计内存读写是***向内核数据结构***、***被动探测内存访问状态*** 的一个较好的选择。页的大小为4KB，相对于现代计算机8G+的总内存量与大多数进程以GB为单位的内存访问量来说是一个较小的统计单位，但是它的问题有以下两点：

   1. 无法应对高频的页访问。探测`young`位只能知道两次探测之间页是否被访问过，但无法知道具体的访问次数，因此需要探测频率高于页访问频率。
   2. 无法应对集中的页访问。如果被测程序集中访问少量的页，本项目中使用的方法则无法获悉具体访问的内存大小。

   我认为有两种可行的解决方案：

   1. 不再从内核数据结构中获取：借助`/proc/smaps`文件可以获取进程的虚拟内存空间使用情况、物理内存使用情况、共享内存使用情况等。从`/proc/smaps`文件获取的统计量均以`KB`为单位，且由内核主动完成内存访问状态的统计，不存在探测频率的问题，是比较理想的获取内存使用量的方式
   2. 不再被动探测：若是一定要从内核数据结构获取统计量、或者需要精确到字节的内存使用量统计，则可以在内核的`page`数据结构中增加成员变量`count`。当待测进程每次访问该页时，内核将访问量计入统计量。缺点在于这种方法需要重新编译内核。而且以字节为单位的内存统计在绝大多数情况下并不必要，在内存有限的嵌入式设备上者这也许是一种可行的方法。

## 总结与感悟

CPUWatch是一款运行于Linux系统的性能监控软件，用户可方便地通过图形界面完成进程启动、性能监控、图表绘制和数据导出全流程操作。CPUWatch的内核模块部分使用无锁的方式直接从内核数据结构中获取进程执行时间与内存页访问情况，在不影响进程本身的前提下高效地获取数据。

**感悟：**我总算见识到了Linux内核。源码面前，了无秘密，下了这半年的功夫以后，看到课本，写到代码，心中更有丘壑。

## 致谢

* 感谢陈全老师一个学期的辛勤付出，让我从Linux内核出发更为透彻地理解操作系统。
* 感谢程家淦和李垚暄学长一个学期以来答疑解惑，在我完成Lab的道路上指点迷津。
* 感谢上海交通大学计算机科学与技术系开设《Linux内核》这门课程。
