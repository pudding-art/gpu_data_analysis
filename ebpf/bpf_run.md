## eBPF对象的生命周期
BPF对象包括BPF maps, BPF programs和调试信息。
1. 创建BPF maps的过程，首先进行bpf(BPF_MAP_CREATE,...)系统调用，内核分配一个struct bpf_map对象，设置改对象的refcnt=1，最后返回一个fd給用户空间。如果进程退出或者崩溃，那么BPFmaps对应的fd也会被关闭，导致refcnt变为0。
2. 加载BPF程序的过程，加载分配两个阶段，一个是创建maps，这些mapsfd之后会放到BPF_LD_IMM64指令的imm字段中, 成为BPF程序的一部分。第二个阶段是对BPF程序进行检验，检验器会把其引用的maps的refcnt++, 并设置改程序的refcnt=1。
3. 将BPF程序attach到hook上，将BPF attach到hook上之后，BPF程序的refcnt++，此时创建, 加载BPF的用户空间程序就可以退出了. 因此还有hook保持着对BPF程序的引用, BPF程序并不会被回收。
4. BPF文件系统(BPFFS),用户空间的程序可以把一个BPF或者BPF maps固定到BPFFS, 以生成一个文件。pin操作会使得BPF对象refcnt++, 因此即使这个BPF程序没有attach到任何地方, 或者一个BPFmaps没有被任何地方使用, 在加载程序退出后, 这些BPF对象任然会存活。如果想要取消某个固定的对象, 只要调用unlink()即可, 也可以直接用rm命令删除这个文件。
### BPF程序的引用计数机制
BPF 程序（以及相关的映射）在内核中使用引用计数来管理其生命周期。引用计数的基本思想是：只要还有某个实体（如用户空间程序、钩子等）在使用BPF程序，它的引用计数就大于0，内核就不会回收它。只有当引用计数降为0时，内核才会释放相关的资源。
### BPFFS
BPFFS（BPF文件系统）的主要用途是提供一种机制，让用户空间程序可以将BPF程序或BPF映射固定到文件系统中，从而实现以下功能：
1. 持久化：即使创建BPF对象的用户空间程序退出，这些对象仍然可以存活，因为它们被固定在文件系统中。
2. 共享：多个用户空间程序可以通过文件系统路径访问和使用同一个BPF对象。
3. 生命周期管理：通过pin和unpin操作，灵活地控制BPF对象的生命周期

BPFFS默认挂载在`/sys/fs/bpf/`路径下。可以通过以下命令查看BPFFS的挂载情况：
```shell
mount -t bpf
```
如果需要自定义挂载路径，可以手动挂载BPFFS到其他目录，但需要确保文件系统类型是BPF_FS_MAGIC。

```c
create -> refcnt=1
attach -> refcnt++
detach -> refcnt--
pin -> refcnt++
unpin -> refcnt--
unlink -> refcnt--
close -> refcnt--
```
## eBPF程序的相关操作
### Load

加载BPF程序的过程主要是通过bpf(BPF_PROG_LOAD, ...) 系统调用将程序的指令注入到内核中。这个过程适用于大多数类型的BPF程序。程序在加载时会经过验证器（verifier）的检查。验证器会执行以下操作：
- 语法检查：验证BPF指令的合法性。
- 安全检查：确保程序不会执行非法操作，如访问越界的内存。
- 指令重写：某些情况下，验证器可能会重写指令，特别是与BPF映射访问相关的指令。

如果启用了JIT编译（Just-In-Time Compilation），验证器通过后，BPF程序可能会被JIT编译成原生机器码。JIT编译可以显著提高BPF程序的执行效率。
加载后的BPF程序在内核内存中以`struct bpf_prog`对象的形式存在。这个对象包含或指向程序的相关信息，包括：
- eBPF字节码。
- 如果进行了JIT编译，还包括JIT编译后的指令。

在这个过程结束时，程序位于内核内存中, 它不依附于特定对象。


引用计数可以通过以下方式增加：
- 文件描述符：加载程序时，bpf() 系统调用会返回一个文件描述符，指向加载的 BPF 程序。这个文件描述符会持有对 BPF 程序的引用。
- Attach 操作：将 BPF 程序 attach 到某个钩子（如 XDP 钩子、cgroup 钩子等）时，钩子会持有对 BPF 程序的引用。
- Link 操作：通过 bpf_link 将 BPF 程序链接到某个对象时，链接会持有对 BPF 程序的引用。
- Pin 操作：将 BPF 程序固定到 BPFFS 中时，文件系统会持有对 BPF 程序的引用。
- prog_array 映射：如果 BPF 程序被引用在 prog_array 映射中，也会增加引用计数。

对于某些程序类型，用户需要在加载时通过bpf_attr结构体的expected_attach_type字段指定预期的attach类型。这个字段用于验证器和系统调用处理程序执行各种验证。加载程序大多与这些attach类型分开。但是某些程序类型需要在加载时就说明附加类型。“附加类型”(attach type)的概念取决于程序类型(prog_type)。有些程序类型没有这个概念：XDP 程序只是附加到接口的 XDP 钩子上。附加到 cgroups 的程序确实有一个“附加类型”，它告诉程序附加到哪里。

## Attach
挂载（Attach）是指将BPF程序绑定到某个特定的钩子（hook）上，使得当该钩子触发时，BPF程序会被执行。挂载过程的具体行为取决于BPF程序的类型和挂载的目标。
当BPF程序被挂载到某个钩子上时，内核中的相关结构会更新，以指向该BPF程序。例如：
- 对于cgroup程序，cgroup_bpf->effective 会指向一个包含struct bpf_prog * 的列表。这意味着内核不会存储BPF程序本身，而是通过指针引用它。
- 当触发该钩子的事件发生时，内核会调用指向的BPF程序。

对于kprobe程序：
- 基于文件描述符的挂载：挂载操作依赖于`perf_event_open()`返回的文件描述符来保持程序的挂载状态。
- 需要持续运行的进程：必须有一个进程保持运行，以持有该文件描述符。如果持有文件描述符的进程退出，BPF程序的引用计数会减少，可能导致程序被卸载。

kprobe允许在内核函数的入口处插入一个断点，当执行到该断点时，内核会调用用户定义的回调函数。kprobe的实现依赖于**内核的断点机制和异常处理机制**。
```c
int fd = perf_event_open(&attr, -1, 0, -1, 0);
if (fd < 0) {
    perror("perf_event_open");
    return -1;
}

struct bpf_link *link = bpf_program__attach_kprobe(prog, false, "vfs_read");
```
在内核函数sys_write上设置kprobe,并在函数入口处执行一个回调函数:
```c
// 定义kprobe结构和回调函数
#include <linux/kprobes.h>
#include <linux/ptrace.h>

static struct kprobe kp = {
    .symbol_name = "sys_write", // 指定要挂钩的内核函数
};

static int handler_pre(struct kprobe *p, struct pt_regs *regs) {
    printk(KERN_INFO "kprobe: sys_write called\n");
    return 0;
}

static void handler_post(struct kprobe *p, struct pt_regs *regs, unsigned long flags) {
    printk(KERN_INFO "kprobe: sys_write finished\n");
}

// 注册和注销kprobe
static int __init kprobe_init(void) {
    kp.pre_handler = handler_pre;
    kp.post_handler = handler_post;

    int ret = register_kprobe(&kp);
    if (ret < 0) {
        printk(KERN_INFO "register_kprobe failed, returned %d\n", ret);
        return ret;
    }
    printk(KERN_INFO "kprobe registered\n");
    return 0;
}

static void __exit kprobe_exit(void) {
    unregister_kprobe(&kp);
    printk(KERN_INFO "kprobe unregistered\n");
}
```
[设置断点]当register_kprobe被调用时，内核会在指定的函数（如 sys_write）的入口处插入一个断点。

[触发回调]当内核执行到sys_write函数时，会触发断点异常。内核的异常处理机制会调用用户定义的pre_handler回调函数。

[单步执行]在pre_handler执行完成后，内核会继续执行sys_write函数。当函数执行完成后，内核会调用post_handler回调函数。

## Link
eBPF Links 是一种用于管理 eBPF 程序挂载的机制，它提供了一种更灵活和强大的接口，用于将 eBPF 程序绑定到内核钩子上。
主要功能包括：
- 持久化运行：通过将eBPF程序绑定到Links上，即使加载程序退出，程序仍然可以继续运行。
- 引用管理：方便跟踪对eBPF程序的引用，确保程序不会在加载程序意外退出时被卸载。
- 灵活性：Links提供了一种通用的接口，适用于多种类型的eBPF程序，包括 tracing、cgroup等

eBPF Links 与传统钩子的区别
- 传统钩子：直接将 eBPF 程序绑定到内核钩子上，如 kprobes、tracepoints 等。这种方式依赖于文件描述符或其他机制来保持程序的挂载状态。
- eBPF Links：引入了一个中间层（Link），eBPF 程序首先绑定到 Link 上，然后 Link 再绑定到内核钩子上。这种方式提供了更好的抽象和管理能力。

在内核中，eBPF Links 的实现主要通过 bpf_link 结构体来管理。以下是 eBPF Links 的实现和使用方式：
1. 创建 Link：通过 bpf_link_create 系统调用创建一个 Link，并将 eBPF 程序绑定到该 Link 上。
2. 挂载 Link：将创建的 Link 挂载到内核钩子上，例如通过 bpf_link_attach。
3. 固定 Link：可以将 Link 固定到 BPFFS 中，通过 bpf_link_pin，这样即使加载程序退出，Link 仍然会保持对 eBPF 程序的引用。
```c
struct bpf_link *link;

// 创建并挂载 eBPF 程序到 Link
link = bpf_program__attach(prog, ...);
if (!link) {
    fprintf(stderr, "Failed to attach program to link\n");
    return -1;
}

// 固定 Link 到 BPFFS
if (bpf_link__pin(link, "/sys/fs/bpf/my_link")) {
    fprintf(stderr, "Failed to pin link\n");
    return -1;
}
```


## Pinning
Pinning是一种机制，用于在BPF文件系统（BPFFS）中创建一个持久化的引用，指向某个eBPF对象（如程序、映射或链接）。通过Pinning，可以确保即使加载该对象的用户空间程序退出，对象仍然保留在内核中。

Pinning是通过`bpf(BPF_OBJ_PIN, ...)`系统调用完成的。这个调用会在BPFFS中创建一个路径（文件），指向目标eBPF对象。之后，可以通过`open()`系统调用打开这个路径，获取指向该对象的文件描述符。

```c
#include <bpf/libbpf.h>
#include <stdio.h>
#include <string.h>

int main() {
    struct bpf_object *obj;
    struct bpf_program *prog;
    const char *pin_path = "/sys/fs/bpf/my_pinned_program";

    // 打开并加载 BPF 对象文件
    obj = bpf_object__open("example.bpf.o");
    if (!obj) {
        fprintf(stderr, "Failed to open BPF object file\n");
        return -1;
    }

    if (bpf_object__load(obj)) {
        fprintf(stderr, "Failed to load BPF object\n");
        return -1;
    }

    // 获取 BPF 程序
    prog = bpf_object__find_program_by_name(obj, "example_prog");
    if (!prog) {
        fprintf(stderr, "Failed to find BPF program\n");
        return -1;
    }

    // Pin 程序到 BPFFS
    if (bpf_program__pin(prog, pin_path)) {
        fprintf(stderr, "Failed to pin BPF program to %s: %s\n", pin_path, strerror(errno));
        return -1;
    }

    printf("BPF program pinned successfully at %s\n", pin_path);
    return 0;
}
```
pin一个BPF链接：
```c
#include <bpf/libbpf.h>
#include <stdio.h>
#include <string.h>

int main() {
    struct bpf_object *obj;
    struct bpf_program *prog;
    struct bpf_link *link;
    const char *pin_path = "/sys/fs/bpf/my_pinned_link";

    // 打开并加载 BPF 对象文件
    obj = bpf_object__open("example.bpf.o");
    if (!obj) {
        fprintf(stderr, "Failed to open BPF object file\n");
        return -1;
    }

    if (bpf_object__load(obj)) {
        fprintf(stderr, "Failed to load BPF object\n");
        return -1;
    }

    // 获取 BPF 程序
    prog = bpf_object__find_program_by_name(obj, "example_prog");
    if (!prog) {
        fprintf(stderr, "Failed to find BPF program\n");
        return -1;
    }

    // 创建并挂载 Link
    link = bpf_program__attach(prog, ...);
    if (!link) {
        fprintf(stderr, "Failed to attach BPF program to link\n");
        return -1;
    }

    // Pin Link 到 BPFFS
    if (bpf_link__pin(link, pin_path)) {
        fprintf(stderr, "Failed to pin BPF link to %s: %s\n", pin_path, strerror(errno));
        return -1;
    }

    printf("BPF link pinned successfully at %s\n", pin_path);
    return 0;
}
```
Pinning的适用场景
1. 程序（Programs）：将BPF程序Pin到BPFFS，确保程序在加载程序退出后仍然可以运行。
2. 映射（Maps）：将BPF映射Pin到BPFFS，使得其他程序可以通过路径访问这些映射。
3. 链接（Links）：将BPF链接Pin到BPFFS，确保链接所绑定的程序在加载程序退出后仍然可以运行。

## 用eBPF跟踪系统调用
我们使用同一个BPF程序, 加载BPF的过程与上文类似, 区别在与attach的过程, 本例中需要通过perf机制来跟踪系统调用. 有关perf的部分只做简要介绍, 具体的可以看perf_event_open系统调用的手册。

```c
/*
    evt_attr: 描述要监视的事件的属性
    pid: 要监视的进程id, 设为-1的话表示监视所有进程
    cpu: 要监视的CPU
    group_fd: 事件组id, 暂时不用管
    flags: 相关表示, 暂时不用管
*/
static int perf_event_open(struct perf_event_attr *evt_attr, pid_t pid, int cpu, int group_fd, unsigned long flags)
{
    int ret;
    ret = syscall(__NR_perf_event_open, evt_attr, pid, cpu, group_fd, flags);
    return ret;
}
```
重点在于配置struct perf_event_attr, 主要成员如下：
```c
struct perf_event_attr { 
   __u32     type;         /* 事件类型 */
   __u32     size;         /* attribute结构的大小 */ 
   __u64     config;       /* 含义根据事件类型而定, 描述具体的事件配置 */
   union { 
       __u64 sample_period;    /* 取样时长 Period of sampling */
       __u64 sample_freq;      /* 取样频率 Frequency of sampling */ 
   };
   __u64     sample_type;  /* 取样种类 */ 

    ...;

   union { 
       __u32 wakeup_events;    /* 每n个事件唤醒一次 */
       __u32 wakeup_watermark; /* bytes before wakeup */ 
   };
};
```
本例中我们要测量的是跟踪点类型中, 进入execve这一事件, 因此可以把struct perf_event_attr的type设置为PERF_TYPE_TRACEPOINT, 表示跟踪点类型的事件. 此时config的值就表示具体要观测哪一个跟踪点, 这个值可以从debugfs中获取, 路径/sys/kernel/debug/tracing/events/<某一事件>/<某一跟踪点>/id中保存着具体的跟踪点的值. 如下:
```shell
sudo cat /sys/kernel/debug/tracing/events/syscalls/sys_enter_execve/id
```
因此如下设置就可以打开测量对应事件的efd:
```c
  //设置一个perf事件属性的对象
    struct perf_event_attr attr = {};
    attr.type = PERF_TYPE_TRACEPOINT;    //跟踪点类型
    attr.sample_type = PERF_SAMPLE_RAW;    //记录其他数据, 通常由跟踪点事件返回
    attr.sample_period = 1;    //每次事件发送都进行取样
    attr.wakeup_events = 1;    //每次取样都唤醒
    attr.config = 678;  // 观测进入execve的事件, 来自于: /sys/kernel/debug/tracing/events/syscalls/sys_enter_execve/id

    //开启一个事件观测, 跟踪所有进程, group_fd为-1表示不启用事件组
    int efd = perf_event_open(&attr, -1/*pid*/, 0/*cpu*/, -1/*group_fd*/, 0);
    if(efd<0){
        perror("perf event open error");
        exit(-1);
    }
    printf("efd: %d\n", efd);
```
接着通过ioctl()打开事件后, 再把BPF程序附着到此事件上就可在每次进入execve时触发BPF程序:
```c
    ioctl(efd, PERF_EVENT_IOC_RESET, 0);        //重置事件观测
    ioctl(efd, PERF_EVENT_IOC_ENABLE, 0);        //启动事件观测
    if(ioctl(efd, PERF_EVENT_IOC_SET_BPF, prog_fd)<0){    //把BPF程序附着到此事件上 
        perror("ioctl event set bpf error");
        exit(-1);
    }
```
整体代码如下, 加载BPF程序时要注意, 此时BPF程序的类型为BPF_PROG_TYPE_TRACEPOINT, 为追踪点类型的BPF程序:
```c
//gcc ./loader.c -o loader
#include <linux/bpf.h>
#include <stdio.h>
#include <sys/syscall.h>
#include <linux/perf_event.h>
#include <stdlib.h>
#include <stdint.h>
#include <errno.h>
#include <fcntl.h>
#include <arpa/inet.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <stdlib.h>

//类型转换, 减少warning, 也可以不要
#define ptr_to_u64(x) ((uint64_t)x)

//对于系统调用的包装, __NR_bpf就是bpf对应的系统调用号, 一切BPF相关操作都通过这个系统调用与内核交互
int bpf(enum bpf_cmd cmd, union bpf_attr *attr, unsigned int size)
{
    return syscall(__NR_bpf, cmd, attr, size);
}

//对于perf_event_open系统调用的包装, libc里面不提供, 要自己定义
static int perf_event_open(struct perf_event_attr *evt_attr, pid_t pid, int cpu, int group_fd, unsigned long flags)
{
    int ret;
    ret = syscall(__NR_perf_event_open, evt_attr, pid, cpu, group_fd, flags);
    return ret;
}


//用于保存BPF验证器的输出日志
#define LOG_BUF_SIZE 0x1000
char bpf_log_buf[LOG_BUF_SIZE];

//通过系统调用, 向内核加载一段BPF指令
int bpf_prog_load(enum bpf_prog_type type, const struct bpf_insn* insns, int insn_cnt, const char* license)
{
    union bpf_attr attr = {
        .prog_type = type,        //程序类型
        .insns = ptr_to_u64(insns),    //指向指令数组的指针
        .insn_cnt = insn_cnt,    //有多少条指令
        .license = ptr_to_u64(license),    //指向整数字符串的指针
        .log_buf = ptr_to_u64(bpf_log_buf),    //log输出缓冲区
        .log_size = LOG_BUF_SIZE,    //log缓冲区大小
        .log_level = 2,    //log等级
    };

    return bpf(BPF_PROG_LOAD, &attr, sizeof(attr));
}

//保存BPF程序
struct bpf_insn bpf_prog[0x100];

int main(int argc, char **argv){
    //先从文件中读入BPF指令
    int text_len = atoi(argv[2]);
    int file = open(argv[1], O_RDONLY);
    if(read(file, (void *)bpf_prog, text_len)<0){
        perror("read prog fail");
        exit(-1);
    }
    close(file);

    //把BPF程序加载进入内核, 注意这里程序类型一定要是BPF_PROG_TYPE_TRACEPOINT, 表示BPF程序用于内核中预定义的追踪点
    int prog_fd = bpf_prog_load(BPF_PROG_TYPE_TRACEPOINT, bpf_prog, text_len/sizeof(bpf_prog[0]), "GPL");
    printf("%s\n", bpf_log_buf);
    if(prog_fd<0){
        perror("BPF load prog");
        exit(-1);
    }
    printf("prog_fd: %d\n", prog_fd);

    //设置一个perf事件属性的对象
    struct perf_event_attr attr = {};
    attr.type = PERF_TYPE_TRACEPOINT;    //跟踪点类型
    attr.sample_type = PERF_SAMPLE_RAW;    //记录其他数据, 通常由跟踪点事件返回
    attr.sample_period = 1;    //每次事件发送都进行取样
    attr.wakeup_events = 1;    //每次取样都唤醒
    attr.config = 678;  // 观测进入execve的事件, 来自于: /sys/kernel/debug/tracing/events/syscalls/sys_enter_execve/id
 //开启一个事件观测, 跟踪所有进程, group_fd为-1表示不启用事件组
    int efd = perf_event_open(&attr, -1/*pid*/, 0/*cpu*/, -1/*group_fd*/, 0);
    if(efd<0){
        perror("perf event open error");
        exit(-1);
    }
    printf("efd: %d\n", efd);

    ioctl(efd, PERF_EVENT_IOC_RESET, 0);        //重置事件观测
    ioctl(efd, PERF_EVENT_IOC_ENABLE, 0);        //启动事件观测
    if(ioctl(efd, PERF_EVENT_IOC_SET_BPF, prog_fd)<0){    //把BPF程序附着到此事件上 
        perror("ioctl event set bpf error");
        exit(-1);
    }

    //程序不能立即退出, 不然BPF程序会被卸载
    getchar();

}
```

```c
sudo ./loader ./prog.text 64
sudo cat /sys/kernel/debug/tracing/trace_pipe
```

![eBPF和内核模块的对比](image-2.png)

