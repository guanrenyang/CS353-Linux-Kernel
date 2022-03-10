## 要完成的功能
1. cd
2. ls
3. cat

## 操作<dirent.h>

### 打开路径（`cd` <- `DIR *opendir (const char *filename)`）

#### struct `DIR`

结构体`DIR`是操作一个路径的句柄（handler）, 它的具体结构对于用户来说时不可见的. 在<dirent.h>的源文件中是这样说的：

```C
/* This is the data type of directory stream objects.
   The actual structure is opaque to users.  */
typedef struct __dirstream DIR;
```

#### 打开路径函数`opendir`

函数声明如下(易理解的版本)
```c
DIR *opendir (const char *filename)
```
`opendir`函数将一个路径打开, 它提取出了传入路径的相关的信息, 输入参数为一个表示路径的**C字符串**, 返回一个DIR结构体的地址.

以下这段代码*调用`opendir`函数打开`/proc`路径*：
```c
int main(void)
{
    /* TODO */
    DIR *dir; //定义DIR指针用于接受打开的路径
    char proc_path[]="/proc"; //要打开的路径名
    dir = opendir(proc_path); //打开路径
    if(!dir){  //如果打开失败的错误判断
        printf("ERROR: fail to open `/proc` directory!\n");
        return -1;
    }

    return 0;
}
```
### 读取路径（`ls` <- `readdir`）

#### `dirent`结构体

`dirent`结构体是`readdir`（read directory）函数的返回值，它包含了从路径中读取到的信息。`dirent`结构体所含的内容如下：

```c
struct dirent
   {
    __ino_t d_ino;   //索引节点号
    __off_t d_off;   //节点在目录中的偏移量

    unsigned short int d_reclen; //文件名的长度
    unsigned char d_type;        //文件类型
    char d_name[256];            //文件名
   };
```
每一个`dirent`结构体保存了一个文件（或路径）的信息，其中路径的文件类型为`dtype=='EOF'`（ASCII码为4），文件的文件类型为`d_type=='BS'`(ASCII为8).
#### `readdir`函数

`readdir`函数读取一个路径（代表路径的DIR结构体的地址）, 输入参数为一个表示路径的`DIR`结构体指针, 返回一个`dirent`结构体的地址.

```c
struct dirent *readdir (DIR *dir_pointer)
```

`readdir`读取一个路径时流式读取，即第一次调用读取第一个文件，第二次调用读取第二个文件，以此类推，如果连读读取两次（如下图）

```c
int main(void)
{
    /* TODO */
    DIR *dir_pointer; //定义DIR指针用于接受打开的路径
    char proc_path[]="/home/guanrenyang/linux"; //要打开的路径名
    dir_pointer = opendir(proc_path); //打开路径
    if(!dir_pointer){  //如果打开失败的错误判断
        printf("ERROR: fail to open `/proc` directory!\n");
        return -1;
    }
    /***readdir***/
    struct dirent * filename_1;
    struct dirent * filename_2;
    filename_1 = readdir(dir_pointer); // 第一次读取
    filename_2 = readdir(dir_pointer); // 第二次读取
    printf("filename:%-10s\td_type:%d\t d_reclen:%us\n",
         filename_1->d_name,filename_1->d_type,filename_1->d_reclen);
    printf("filename:%-10s\td_type:%d\t d_reclen:%us\n",
         filename_2->d_name,filename_2->d_type,filename_2->d_reclen);

    return 0;
}
```

则会读取到路径下的第一、第二个文件。如果要**读取所有文件**，一般使用一个`while`循环：
```c
int main(void)
{
    /* TODO */
    DIR *dir_pointer; //定义DIR指针用于接受打开的路径
    char proc_path[]="/home/guanrenyang/linux"; //要打开的路径名
    dir_pointer = opendir(proc_path); //打开路径
    if(!dir_pointer){  //如果打开失败的错误判断
        printf("ERROR: fail to open `/proc` directory!\n");
        return -1;
    }

    /*** readdir ***/
    struct dirent * filename;
    while ((filename = readdir(dir_pointer))) //读取完路径以后会跳出while循环
    {
        printf("filename:%-10s\td_type:%d\t d_reclen:%us\n",
        filename->d_name,filename->d_type,filename->d_reclen);
    }

    return 0;
}
```

_注意：while中的赋值语句一定要再用一个括号括起来，这是为了显示告诉编译器：**我真的是要使用赋值语句，而不是把==写成了=**。_

很多指令的cmd长度为0，要用[name]来代替。
不在内核中，strlen不会记录换行符
status最后一个换行符要去掉
strncpy指定个数时也不需要考虑最后的\0
cmdline文件不换行地存了多个字符串，需要按字符读取
1. pid:路径名
2. cmd：cmdline
3. state：status文件中的state
