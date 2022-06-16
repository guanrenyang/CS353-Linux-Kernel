# Project 4

## Task1：隐藏文件

### readdir

隐藏文件在`super.c`的`romfs_readdir`函数中实现。`romfs_readdir`函数读取一个目录下面的各个目录（或文件）。在程序主体的`for(;;)`循环中，`romfs_dev_read`、`romfs_dev_strnlen`和`romfs_dev_read`函数识别出文件名信息，`dir_emit`函数进行文件读取。

在`for(;;)`循环中的`fsname[j]='\0'`语句显著地将一个读取到的字符数组转化为C风格字符串，这也标志着文件名识别结束，文件读取环节的开始。

### 具体实现

隐藏文件代码段具体实现在在`fsname[j]='\0'`语句以后。首先，判断当前的文件名是不是需要隐藏的文件名。如果是，则计算下一次循环的`offset`，并使用`continue`跳过文件读取部分。代码截图如下：

![image-20220616225215856](https://michael-picgo.obs.cn-east-3.myhuaweicloud.com/image-20220616225215856.png)

## Task2：加密文件

### readpage

加密文件任务实现在`romfs_readpage`函数中，它读取文件中一个页大小的数据，将页中数据读进函数中声明的指针`buf`指向的地址空间。`romfs_readpage`函数中的变量`fillsize`是实际读取到的内容大小，`memset`语句将`fillsize`大小以外的内容置零，`SetPageUptodate`语句标志着读取完成。最后的`flush_dcache_page`将缓存中的数据拷贝进内存（保证一致性），`kunmap`与`unlock_page`语句分别取消页的地址空间映射、解锁。

### 从struct file获取文件名

`struct file`结构体定义在`<linux/fs.h>`中，内含`stuct path`类型的成员变量`f_path`。`stuct path`定义在`<linux/path.h>`中，内含`struct dentry *`类型成员变量`dentry`。目录项`struct dentry`中的C风格字符串`d_iname`就是文件名。

### 具体实现

加密文件的代码具体实现在`SetPageUptodate`语句（完成读取）之后。先比较`romfs_readpage`函数参数`struct file *file`对应的文件名与目标文件名。如果相同，则将`buf`指向的连续地址空间的每个字节都加1（加密）。代码截图如下：

![image-20220616232728521](https://michael-picgo.obs.cn-east-3.myhuaweicloud.com/image-20220616232728521.png)

## Task3：更改文件执行权限

### romfs_lookup

更改文件执行权限的任务实现在`romfs_lookup`函数中，它是读取一个目录项的`inode`的第一道关口。可以在该函数读取到`inode`以后、函数返回前，设置文件的执行权限，文件执行权限保存在`struct inode`内含的`umode_t`类型的成员变量`i_mode`中，`i_mode`的每一位代表一个执行权限。`romfs_lookup`函数内的`const char *name`字符串保存着`inode`对应的文件名。

### 具体实现

更改文件执行权限的具体代码实现在`romfs_lookup`函数return之前。先比较当前文件名（`name`）与目标文件名，如果相同，则更改`inode->i_mode`变量的对应位。`<linux/stat.h>`中定义的宏`S_IXOTH`、`S_IXGRP`和`S_IXUSR`分别代表文件所有者、所有者所在组和其他所有用户对文件的可执行权限，将`inode->i_mode`变量与这三个宏执行*按位或* 运算，可以授予完全的可执行权限。代码截图如下：

![image-20220616234312903](https://michael-picgo.obs.cn-east-3.myhuaweicloud.com/image-20220616234312903.png)

## 结果分析

未加载`romfs.ko`模块时，执行结果如下：

![image-20220616153821839](https://michael-picgo.obs.cn-east-3.myhuaweicloud.com/image-20220616153821839.png)

加载`romfs.ko`模块以后，aa文件被成功隐藏，bb文件每一个字符的ASCII码值都+1，cc文件成功执行：

![image-20220616164558469](https://michael-picgo.obs.cn-east-3.myhuaweicloud.com/image-20220616164558469.png)