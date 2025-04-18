### strace跟踪helloworld


```shell
sudo strace -v -f ./hello.py
```
- `-f` 跟踪由fork(2),vfork(2) and clone(2)调用产生的子进程,跟踪多线程进程时有用
- `-v` 输出所有的系统调用，一些调用关于环境变量，状态，输入输出等调用，由于使用频繁默认不输出
- `-e EXPR`
	指定一个表达式，用来控制如何跟踪。格式如下: [qualifier=][!]value1[,value2]... 	qualifier 只能是 `trace, abbrev, verbose, raw, signal, read, write` 其中之一。value 是用来限定的符号或数字。默认的 qualifier 是 trace，感叹号是否定符号。例如：-e open 等价于 -e trace=open，表示只跟踪 open 调用。而 -etrace=!open 表示跟踪除了 open 以外的所有其他调用。有两个特殊的符号 all 和 none，分别表示跟踪所有和不跟踪任何系统调用。注意有些 Shell 使用 ! 来执行历史记录里的命令，所以要使用反斜杠对 ! 进行转义
    - `-e trace=file`
        只跟踪有关文件操作的系统调用
    - `-e trace=process` 
        只跟踪有关进程控制的系统调用
    - `-e trace=network` 
        跟踪与网络有关的所有系统调用
    - `-e trace=signal`
        跟踪所有与系统信号有关的系统调用 
    - `-e trace=ipc` 
        跟踪所有与进程通讯有关的系统调用
    - `-e trace=desc`
        跟踪所有与文件描述符相关的系统调用
    - `-e trace=memory`
        跟踪所有与内存映射相关的系统调用


-  `-o FILENAME`
	将 strace 的输出写入指定文件
- `-p PID`
	跟踪指定的进程
- -P PATH
	让strace只跟踪那些涉及这些路径的系统调用。多个-P选项可用于指定多个路径


忽略无关输出后，可以看到如下系统调用：
```shell
...
/* 1) 加载BPF程序 */
bpf(BPF_PROG_LOAD,...) = 4
...

/* 2）查询事件类型 */
openat(AT_FDCWD, "/sys/bus/event_source/devices/kprobe/type", O_RDONLY) = 5
read(5, "6\n", 4096)                    = 2
close(5)                                = 0
...

/* 3）创建性能监控事件 */
perf_event_open(
    {
        type=0x6 /* PERF_TYPE_??? */,
        size=PERF_ATTR_SIZE_VER7,
        ...
        wakeup_events=1,
        config1=0x7f275d195c50,
        ...
    },
    -1,
    0,
    -1,
    PERF_FLAG_FD_CLOEXEC) = 5

/* 4）绑定BPF到kprobe事件 */
ioctl(5, PERF_EVENT_IOC_SET_BPF, 4)     = 0
...
```

从输出中，你可以看出 BPF 与性能事件的绑定过程分为以下几步：
- 首先，借助 bpf 系统调用，加载 BPF 程序，并记住返回的文件描述符；
- 然后，查询kprobe类型的事件编号。BCC 实际上是通过 `/sys/bus/event_source/devices/kprobe/type`来查询的；
- 接着，调用 perf_event_open 创建性能监控事件。比如，事件类型（type 是上一步查询到的 6）、事件的参数（ config1 包含了内核函数 do_sys_openat2 ）等；
- 最后，再通过 ioctl 的 PERF_EVENT_IOC_SET_BPF 命令，将 BPF 程序绑定到性能监控事件。