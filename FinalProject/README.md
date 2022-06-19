

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