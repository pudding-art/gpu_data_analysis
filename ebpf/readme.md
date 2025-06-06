# libbpf学习路线
## 系统调用

BPF之路一bpf系统调用（翻译的man bpf,可以看原文）
https://www.anquanke.com/post/id/263803

BPF之路二(e)BPF汇编
https://www.anquanke.com/post/id/263988

BPF之路三如何运行BPF程序
https://www.anquanke.com/post/id/265887

BPF之路四JIT源码分析（代码分析较多，可以考虑看Linux3.x版本的代码逻辑更清晰）
https://www.anquanke.com/post/id/266765

## libbpf例子
找一个能跑通的简单的例子。

eBPF学习记录（四）使用libbpf开发eBPF程序（需要修改才能运行）
https://blog.csdn.net/sinat_22338935/article/details/123318084

【eBPF】使用libbpf开发eBPF程序
https://zhuanlan.zhihu.com/p/596058784

可以将如下简单的监控vfs_mkdir函数的ebpf代码转换一下
https://blog.spoock.com/2023/08/14/eBPF-Helloworld/

## 获取/掌握/了解编写ebpf程序的范式
了解eBPF的运行原理，eBPF程序是如何与内核进行交互的（编程接口），各类eBPF程序的触发机制及其应用场景。

![bpf_internals](image-7.png)
图片来自 https://www.usenix.org/conference/lisa21/presentation/gregg-bpf


![paradigms](image-24.png)
## 看懂熟悉libbpf-bootstrap的一个例子

每个函数做了什么，获取数据源之后做了什么

bootstrap.c
- bootstrap_bpf__open()：数据处理
- bootstrap_bpf_load() 
- bootstrap_bpf_attach()：attach放在了哪里，放在这个位置应该如何触发，触发之后做了什么->handle_exec
- 构造通信机制,eg:ring_buffer,etc.
- ring_buffer__poll读缓冲区 
- bootstrap.bpf.c退出循环
- 注册函数handle_event

bootstrap.bpf.c
- 加载上下文的信息
- 更新信息
- bpf_ringbuf_submit()将数据放在**缓冲区**中（map）

## 将BCC工具翻译为libbpf
1. 分析BCC中实现各个部分的功能
2. 找到对应到libbpf中如何实现
3. 大部分的范式将接口改变一下即可，熟悉一下如何构造libbpf中的数据源，和BCC中数据比较差异，数据源/load和attach的方式/通信的方式不同，BCC使用python更多，libbpf使用C语言的库更多
4. 交互过程，交互算法提炼出来对应到libbpf中实现


## 参考
1. libbpf学习路径分享
https://www.bilibili.com/video/BV1xt421W7vp/?spm_id_from=333.1007.top_right_bar_window_history.content.click
2. eBPF Documentary
https://ebpf.io/zh-hans/what-is-ebpf/
3. eBPF介绍 https://coolshell.cn/articles/22320.html
4. libbpf-bootstrap https://github.com/libbpf/libbpf-bootstrap
5. https://man7.org/linux/man-pages/man2/bpf.2.html
6. Linux Socket Filtering aka Berkeley Packet Filter (BPF) https://www.kernel.org/doc/html/latest/networking/filter.html#networking-filter
7. Unofficial eBPF spec https://github.com/iovisor/bpf-docs/blob/master/eBPF.md
8. BPF internals https://www.usenix.org/conference/lisa21/presentation/gregg-bpf
9. eBPF - difference between loading, attaching, and linking? https://stackoverflow.com/questions/68278120/ebpf-difference-between-loading-attaching-and-linking
10. bpf_study https://github.com/pudding-art/bpf_study
11. How to get Linux ebpf assembly? https://stackoverflow.com/questions/39998050/how-to-get-linux-ebpf-assembly/40912405
12. ubpf https://github.com/iovisor/ubpf/
13. Linux内核eBPF虚拟机源码分析 https://bbs.kanxue.com/thread-267956.htm
14. 一文读懂eBPF|JIT实现原理 https://www.51cto.com/article/706101.html
15. 攻击网页浏览器:面向脚本代码块的ROP Gadget注入 https://www.sciengine.com/doi/pdf/61A042FEC85341FD84E0EE36AFC40D79
16. 尾调用优化 https://www.ruanyifeng.com/blog/2015/04/tail-call.html
17. eunomia-bpf https://github.com/eunomia-bpf
18. eBPF开发实践教程 https://eunomia.dev/zh/tutorials/SUMMARY/
19. eunomia https://eunomia.dev/
