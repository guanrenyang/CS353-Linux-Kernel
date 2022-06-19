#include <linux/kernel.h>
#include <linux/module.h>
#include <linux/proc_fs.h>
#include <linux/uaccess.h>
#include <linux/string.h>
#include <linux/sched.h>
#include <linux/sched/cputime.h>
#include <linux/sched/signal.h>
#include <linux/mm.h>
#include <linux/types.h>
#include <linux/timer.h>
#include <asm/pgtable_types.h>
#include <asm/page_types.h>
#define MAX_SIZE 128

static struct proc_dir_entry *proc_ent;
static char output[MAX_SIZE];
static int out_len;
static struct task_struct* taskp = NULL; // the task_struct with the inputed pid

__u64 total_utime;
__u64 total_stime;
__u64 total_cutime;
__u64 total_cstime;

//DEBUG
unsigned long long num_pte_valid=0, num_pte_none = 0;
int pid_is_tgid = 1;
/* fuse `thread_group_cputime_adjusted` and `thread_group_cputime` */
static void my_thread_group_cputime_adjusted(struct task_struct *task, __u64 *utime, __u64 *stime){
    struct task_struct *t;
    *utime = task->signal->utime;
    *stime = task->signal->stime;

    for_each_thread(task, t) {
        *utime += t->utime;
        *stime += t->stime;
    }
}
static void my_task_cputime_adjusted(struct task_struct *task, __u64 *utime, __u64 *stime) {
    *utime = task->utime;
    *stime = task->stime;
}
static int get_time(struct task_struct *task, __u64 *utime, __u64 *stime, __u64 *cutime, __u64 *cstime)
{
    *cutime = task->signal->cutime;
    *cstime = task->signal->cstime;

    if(task->pid==task->tgid)
    {
        my_thread_group_cputime_adjusted(task, utime, stime);
        pid_is_tgid = 1;
    } 
    else 
    {
        my_task_cputime_adjusted(task, utime, stime);
        pid_is_tgid = 0;
    }
    return 0;
}
/* Clear a bit and return its old value, not atomic */
static int my_test_and_clear_bit(int nr, unsigned long *addr)
{
	unsigned long mask = BIT_MASK(nr);
	unsigned long *p = ((unsigned long *)addr) + BIT_WORD(nr);
	unsigned long old;

	old = *p;
	*p = old & ~mask;

	return (old & mask) != 0;
}
static int my_ptep_test_and_clear_young(pte_t *ptep){
    int is_pte_young = 0;
    int ret = 0;

    // `pte_young`
    is_pte_young = _PAGE_ACCESSED & PTE_FLAGS_MASK & ptep->pte;
    
    if(is_pte_young)
    {
        //DEBUG: to test whether the `yount` bit is cleared correctly
        // pr_info("Before clear: %#lx", ptep->pte);
        ret = my_test_and_clear_bit(_PAGE_BIT_ACCESSED, (unsigned long *) &ptep->pte);
        // pr_info("After  clear: %#lx", ptep->pte);
    }


    // //DEBUG
    // if(ret>0){
    //     pr_alert("DEBUG: ret = %d", ret);
    // }
    return ret;
}
static pte_t *find_pte_from_address(struct vm_area_struct *vma, unsigned long addr) {
    pgd_t *pgd;
    p4d_t *p4d;
    pud_t *pud;
    pmd_t *pmd;
    pte_t *pte;

    pgd = pgd_offset(vma->vm_mm, addr);
    if(pgd_none(*pgd) || pgd_bad(*pgd))
    {
        // pr_alert("pgd is null\n");
    }
    
    p4d = p4d_offset(pgd, addr);
    if (p4d_none(*p4d) || p4d_bad(*p4d))
    {
        // pr_alert("p4d is null\n");
    }

    pud = pud_offset(p4d, addr);
    if (pud_none(*pud) || pud_bad(*pud))
    {
        // pr_alert("pud is null\n");
    }

    pmd = pmd_offset(pud, addr);
    if(pmd_none(*pmd) || pmd_bad(*pmd))
    {
        // pr_alert("pmd is null\n");
    }

    pte = pte_offset_kernel(pmd, addr);
    if(pte_none(*pte))
    {
        // pr_alert("pte is null\n");
    }

    return pte;

}
static unsigned long long get_accessed_page_num(struct task_struct *taskp){
    int res;
    unsigned long long sum = 0;
    pte_t *ptep;
    struct vm_area_struct *vmap = taskp->mm->mmap;
    unsigned long addr;

    while (vmap!=NULL)
    {
        for (addr = vmap->vm_start; addr < vmap->vm_end; addr += PAGE_SIZE)
        {
            ptep = find_pte_from_address(vmap, addr);
            res = my_ptep_test_and_clear_young(ptep);
            sum+=res;

            // to calculate the number of valid/invalid ptes
            if (pte_none(*ptep)) {   
                num_pte_none++;
            }
            else {
                num_pte_valid++;
            }
        }
        vmap = vmap->vm_next;
    }

    return sum;
}
static ssize_t proc_read(struct file *fp, char __user *ubuf, size_t len, loff_t *pos)
{
    int count; /* the number of characters to be copied */

    __u64 utime;
    __u64 stime;
    __u64 cutime;
    __u64 cstime;
    
    unsigned long long num_accessed_page;
    if (*pos == 0) {
        /* a new read, update process' status */
        /* TODO */

        utime = stime = cutime = cstime = 0;
        
        if (taskp!=NULL)
        {   
            pr_info("LOG: valid task pointer");
            pr_info("LOG: get_time");
            get_time(taskp, &utime, &stime, &cutime, &cstime);

            pr_info("DEBUG: pid=tgid: %d", pid_is_tgid);

            pr_info("LOG: get_accessed_page_num");
            num_accessed_page = get_accessed_page_num(taskp);

            pr_info("DEBUG: delta\nutime: %lld\nstime: %lld\ncutime: %lld\ncstime: %lld\nnum_accessed_page: %lld\n", 
                utime-total_utime, stime-total_stime, cutime-total_cutime, cstime-total_cstime, num_accessed_page);

            sprintf(output, "pid: %d\nutime: %lld\nstime: %lld\ncutime: %lld\ncstime: %lld\nnum_accessed_page: %lld\n", 
                taskp->pid, utime, stime, cutime, cstime, num_accessed_page);
            out_len = strlen(output);
        } 
        else 
            out_len = 0;

    }

    if (out_len - *pos > len) {
        count = len;
    } else {
        count = out_len - *pos;
    }

    pr_info("LOG: Reading the proc file\n");
    if (copy_to_user(ubuf, output + *pos, count)) return -EFAULT;
    *pos += count;
    
    return count;
}

static ssize_t proc_write(struct file *fp, const char __user *ubuf, size_t len, loff_t *pos)
{
    int pid;

    if (*pos > 0) return -EFAULT;
    pr_info("LOG: Writing the proc file\n");
    if(kstrtoint_from_user(ubuf, len, 10, &pid)) return -EFAULT;
    
    taskp = get_pid_task(find_get_pid(pid), PIDTYPE_PID);

    get_time(taskp, &total_utime, &total_stime, &total_cutime, &total_cstime);// record the starting time
    get_accessed_page_num(taskp);// clear `young` of all pages 

    pr_info("DEBUG: num_pte_valid: %lld, num_pte_none: %lld", num_pte_valid, num_pte_none);
    *pos += len;
    return len;
}

static const struct proc_ops proc_ops = {
    .proc_read = proc_read,
    .proc_write = proc_write,
};

static int __init watch_init(void)
{
    proc_ent = proc_create("watch", 0666, NULL, &proc_ops);
    if (!proc_ent) {
        proc_remove(proc_ent);
        pr_alert("Error: Could not initialize /proc/watch\n");
        return -EFAULT;
    }
    pr_info("LOG: /proc/watch created\n");
    
    return 0;
}

static void __exit watch_exit(void)
{
    proc_remove(proc_ent);
    pr_info("LOG: /proc/watch removed\n");
}

module_init(watch_init);
module_exit(watch_exit);
MODULE_LICENSE("GPL");