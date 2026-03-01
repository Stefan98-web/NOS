#define _GNU_SOURCE
#include <stdio.h>
#include <unistd.h>
#include <sys/syscall.h>
#include <errno.h>
#include <string.h>
#include <sys/types.h>

#define __NR_find_procs_by_file 449

struct proc_info {
    pid_t pid;
};

int main(int argc, char *argv[])
{
    if (argc != 2) {
        printf("Usage: %s <path>\n", argv[0]);
        return 1;
    }

    struct proc_info buffer[128];

    long ret = syscall(__NR_find_procs_by_file,
                       argv[1],
                       buffer);

    if (ret < 0) {
        printf("Syscall failed: %s (errno=%d)\n",
               strerror(errno), errno);
        return 1;
    }

    printf("Syscall returned %ld entries\n", ret);

    for (int i = 0; i < ret; i++) {
        printf("PID: %d\n", buffer[i].pid);
    }

    return 0;
}