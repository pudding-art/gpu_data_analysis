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

//创建一个映射, 参数含义: 映射类型, key所占自己, value所占字节, 最多多少个映射
int bpf_create_map(enum bpf_map_type map_type, unsigned int key_size, unsigned int value_size, unsigned int max_entries)
{
    union bpf_attr attr = {    //设置attr指向的对象
        .map_type = map_type,
        .key_size = key_size,
        .value_size = value_size,
        .max_entries = max_entries
    };

    return bpf(BPF_MAP_CREATE, &attr, sizeof(attr)); //进行系统调用
}

//在映射中更新一个键值对
int bpf_update_elem(int fd, const void* key, const void* value, uint64_t flags)
{
    union bpf_attr attr = {
        .map_fd = fd,
        .key = ptr_to_u64(key),
        .value = ptr_to_u64(value),
        .flags = flags,
    };

    return bpf(BPF_MAP_UPDATE_ELEM, &attr, sizeof(attr));
}

//在映射中根据指针key指向的值搜索对应的值, 把值写入到value指向的内存中
int bpf_lookup_elem(int fd, const void* key, void* value)
{
    union bpf_attr attr = {
        .map_fd = fd,
        .key = ptr_to_u64(key),
        .value = ptr_to_u64(value),
    };

    return bpf(BPF_MAP_LOOKUP_ELEM, &attr, sizeof(attr));
}

int main(void){
    //首先创建一个数组映射, 键和值都是4字节类型, 最多0x100个映射
    int map_fd = bpf_create_map(BPF_MAP_TYPE_ARRAY, 4, 4, 0x100);
    printf("BPF_map_fd: %d\n", map_fd);

    //按照key->key+1的规律填充这个数组映射
    for(int idx=0; idx<0x20; idx+=1){
        int value = idx+1;
        //记住, 数组映射中的元素预先分配, 已经存在, 不可删除, 因此flag要么是BPF_ANY, 要么是BPF_EXISTS, 表示更新一个已有的值
        if(bpf_update_elem(map_fd, &idx, &value, BPF_EXIST)<0){ 
            perror("BPF update error");
            exit(-1);
        }
    }

    //读入key
    int key;
    scanf("%d", &key);

    //尝试在数组映射中查找对应的值
    int value;
    if(bpf_lookup_elem(map_fd, &key, &value)<0){
        perror("BPF lookup error");
        exit(-1);
    }
    printf("key: %d => value: %d\n", key, value);

}