//gcc ./bpf.c -o bpf
#include <stdio.h>
#include <stdlib.h>  //为了exit()函数
#include <stdint.h>    //为了uint64_t等标准类型的定义
#include <errno.h>    //为了错误处理
#include <linux/bpf.h>    //位于/usr/include/linux/bpf.h, 包含BPF系统调用的一些常量, 以及一些结构体的定义
#include <sys/syscall.h>    //为了syscall()

//类型转换, 减少warning, 也可以不要
#define ptr_to_u64(x) ((uint64_t)x)

//对于系统调用的包装, __NR_bpf就是bpf对应的系统调用号, 一切BPF相关操作都通过这个系统调用与内核交互
int bpf(enum bpf_cmd cmd, union bpf_attr *attr, unsigned int size)
{
    return syscall(__NR_bpf, cmd, attr, size);
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

//BPF程序就是一个bpf_insn数组, 一个struct bpf_insn代表一条bpf指令
struct bpf_insn bpf_prog[] = {
    { 0xb7, 0, 0, 0, 0x2 }, //初始化一个struct bpf_insn, 指令含义: mov r0, 0x2;
    { 0x95, 0, 0, 0, 0x0 }, //初始化一个struct bpf_insn, 指令含义: exit;
};

int main(void){
    //加载一个bpf程序
    int prog_fd = bpf_prog_load(BPF_PROG_TYPE_SOCKET_FILTER, bpf_prog, sizeof(bpf_prog)/sizeof(bpf_prog[0]), "GPL");
    if(prog_fd<0){
        perror("BPF load prog");
        exit(-1);
    }
    printf("prog_fd: %d\n", prog_fd);
    printf("%s\n", bpf_log_buf);    //输出程序日志
}