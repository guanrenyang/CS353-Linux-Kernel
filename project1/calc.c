#include <linux/kernel.h>
#include <linux/module.h>
#include <linux/proc_fs.h>
#include <linux/uaccess.h>

#define MAX_SIZE 128
#define ID "519021911058"
#define PROC_NAME "calc"

static int operand1;
module_param(operand1, int, 0);
static char *operator;
module_param(operator, charp, 0);
static int operand2[MAX_SIZE];
static int ninp;
module_param_array(operand2, int, &ninp, 0);

static struct proc_dir_entry *proc_ent;
static struct proc_dir_entry *proc_dir;
static int output[MAX_SIZE];
int out_len;

static ssize_t proc_read(struct file *fp, char __user *ubuf, size_t len, loff_t *pos)
{   

    if(out_len!=0 && *pos>=out_len) {
        pr_info("LOG: copy done");
        return 0;
    }

    // 判断操作符`operator`，执行对应操作或输出错误信息
    if (operator!=NULL&&!strcmp(operator, "add")) {
        int i;
        for (i = 0; i < ninp; i++)
        {
            output[i] = operand1+operand2[i];
        }
    } else if(operator!=NULL&&!strcmp(operator, "mul")) {
        int i;
        for (i = 0; i < ninp; i++)
        {
            output[i] = operand1*operand2[i];
        }
    } else {
        pr_err("ERROR:operator is uncorrect!");
        return 0;
    }
    
    // 将计算出来的结果（int数组）转换为字符串
    char output_buffer[10*MAX_SIZE]="";
    
    int i = 0;
    for ( i = 0; i < ninp; i++)
    {   
        char int_buffer[4];
        snprintf(int_buffer, 4, "%d", output[i]);
        strcat(output_buffer, int_buffer);
        if (i!=ninp-1)
            strcat(output_buffer, ",");
        else
            strcat(output_buffer, "\n");
    }
    
    // 计算输出字符串的长度
    out_len = strlen(output_buffer);

    // if(*pos>=out_len) {
    //     pr_info("LOG: copy done");
    //     return 0;
    // }
    
    // 将结果从内核空间拷贝到用户空间并自增偏移量`*pos`
    int err;
    err = copy_to_user(ubuf, output_buffer, out_len); 
    if(err){
        pr_alert("ERROR: fail to copy to user");
    } else {
        pr_info("LOG: copy to user");
        *pos += out_len;
    }

    return out_len;
}

static ssize_t proc_write(struct file *fp, const char __user *ubuf, size_t len, loff_t *pos)
{
    /* TODO */
    char buffer[10];
    if(copy_from_user(buffer, ubuf, len)){
        pr_err("ERROR: fail to copy from file!");
        return len;
    }
    buffer[len-1]='\0';
    
    
    if(strlen(buffer)==0){
        pr_err("ERROR: write number error!");
        return len;
    }

    char *end;
    long long res = simple_strtoll(buffer, &end, 10);
    pr_info("res: %lld", res);
    operand1 = (int) res;
    pr_info("operand1: %d", operand1);
    return len;
} 

static const struct proc_ops proc_ops = {
    .proc_read = proc_read,
    .proc_write = proc_write,
};

static int __init proc_init(void)
{
    /* TODO */
    // 在`/proc`下创建以学号命名的路径:
    proc_dir = proc_mkdir(ID, NULL); 
    if(proc_dir==NULL) {
        pr_alert("ERROR:Could not create directory /proc/%s\n", ID);
        return -ENOMEM;
    }
    // 在`/proc/519021911058`下创建创建文件`calc`:
    proc_ent = proc_create(PROC_NAME, 0, proc_dir, &proc_ops);
    if (proc_ent==NULL){
        proc_remove(proc_dir);
        pr_alert("ERROR:Could not initialize /proc/%s/%s\n", ID, PROC_NAME); 
        return -ENOMEM; 
    }
    
    pr_info("/proc/%s/%s created\n", ID, PROC_NAME);
    
    // 返回`0`, 表示成功初始化模块
	return 0;
}

static void __exit proc_exit(void)
{
    
    /* TODO */

    // 删除`/proc/519021911058`整个路径
    proc_remove(proc_dir);
    
    printk( KERN_INFO "/proc/%s removed\n", ID);
    
}

module_init(proc_init);
module_exit(proc_exit);
MODULE_LICENSE("GPL");
