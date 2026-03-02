#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <sys/syscall.h>
#include <string.h>
#include <errno.h>

#define SYS_find_procs_by_file 449
#define MAX_PROCS 1024

struct proc_info {
    pid_t pid;
    int priority;
    int nice;
    uid_t uid;
    unsigned long vm_size;
    unsigned long utime;
    unsigned long stime;
};

int main(int argc, char *argv[])
{
    if (argc != 2) {
        fprintf(stderr, "Usage: %s <file_path>\n", argv[0]);
        return 1;
    }

    const char *path = argv[1];
    struct proc_info results[MAX_PROCS];

    long ret = syscall(SYS_find_procs_by_file, path, results);

    if (ret < 0) {
        perror("syscall failed");
        return 1;
    }

    if (ret == 0) {
        printf("No processes are using file: %s\n", path);
        return 0;
    }

    printf("Processes using file: %s\n\n", path);

    for (int i = 0; i < ret; i++) {
        printf("PID: %d\n", results[i].pid);
        printf("Priority: %d\n", results[i].priority);
        printf("Nice: %d\n", results[i].nice);
        printf("UID: %d\n", results[i].uid);
        printf("Virtual Memory: %lu bytes\n", results[i].vm_size);
        printf("User Time: %lu\n", results[i].utime);
        printf("System Time: %lu\n", results[i].stime);
        printf("---------------------------------\n");
    }

    printf("Total processes found: %ld\n", ret);

    return 0;
}