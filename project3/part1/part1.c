#include <linux/kernel.h>
#include <linux/module.h>
#include <linux/sched.h>
#include <linux/mm_types.h>
#include <linux/proc_fs.h>
#include <linux/uaccess.h>

#define PROC_NAME "mtest"

static struct proc_dir_entry *proc_ent;

static ssize_t proc_read(struct file *fp, char __user *ubuf, size_t len, loff_t *pos)
{
    int count; /* the number of characters to be copied */
    if (out_len - *pos > len) {
        count = len;
    }
    else {
        count = out_len - *pos;
    }

    pr_info("Reading the proc file\n");
    if (copy_to_user(ubuf, output + *pos, count)) return -EFAULT;
    *pos += count;
    
    return count;
}
static ssize_t proc_write(struct file *fp, const char __user *ubuf, size_t len, loff_t *pos)
{
    /* TODO */
    char buffer[30];
    if(copy_from_user(buffer, ubuf, len)){
        pr_err("ERROR: fail to copy from file!");
        return len;
    }
    buffer[len-1] = '\0';
    /* len 计入了末尾的'\0'，所以len-1 */
    
    char operator = buffer[0];
    int pid = 0;
    unsigned int address = 0;
    int content = 0;

    int i;
    for (i=2;buffer[i]!=' ';i++){ // buffer[0] is 'r' or 'w', buffer[1] is space
        pid = pid*10 + (buffer[i]-'0');
    }
    i++;
    for (; buffer[i]!='\n'&&buffer[i]!=' ';i++){
        address = address*10 + (buffer[i]-'0');
    }
    i++;

    if (operator=='w')
    {
        for (;buffer[i]!='\n';i++){
            content = content*10 + (buffer[i]-'0');
        }
        pr_info("%c %d %lx %d", operator, pid, address, content);
    } else {
        pr_info("%c %d %lx", operator, pid, address);
    }
    
    
    /* TODO 向進程對應的地址寫或讀文件*/
    struct task_struct *task = current;
    struct mm_struct *mm = task->mm;
    return len;
} 

static const struct proc_ops proc_ops = {
    .proc_read = proc_read,
    .proc_write = proc_write,
};

static int __init proc_init(void)
{
    /* TODO */
    
    proc_ent = proc_create(PROC_NAME, 0, NULL, &proc_ops);
    if (proc_ent==NULL){
        proc_remove(proc_ent);
        pr_info("ERROR:Could not initialize /proc/%s\n", PROC_NAME); 
        return -ENOMEM; 
    }

    pr_info("/proc/%s created\n", PROC_NAME);

    // 返回`0`, 表示成功初始化模块
	return 0;
}

static void __exit proc_exit(void)
{
    
    /* TODO */
    // 删除`/proc/mtest`文件
    proc_remove(proc_ent);
    
    pr_info("/proc/%s removed\n", PROC_NAME);
    
}

module_init(proc_init);
module_exit(proc_exit);
MODULE_LICENSE("GPL");