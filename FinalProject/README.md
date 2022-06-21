

`do_task_stat`函数负责写`/proc/<pid>/stat`文件

`whole`=1或0时有不同的函数来更新`cutime`、`cstime`

![image-20220617162725588](https://michael-picgo.obs.cn-east-3.myhuaweicloud.com/image-20220617162725588.png)

进程如果是进程组的leader，whole=0，使用`task_cputime_adjusted(task, &utime, &stime);`

如果不是进程组的leader，whole=1，使用`thread_group_cputime_adjusted(task, &utime, &stime);`

tid和tid的区别：

<img src="https://michael-picgo.obs.cn-east-3.myhuaweicloud.com/image-20220617162139845.png" alt="image-20220617162139845" style="zoom:67%;" />

If pmd is NULL, pte is also NULL.

When ptep is none, ptep_test_and_clear_young(ptep)=0.

模块无法访问kernel路径下的文件

python无法使用open读取proc文件，试过改proc read函数，但是总是killed。

多写一些qt的thread和process，注重同步机制

![image-20220621181624116](https://michael-picgo.obs.cn-east-3.myhuaweicloud.com/image-20220621181624116.png)

这段代码必须要写在构造函数当中，否则thread启动后，开始的变量被回收了，thread就变成了僵尸线程

在C++的实例中worker是一个pointer，所以可以是临时变量，这样虽然pointer本身会随着构造函数而消失，但是new出来的空间不会消失。而在python中必须要worker和workerthread定义成成员变量（self.），否则都会随着构造函数而解析掉

使用page的问题：

1. 可能在interval内testbench多次读写同一个页，但是我们只计一次
2. 无法判断内存读写是否连续
3. 集中读取同一页、与分散读取多个页，无法区分