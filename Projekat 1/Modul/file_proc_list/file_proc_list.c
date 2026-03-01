#include <linux/module.h>
#include <linux/kernel.h>
#include <linux/init.h>
#include <linux/fs.h>
#include <linux/namei.h>
#include <linux/sched/signal.h>
#include <linux/fdtable.h>
#include <linux/rcupdate.h>
#include <linux/mm.h>
#include <linux/cred.h>

MODULE_LICENSE("GPL");
MODULE_AUTHOR("Stefan");
MODULE_DESCRIPTION("List processes that use a specific file");

static char *filepath = NULL;
module_param(filepath, charp, 0000);
MODULE_PARM_DESC(filepath, "Path to target file");

static int __init file_users_init(void)
{
    struct path path;
    struct inode *target_inode;
    struct task_struct *task;
    int ret;

    if (!filepath) {
        printk(KERN_INFO "No file path provided\n");
        return -EINVAL;
    }

    ret = kern_path(filepath, LOOKUP_FOLLOW, &path);
    if (ret) {
        printk(KERN_INFO "File not found: %s\n", filepath);
        return ret;
    }

    target_inode = d_inode(path.dentry);

    printk(KERN_INFO "Target file: %s\n", filepath);
    printk(KERN_INFO "Target inode: %lu\n", target_inode->i_ino);

    rcu_read_lock();

    for_each_process(task) {

        struct files_struct *files = task->files;
        struct fdtable *fdt;
        unsigned int i;

        if (!files)
            continue;

        spin_lock(&files->file_lock);
        fdt = files_fdtable(files);

        for (i = 0; i < fdt->max_fds; i++) {

            struct file *file = fdt->fd[i];

            if (!file)
                continue;

            if (file_inode(file) == target_inode) {

                unsigned long mem_usage = 0;
                unsigned long cpu_time = 0;

                if (task->mm)
                    mem_usage = get_mm_rss(task->mm) << PAGE_SHIFT;

                cpu_time = (task->utime + task->stime) / HZ;

                printk(KERN_INFO
                       "PID: %d | COMM: %s | PRIO: %d | NICE: %d | UID: %u | MEM: %lu KB | CPU: %lu s\n",
                       task->pid,
                       task->comm,
                       task->prio,
                       task_nice(task),
                       __kuid_val(task->cred->uid),
                       mem_usage / 1024,
                       cpu_time);
            }
        }

        spin_unlock(&files->file_lock);
    }

    rcu_read_unlock();

    path_put(&path);

    return 0;
}

static void __exit file_users_exit(void)
{
    printk(KERN_INFO "Module removed\n");
}

module_init(file_users_init);
module_exit(file_users_exit);