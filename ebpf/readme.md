## 系统调用

BPF之路一bpf系统调用
https://www.anquanke.com/post/id/263803

BPF之路二(e)BPF汇编
https://www.anquanke.com/post/id/263988

BPF之路三如何运行BPF程序
https://www.anquanke.com/post/id/265887

BPF之路四JIT源码分析
https://www.anquanke.com/post/id/266765

## libbpf例子
找一个能跑通的简单的例子

【eBPF】使用libbpf开发eBPF程序
https://zhuanlan.zhihu.com/p/596058784

## 获取/掌握/了解编写ebpf程序的范式

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
libbpf学习路径分享
https://www.bilibili.com/video/BV1xt421W7vp/?spm_id_from=333.1007.top_right_bar_window_history.content.click