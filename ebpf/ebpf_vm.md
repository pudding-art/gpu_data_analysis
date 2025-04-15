# eBPF虚拟机
verifier:eBPF的验证器，实现了一个本模块下的CFI/CFG(完整控制流)机制。

jit:Just-In-Time,即时编译，eBPF汇编会在内核中被规则替换成真正的x86_64指令。

所有的eBPF汇编指令在内核中定义为一个struct bpf_insn，使用时一般将连续的指令放置成一个结构体数组，然后通过内核态的bpf_prog_load载入编译运行。而内核态的程序对应struct bpf_prog结构体。bpf_prog_load函数主要执行以下关键操作：单bpf函数调用`bpf_prog_select_runtime(prog,&err)`jit编译prog,多bpf函数的prog调用`jit_subprog`。两者都会统一到针对`do_jit`的调用。
