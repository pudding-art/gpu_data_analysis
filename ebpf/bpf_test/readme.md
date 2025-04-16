# 使用libbpf开发eBPF程序

libbpf是一个C语言库，伴随内核版本分发，用于辅助eBPF程序的加载和运行。它提供了用于与eBPF系统交互的一组C API，使开发者能够轻松地编写用户态程序来加载和管理eBPF程序。这些用户态程序通常用于分析、监控或优化系统性能。

![libbpf_ebpf](image.png)
参考自：https://zhuanlan.zhihu.com/p/596058784

生成eBPF程序字节码，字节码最终被内核中的「虚拟机」执行。 通过系统调用加载eBPF字节码到内核中，将eBPF程序attach到各个事件、函数。 创建map，用于在内核态与用户态进行数据交互。「事件」、TP点触发时，调用attach的eBPF字节码并执行其功能。

- syscall_count_kern.c为eBPF程序的C代码，使用clang编译为eBPF字节码
- syscall_count_user.cpp为用户态程序，用于调用libbpf加载eBPF字节码

字节码生成有多种方式：
1. 手动编写字节码（手写汇编指令），使用libbpf中的内存加载模式。
2. 编写c代码，由clang生成，使用libbpf解析elf文件获取相关字节码信息。
3. 一些其他工具能够解析脚本语言生成字节码（bpftrace）。

"vmlinux.h"是一个包含了完整的内核数据结构的头文件，是从vmlinux内核二进制中提取的。使用这个头文件，eBPF程序可以访问内核的数据结构，不用手动引入内核头文件。如果内核不支持生成该头文件，请手动引入所需要的内核头文件。


## libbpf例子
1. 【eBPF】使用libbpf开发eBPF程序
https://zhuanlan.zhihu.com/p/596058784
2. libbpf
https://github.com/libbpf/libbpf
3. libbpf https://docs.ebpf.io/ebpf-library/libbpf/
4. 