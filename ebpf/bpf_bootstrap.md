# 看懂熟悉libbpf-bootstrap的一个例子

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


