# Project 3

## Task 1

### 工作流

任务一可以概括为**给定用户进程的PID和在它自己的地址空间中的虚拟地址，在内核空间修改该地址上一字节的内容**。完成这一任务需要以下四个步骤：

1. 根据PID查找用户进程对应的`task_struct`结构体。
2. 根据`task_struct`结构体中的页表信息，查找虚拟地址对应的物理页（`struct page`）
3. 将物理页（`struct page`）映射到内核进程的虚拟地址
4. 内核模块读取/写入该虚拟地址

设四个步骤均在`proc_write()`函数中完成。

#### 进程查找

Linux将所有进程的`task_struct`结构体组织成一个双链表，因此可以通过一个进程的`task_struct`找到任意一个进程的`task_struct`。`pid_task()`函数根据目标进程在当前进程的命名空间中的PID找到进程对应的`task_struct`结构体。由于指令传入的PID并不是目标进程（用户进程）在当前进程（内核进程）的命名空间中的PID，`find_vpid()`函数完成这一转换。

因此，进程查找可以使用如下语句完成：

```C
struct task_struct *task = pid_task(find_vpid(pid), PIDTYPE_PID);
```

#### 查询页表

进程`task_struct`结构体中的`mm_struct`类型的成员变量`mm`内含有该进程地址空间相关的全部信息，当然也包括顶级页目录的入口。

X86(`CONFIG_X86_64=y`)架构支持多级页表，页目录、页表等都定义在文件`pgtable_types.h`中。在X86架构上页表的具体结构由`CONFIG_PGTABLE_LEVELS`来确定。编译内核时默认设置`CONFIG_PGTABLE_LEVELS=5`，对应`pgd_t`, `p4d_t`, `pud_t`, `pmt_t`, `pte_t`五级。

可以使用如下方式逐级查询页表（具体实现中针对每一层都进行了错误处理）：

```C
pgd_t *pgd = pgd_offset(task->mm, address);
p4d_t *p4d = p4d_offset(pgd, address);
pud_t *pud = pud_offset(p4d, address);
pmd_t *pmd = pmd_offset(pud, address);
pte_t *pte = pte_offset_kernel(pmd, address);
struct page *page = pte_page(*pte);

```

#### 内存映射

当一个进程使用诸如（`*address = 0`）的方式给地址`address`上的元素赋值时，`address`时当前进程的地址空间中的一个*虚拟地址*。在取得了物理页的`struct page`结构体或者物理地址（`unsigned long`类型）以后，必须要将这个物理位置映射到当前进程的虚拟地址空间中，才可以进而对这个地址上的元素进程操作。

`void* kmap_local_page(struct page *)`函数将一个物理页映射到当前进程的地址空间以供*临时使用*，`kunmap_local(void*)`结束这一映射：

```C
void* base = (unsigned long) kmap_local_page(page);
/* do something */
kunmap_local(base);
```

需要注意的是：`kmap_local_page`返回的是页的基地址，它还必须加上页内偏移量才能所引导需要操作的元素：

```C
char* dest_addr = ((unsigned long)base & PAGE_MASK) | (address & ~PAGE_MASK); // PAGE_MASK = 0xfffff000
```

页的大小为4K(2^12)，虚拟地址`address`的最后12位为页内偏移量。`PAGE_MASK`的值为`0xfffff000`，上面代码中按位或运算`|`右边计算出页内偏移量，左边计算出页的基地址，二者按位或得到最终地址。

#### 具体实现

本报告中略去命令解析部分。解析后的命令保存在以下四个成员变量中：

```C
char operator;
int pid;
unsigned long address;
char content; // invalid when operator=='r'
```

在完成了以上进程查找、查询页表、内存映射以后，内核进程中可以对`dest_addr`指针进行直接访问：

```c
if (operator=='w'){
    *dest_addr  = content;
} else if (operator=='r') {
    sprintf(output,"%d", (int)(*dest_addr));
    out_len = strlen(output);
}
```

### 实现结果

![image-20220520010313402](https://michael-picgo.obs.cn-east-3.myhuaweicloud.com/img/image-20220520010313402.png)

## Task 2

### 工作流

任务二的目的可以概括为：**当用户进程调用`mmap()`——希望将`/proc`文件系统中的文件`/proc/maptest`映射到用户进程的地址空间中时，告诉用户进程需要被映射的物理内容是什么**。

由于`/proc`文件系统是一个虚拟的文件系统，里面的文件也并不是真是存在的“文件”，因此需要指定当`/proc/maptest`文件被映射时的行为，它通过回调函数`proc_mmap()`完成。

#### 分配物理页

分配物理页可以通过`kmalloc()`、`vmalloc()`或`alloc_page()`函数完成，此处使用`alloc_page()`函数完成：

```C
unsigned long alloc_page(gfp_t gfp_mask, unsigned int order=0)
```

`alloc_page()`函数分配`2^order`个连续的物理页，并返回一个指针，指向第一个页的`struct page`结构体。`gfp_t`是一个标志用以标明使用的*分配器*，最常规的分配器为`GFP_KERNEL`。得到物理页以后，向物理页中写入内容的操作同任务一的*内存映射* 部分。

**具体实现：**

```C
// TODO: allocate page and copy content
page = alloc_page(GFP_KERNEL);

base = (unsigned long) kmap_local_page(page);

char* dest_addr = ((unsigned long)base & PAGE_MASK); // PAGE_MASK = 0xfffff000

strcpy(dest_addr, content);

kunmap_local(base);
```

#### 内存映射

`mmap()`函数将内核地址空间中的内容映射到用户地址空间。用户地址空间相关的信息被包含在一个`vm_area_struct`结构体中，在`proc_mmap()`中要做的就是指明`vm_area_struct`结构体应该对应的物理页。这个`vm_area_struct`通过`proc_mmap`的参数传入：

```C
static int proc_mmap(struct file* fp, struct vm_area_struct* vma) {
    // TODO
}
```

完成内存映射的核心函数是`remap_pfn_range()`，它将连续的物理地址空间映射到由`vm_area_struct`表示的虚拟地址空间：

```C
int remap_pfn_range (structure vm_area_struct *vma, unsigned long addr,
                     unsigned long pfn, unsigned long size, pgprot_t prot);
```

* `vma`：被映射的虚拟地址空间，也就是`proc_mmap()`中的参数——`vma`
* `addr`：虚拟地址空间的开始地址——`vma->vm_start`
* `pfn`：虚拟地址空间需要被映射到的物理页的页框号（page frame number）
* `size`：需要被映射的地址空间大小——`vma->vm_end - vma->vm_start`
* `prot`：映射保护标记——`vma->vm_page_prot`

可见，`remap_pfn_range()`函数的6个参数中除了`pfn`以外的参数都已经内含于`vm_area_struct`结构体`vma`中。`pfn`是物理页对应的页框号，可通过`page_to_pfn()`宏从`struct page`结构体得到。

**具体实现：**

```C
static int proc_mmap(struct file* fp, struct vm_area_struct* vma) {
    // TODO
    unsigned long pfn = page_to_pfn(page);
    unsigned long len = vma->vm_end - vma->vm_start;

    int ret = remap_pfn_range(vma, vma->vm_start, pfn, len, vma->vm_page_prot);
    if (ret < 0) {
        pr_err("could not map the address area\n");
        return -EIO;
    }
    
    return 0;
}
```

### 实现结果

![image-20220520014327801](https://michael-picgo.obs.cn-east-3.myhuaweicloud.com/img/image-20220520014327801.png)

## 心得体会

本次Lab让我深入理解了进程地址空间的概念。过去在学习《操作系统》课程时，我只是了解到进程与线程的地址空间隔离、有一个页表用于索引地址、每个进程有一个Process Control Block来控制全部上下文，但这些都流于泛泛而谈。当不知道实现细节时，我只知道大体思路，只能回答一些概念性的问题，理解也是不深刻的。

因此，我虽然学习过《操作系统》、《计算机组成》、《计算机体系结构》这三门课，但是他们在我的知识体系中是孤立的，本次实验一定程度上帮我打通了他们之间的脉络。

