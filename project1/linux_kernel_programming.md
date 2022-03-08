# Linux内核编程

## 任务

### 任务一： 简易计算器
1. 编写带命令行参数的内核模块
2. 可以通过`\proc`文件系统进行*读取* 和*写入*

### 任务二： 模拟ps指令

## Linux 内核代码结构

### 内核函数模板
```c
#include <linux/kernel.h>
#include <linux/module.h>
#include <linux/proc_fs.h>
#include <linux/uaccess.h>

#define MAX_SIZE 128
#define ID "519021911058"

static int operand1;
module_param(operand1, int, 0);
static char *operator;
module_param(operator, charp, 0);
static int operand2[MAX_SIZE];
static int ninp;
module_param_array(operand2, int, &ninp, 0);

static struct proc_dir_entry *proc_ent;
static struct proc_dir_entry *proc_dir;
static char output[MAX_SIZE];
int out_len;

static ssize_t proc_read(struct file *fp, char __user *ubuf, size_t len, loff_t *pos)
{
    /* TODO */
}

static ssize_t proc_write(struct file *fp, const char __user *ubuf, size_t len, loff_t *pos)
{
    /* TODO */
}

static const struct proc_ops proc_ops = {
    .proc_read = proc_read,
    .proc_write = proc_write,
};

static int __init proc_init(void)
{
    /* TODO */
}

static void __exit proc_exit(void)
{
    /* TODO */
}

module_init(proc_init);
module_exit(proc_exit);
MODULE_LICENSE("GPL");
```
### 内核的出入口：`__init`和`__exit`宏

带`__init`的函数是程序的入口，是内核的初始化函数，内核在被加载时会执行它。对于内置模块（不可加载）模块来说，带`__init`的函数执行完以后会释放内存。

带`__exit`的函数是程序的出口，时内核的清理函数，内核在被删除时会执行它。对于内置模块（不可加载）模块来说，带`__exit`的函数不会得到执行。

```c
static int __init proc_init(void) //程序入口
{
    /* TODO */
}

static void __exit proc_exit(void) //程序出口
{
    /* TODO */
}
```
### 添加命令行参数

## `/proc`文件系统

### `/proc`简介

`/proc`文件系统的名字是process（进程）的简写，是内核（内核模块）与其他进程进行通信的机制。不同于一般位于磁盘(Disk)上的文件系统，`/proc`文件系统完全位于内存(Memory)中，因此当计算机重启时`/proc`文件系统中的内容都会清空。

### `proc_ops`结构

`proc_ops`结构体的作用是**告诉内核：当对应的文件系统的被读取（或写入）时执行什么对应的函数**。注意：`proc_ops`是在内核版本v5.6+定义，之前版本使用`file_operations`，它比`proc_ops`有更多冗余。
### 操作`/proc`文件系统的内核代码

https://sysprog21.github.io/lkmpg/#the-procops-structure