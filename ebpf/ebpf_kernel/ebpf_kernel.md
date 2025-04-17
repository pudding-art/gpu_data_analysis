# 使用eBPF跟踪内核状态

bpftrace

跟踪类eBPF程序主要包括内核插桩`BPF_PROG_TYPE_KPROBE`、跟踪点`BPF_PROG_TYPE_TRACEPOINT`以及性能事件`BPF_PROG_TYPE_PERF_EVENT`等程序类型，而每类eBPF程序又可以挂载到不同的内核函数、内核跟踪点或性能事件上。当这些内核函数、内核跟踪点或性能事件被调用的时候，挂载到其上的eBPF程序就会自动执行。

> 我不知道内核中都有哪些内核函数、内核跟踪点或性能事件的时候，可以在哪里查询到它们的列表呢？对于内核函数和内核跟踪点，在需要跟踪它们的传入参数和返回值的时候，又该如何查询这些数据结构的定义格式呢？


## 查询内核跟踪点
为了方便调试，内核将**所有函数以及非栈变量的地址**都抽取到了`/proc/kallsyms`中，这样调试器就可以根据地址找出对应的函数和变量。当调试器（如 gdb 等调试工具）需要知道某个内核函数或者非栈变量的地址时，就可以通过查询这个 “地址簿” 来获取。假设内核中有一个名为`sys_write`的函数，它用于处理写操作的系统调用。在内核编译完成后，这个函数会被加载到内存中的某个地址，比如 0xc1000000（这个地址是假设的，实际地址会根据内核的加载情况等因素而变化）。同时，内核中有一个全局变量`task_struct`，它用于描述一个进程的结构，这个变量被分配在内存地址 0xc2000000 处（同样也是假设的地址）。这些函数和变量的地址信息会被记录在`/proc/kallsyms`文件中。当开发人员使用调试器进行内核调试时，例如在调试一个与写操作相关的内核问题时，他们可以使用调试器的命令来查看/proc/kallsyms 文件，找到`sys_write`函数的地址 0xc1000000。然后，调试器可以根据这个地址来定位到`sys_write`函数的代码位置，查看函数的执行流程、参数传递等信息，从而帮助开发人员分析和解决内核中的问题。对于`task_struct`变量也是如此，通过其在`/proc/kallsyms`中的地址，可以方便地查看和修改这个变量的值，以用于调试目的。

![kallsyms](image.png)
```shell
# 变量地址/函数入口地址 符号类型 符号名称
c1000000 T sys_write
c1000100 T sys_read
c2000000 D task_struct
c2000100 R kernel_version
```
符号类型：T代表是函数/代码地址，D代表是一个已经初始化的全局变量，R代表一个只读变量。
如果内核崩溃日志中提到地址0xc1000000,调试器可以通过/proc/kallsyms确定这是sys_write函数的地址;也可以通过该文件分析内核的内存布局，了解内核函数和变量的分布情况。很显然，具有实际含义的名称要比16进制的地址易读得多。对内核插桩类的eBPF程序来说，它们要挂载的内核函数就可以从/proc/kallsyms这个文件中查到。

注意，内核函数是一个非稳定API，在新版本中可能会发生变化，并且内核函数的数量也在不断增长中。
![wc](image-1.png)
这些符号表不仅包括了内核函数，还包含了非栈数据变量。而且并不是所有内核函数都是可跟踪的，只有显式导出的内核函数才可以被eBPF进行动态跟踪。因而，通常我们并不直接从内核符号表查询可跟踪点。


为了方便内核开发者获取所需的跟踪点信息，内核调试文件系统DebugFS还向用户空间提供了内核调试所需的基本信息，如内核符号列表、跟踪点、函数跟踪ftrace状态以及参数格式等。
![debugfs](image-2.png)
```shell
sudo cat /sys/kernel/debug/tracing/events/syscalls/sys_enter_execve/format # 查询execve系统调用的参数格式
```
![execve](image-3.png)
如果遇到/sys/kernel/debug目录不存在的错误，说明你的系统没有自动挂载调试文件系统。只需要执行下面的mount命令即可挂载：
```shell
sudo mount -t debugfs debugfs /sys/kernel/debug
```
注意，eBPF程序的执行也依赖于DebugFS。如果你的系统没有自动挂载它，那么我推荐你把它加入到系统开机启动脚本里面，这样机器重启后eBPF程序也可以正常运行。

可以从/sys/kernel/debug/tracing中找到所有内核预定义的跟踪点，进而可以在需要时把eBPF程序挂载到对应的跟踪点。

## 查询性能事件
可以使用perf来查询性能事件，可以不带参数查询所有性能事件也可以加入可选的事件类型参数进行过滤：
```shell
sudo perf list [hw|sw|cache|tracepoint|pmu|sdt|metric|metricgroup]
```

## 参考文献
1. 内核跟踪 https://time.geekbang.org/column/article/484207
2. DebugFS https://www.kernel.org/doc/html/latest/filesystems/debugfs.html