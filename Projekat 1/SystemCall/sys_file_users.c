#include <linux/kernel.h>
#include <linux/sched.h>
#include <linux/fs.h>
#include <linux/fdtable.h>
#include <linux/slab.h>
#include <linux/uaccess.h>
#include <linux/cred.h>
#include <linux/time.h>
#include <linux/syscalls.h>
#include <linux/path.h>
#include <linux/namei.h>
#include <linux/dcache.h>
#include <linux/mount.h>

struct proc_info {
    pid_t pid;
    int priority;
    int nice;
    uid_t uid;
    unsigned long vm_size;
    long utime;
    long stime;
};

SYSCALL_DEFINE2(find_procs_by_file, const char __user *, path, struct proc_info __user *, out)
{
    struct file *f;
    struct inode *inode;
    struct task_struct *task;
    struct fdtable *fdt;
    struct path p;
    int copied = 0;

    if (kern_path(path, LOOKUP_FOLLOW, &p))
        return -ENOENT;

    inode = p.dentry->d_inode;
    path_put(&p);

    rcu_read_lock();
    for_each_process(task) {
        int fd;
        task_lock(task);
        fdt = files_fdtable(task->files);
        for (fd = 0; fd < fdt->max_fds; fd++) {
            f = fdt->fd[fd];
            if (f && f->f_inode == inode) {
                struct proc_info info;
                info.pid = task->pid;
                info.priority = task->prio;
                info.nice = task_nice(task);
                info.uid = __kuid_val(task->cred->uid);
                info.vm_size = task->mm ? task->mm->total_vm << PAGE_SHIFT : 0;
                info.utime = task->utime;
                info.stime = task->stime;

                if (copy_to_user(&out[copied], &info, sizeof(info))) {
                    task_unlock(task);
                    rcu_read_unlock();
                    return -EFAULT;
                }
                copied++;
                break;
            }
        }
        task_unlock(task);
    }
    rcu_read_unlock();
    return copied;
}