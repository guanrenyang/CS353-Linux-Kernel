# Linux内核编程
## 我的观察
内核对全局变量的赋值先于__init函数
## 任务

### 任务一： 简易计算器
1. 编写带命令行参数的内核模块
2. 可以通过`\proc`文件系统进行*读取* 和*写入*



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

下面是事例代码片段：
```c
static ssize_t proc_read(struct file *fp, char __user *ubuf, size_t len, loff_t *pos){
    /* TODO */
}

static ssize_t proc_write(struct file *fp, const char __user *ubuf, size_t len, loff_t *pos){
    /* TODO */
}
// 暂时可以不需要关注以上两个函数的声明和实现
// 只需要知道在读取(写入)/proc文件系统时执行proc_read(proc_write)
static const struct proc_ops proc_ops = {   
    .proc_read = proc_read,
    .proc_write = proc_write,
};
```
### 操作`/proc`文件系统的内核代码
#### 在`/proc`下操作文件

在`/proc`文件系统下创建文件（例如`/proc/helloworld`）需要在内核模块的*入口* 函数中使用`proc_create`函数进行创建，它返回一个结构体(struct)`proc_dir_entry`，这个文件可以被用来配置`/proc/helloworld`，如果`proc_create`返回了`NULL`就说明创建不成功。

#### 用户空间和内核空间
Linux 内存(在Intel体系结构上)是分段的，这意味着指针本身并不指向内存中的唯一位置，只指向内存段中的一个位置，而不同的内存段有不同权限。内核有一个属于内核的段，每个进程都有自己的段，他们只能访问自己的段。

这一点在写单个线程的代码时无关紧要，但是在写内核代码时就需要考虑到。用户读写`/proc`文件系统时是在用户空间发出信息，换言之是将一个指向用户段的指针传给了内核，此时内核无法访问指针指向的空间，就需要使用`copy_from_user`或者`get_user`来授予内核访问权限。

#### `/proc`文件系统的读写处理函数

1. `proc_read()`函数在`proc_ops`结构中“注册”，会在用户读取（例如`cat`指令）`/proc`文件系统的对应模块时得到执行。需要注意的是**用户读取`/proc`时要使用`copy_to_user`将变量从内核空间移动到用户空间。**
2. `proc_write()`函数在`proc_ops`结构中“注册”，会在用户写入（例如`echo`指令）`/proc`文件系统的对应模块的时候得到执行。需要注意的是**用户读取`/proc`时要使用`copy_from_user`或`get_user`函数将变量从用户空间移动到内核空间。**

## `proc_read`函数的机制测试
使用这一代码
```C
static ssize_t proc_read(struct file *fp, char __user *ubuf, size_t len, loff_t *pos)
{
    /* TODO */
    pr_info("pos 1:%lld", *pos);
    char s[13] = "HelloWorld!\n"; 
    int l = sizeof(s); 
    ssize_t ret = l; 
    // pr_info("len: %ld", len);
    if (*pos >= 26 || copy_to_user(ubuf, s, l)) { 
        pr_info("pos 2:%lld", *pos);
        pr_info("copy_to_user failed\n"); 
        ret = 0; 
    } else { 
        pr_info("procfile read %s\n", fp->f_path.dentry->d_name.name); 
        pr_info("pos 3:%lld", *pos);
        *pos += l; 
    } 
    pr_info("pos 4:%lld", *pos);
    return ret; 
}
```
得到的结果为
使用这个代码，cat没有输出，而且最后一个打印*pos的指令总是被忽略掉。
```c
static ssize_t proc_read(struct file *fp, char __user *ubuf, size_t len, loff_t *pos)
{
    /* TODO */
    pr_info("pos 1:%lld", *pos);
    char s[13] = "HelloWorld!\n"; 
    int l = sizeof(s); 
    ssize_t ret = l; 
    // pr_info("len: %ld", len);

    if (copy_to_user(ubuf, s, l))
        pr_info("error");
    *pos+=l;

    pr_info("pos 2:%lld", *pos);

    if (copy_to_user(ubuf, s, l))
        pr_info("error");
    *pos+=l;

    pr_info("pos 3:%lld", *pos);
    if(*pos>=26){
        ret = 0;
    }
    pr_info("pos 4:%lld", *pos);
    pr_info("pos 5:%lld", *pos);
    pr_info("pos 6:%lld", *pos);
    return 13; 
}
```
使用这个代码，第一次helloworld完整插入，第二次只返回了一个H，但是使用vim打开/proc文件系统calc文件时发现两个helloworld都完整插入
```c
static ssize_t proc_read(struct file *fp, char __user *ubuf, size_t len, loff_t *pos)
{
    pr_info("pos 1:%lld", *pos);
    char s[13] = "HelloWorld!\n"; 
    int l = sizeof(s); 
    ssize_t ret = l; 
    /* TODO */
    if(*pos>=26){
        return 0;
    }
    if (*pos >=13)
    {
        copy_to_user(ubuf, s, 13);
        *pos+=13;
        return 1;
    }
    
    copy_to_user(ubuf, s, 13);
    *pos+=13;

    return ret; 
}
```
使用这个代码，可以完整插入，可见：`proc_read`的返回值很关键
```c
static ssize_t proc_read(struct file *fp, char __user *ubuf, size_t len, loff_t *pos)
{
    pr_info("pos 1:%lld", *pos);
    char s[13] = "HelloWorld!\n"; 
    int l = sizeof(s); 
    ssize_t ret = l; 
    /* TODO */
    if(*pos>=26){
        return 0;
    }
    if (*pos >=13)
    {
        copy_to_user(ubuf, s, 13);
        *pos+=13;
        return ret;
    }
    
    copy_to_user(ubuf, s, 13);
    *pos+=13;

    return ret; 
}
```
使用这个代码，*pos的输出正常，但是cat只输出一行helloworld，vim查看calc中有14个换行符ctrl @（1个来自第一个helloworld\n）。猜想proc_read的返回值表示本次copy了多少个字节。
```c
static ssize_t proc_read(struct file *fp, char __user *ubuf, size_t len, loff_t *pos)
{
    pr_info("pos 1:%lld", *pos);
    char s[13] = "HelloWorld!\n"; 
    int l = sizeof(s); 
    ssize_t ret = l; 
    // pr_info("len: %ld", len);
    if(*pos>=26){
        ret = 0;
        return 0;
    }
    if (copy_to_user(ubuf, s, l))
        pr_info("error");
    *pos+=l;

    pr_info("pos 2:%lld", *pos);

    if (copy_to_user(ubuf, s, l))
        pr_info("error");
    *pos+=l;

    pr_info("pos 3:%lld", *pos);
    
    pr_info("pos 4:%lld", *pos);
    pr_info("pos 5:%lld", *pos);
    pr_info("pos 6:%lld", *pos);
    return 26; 
}
```
## 一些要点
1. 输出的时候要把int转为char再输出，可以使用snpirntf来格式化输出到字符串
2. 不能返回-EFAULT，不知道调用者会得到错误码以后会干什么（问老师）
3. read要返回0，write不能返回0
4. proc_write会导致最后带有一个'\n'，len变量也计算了这个换行符，需要在 `copy\_from\_user` 以后显示换为'\0'，len=有效长度+'\0'的长度。strlen会计入\0
5. linux内核中的整数和字符串转换函数[link](https://www.cnblogs.com/pengdonglin137/articles/4125746.html)

**最大的问题：proc_read提前return了但是后面的还是得到执行**
**第一次cat的时候，pr_err语句得不到执行**
**为什么官方代码不直接返回0，而是等到第二次再返回0；即为什么proc_read一定要执行两次**
https://sysprog21.github.io/lkmpg/#the-procops-structure

### 任务二： 模拟ps指令
1. opendir()用来打开参数name 指定的目录, 并返回DIR*形态的目录流, 和open()类似, 接下来对目录的读取和搜索都要使用此返回值.
2. dirent.h使用[link](https://blog.csdn.net/dream_allday/article/details/75243818)
