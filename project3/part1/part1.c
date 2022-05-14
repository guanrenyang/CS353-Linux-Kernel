#include <linux/kernel.h>
#include <linux/module.h>
#include <linux/sched.h>
#include <asm/page.h>
#include <linux/pgtable.h>
#include <linux/mm_types.h>
#include <linux/pid.h>
#include <linux/proc_fs.h>
#include <linux/uaccess.h>

#define MAX_SIZE 128
#define PROC_NAME "mtest"

static struct proc_dir_entry *proc_ent;
static char output[MAX_SIZE];
static int out_len;

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
// change a char of 16 to 10
inline unsigned long char_to_int(char c)
{
    if (c >= '0' && c <= '9') {
        return c - '0';
    }
    else if (c >= 'a' && c <= 'f') {
        return c - 'a' + 10;
    }
    else if (c >= 'A' && c <= 'F') {
        return c - 'A' + 10;
    }
    else {
        return -1;
    }
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
    
    pr_info("buffer %s",buffer);

    char operator = buffer[0];
    int pid = 0;
    unsigned long address = 0;
    int content = 0;

    int i;
    for (i=2;buffer[i]!=' ';i++){ // buffer[0] is 'r' or 'w', buffer[1] is space
        pid = pid*10 + (buffer[i]-'0');
    }
    i++;
    for (; buffer[i]!='\0'&&buffer[i]!=' ';i++){
        address = address*16 + char_to_int(buffer[i]);
    }
    i++;
    pr_info("address %lx", address);
    if (operator=='w')
    {
        for (;buffer[i]!='\0';i++){
            content = content*10 + (buffer[i]-'0');
        }
        pr_info("%c %d %lx %d", operator, pid, address, content);
    } else {
        pr_info("%c %d %lx", operator, pid, address);
    }
    
    /* TODO 根据PID获取task_struct */
    struct task_struct *task = pid_task(find_vpid(pid), PIDTYPE_PID);
    if (task == NULL) {
        pr_err("ERROR: fail to find task_struct!");
        return len;
    }
    
    // X86 CONFIG_PGTABLE_LEVELS=5
    pgd_t *pgd = pgd_offset(task->mm, address);
	if(pgd_none(*pgd) || pgd_bad(*pgd))
	{
		pr_alert("pgd is null\n");
	}
    
    p4d_t *p4d = p4d_offset(pgd, address);
    if (p4d_none(*p4d) || p4d_bad(*p4d))
	{
		pr_alert("p4d is null\n");
	}

    pud_t *pud = pud_offset(p4d, address);
    if (pud_none(*pud) || pud_bad(*pud))
	{
		pr_alert("pud is null\n");
	}

	pmd_t *pmd = pmd_offset(pud, address);
	if(pmd_none(*pmd) || pmd_bad(*pmd))
	{
		pr_alert("pmd is null\n");
	}

	pte_t *pte = pte_offset_kernel(pmd, address);
	if(pte_none(*pte))
	{
		pr_alert("pte is null\n");
	}
    
    struct page *page = pte_page(*pte);
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