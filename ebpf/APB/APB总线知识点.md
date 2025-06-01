![image-20240319175059886](/Users/hong/Library/Application%20Support/typora-user-images/image-20240319175059886.png)

## IWAG

验证一个模块主要分为3个方面：

设计文档的理解（**模块功能**——应用层功能+模块结构+模块功能点；时序分析——总线协议时序分析+模块时序分析+接口信号分析；**寄存器相关配置**——寄存器列表+寄存器功能配置）；验证平台的搭建；模块级验证结果

### 模块功能概述

#### 模块应用层功能

> 查阅设计文档或b站、csdn网站、知乎了解该模块的具体应用层功能，对功能进行简述。随着验证过程的不断推进更加全面的了解模块应用层功能（针对具体问题理解）。

检测并解决由**软件错误**导致的故障；当计数器达到给定的超时值时触发一个中断（仅适用于窗口型看门狗）或产生系统复位。

独立看门狗由其**专用低速时钟（LSI）**驱动，因此即便在主时钟发生故障时仍然保持工作状态。窗口看门狗（WWDG）时钟由APB1时钟经预分频后提供，通过可配置的时间窗口来检测应用程序非正常的过迟或过早操作。

IWDG最适合那些需要看门狗作为一个在主程序之外，能够完全独立工作，并对时间要求比较低的场合。WWDG最适合那些要求看门狗在精确计时窗口作用的应用程序。独立看门狗最长差不多可以超时30s左右，可供选择的范围很大。

看门狗的几个特点：

- 时钟独立不依赖其他；
- 时钟来自LSI，精度不会很高，故而可推断IWDG应用于对时间精度要求比较低的场合；
- 还需要关注的就是寄存器如何配置；

看门狗功能：

- 任何时候启动独立看门狗时，看门狗会从0xFFF开始向下计数，直至减到0x000时产生复位。如何避免复位？不断给看门狗赋值（喂狗），只要不断喂狗程序就不会出现问题，但是一旦超过了最大喂狗时间，程序就会复位；
- 时间的设置，前面说过看门狗对时间的要求不高，但是这个不高应该如何理解？实际上就是最大时间的设置，大概估算一下**从程序开始执行看门狗到需要设定喂狗的地方大概需要多少时间**，然后设置相对长一点的时间，如果在该时间内，程序没有执行到该处，就会触发看门狗；

> RTC：Real-time Clock

#### 看门狗的具体实现

IWDG一个需要注意的地方就是关于寄存器有访问保护，首先需要对寄存器写入一定的值之后才能取消访问保护，然后才可以进行相应的寄存器设置。

重点3个寄存器：

- KR 	关键字寄存器
- PR         预分频寄存器
- RLR       重载寄存器

KR：必须每隔一段时间便通过软件对这些位写入键值AAAAh，否则当计数器计数到0时，看门狗会产生复位；写入键值5555h可使能对IWDG_PR和IWDG_RLR寄存器的访问；写入键值CCCCh可启动看门狗；

PR：通过设定分频从而设置时间，还有ST官方手册里面有个表，可以查你大概需要多少时间，然后设置就OK；

RLR：每次喂狗后需要赋值，这个值就来自这里，reload重装载值然后从装载的值开始向下计数直到下一次喂狗；

通过总线端的数据传输完成对IWDG的寄存器进行功能配置，右侧为IWDG本身的接口；IWDG为一个32bit递减计数器，由RL寄存器初始化，递减到0000时，输出端WDOGINT拉高，输出终端信号；当WDOGCLKEN信号为高时，计数器会在每个WDOGCLK的上升沿-1，计数到0时，若此时WDOGCONCROL寄存器部分的INT域与RES域为高则使能reset和interrupt功能，输出中断信号并且IWDG会按照RLR中预定值进行重置，若WDOGCONTROL域中有未使能的情况则会等待重置或无法输出中断。

![图1.1 apb_watchdog接口](https://img-blog.csdnimg.cn/6461bd1e809b439e81d07b48b18fdb69.png#pic_center)

https://zhuanlan.zhihu.com/p/66702            

### 测试平台环境搭建

利用gvim可以创建与打开文件如下：

- verilog文件夹中存放设计代码;
- uvm文件夹中存放验证代码与其环境结构;
- cfg为配置文件，由顶层basetest创建，其中包括一些**配置信息**，也可**将interface，regmodel打包传入**
- env为验证环境部分，主体为pkg，**env与virtual sequencer**
- **reg为寄存器模型**
- seq_lib为存放测试用例sequence文件夹
- sim为仿真文件夹
- tb为testbench与interface文件夹
- test用以存放不同测试文件
- vip_lib中存放了apb2总线的vip
- 在创建模板时，除vip部分其他基本为空

<img src="/Users/hong/Library/Application%20Support/typora-user-images/image-20240320224653735.png" alt="image-20240320224653735" style="zoom:20%;" />



原文链接：https://blog.csdn.net/peop1e/article/details/124585217

### 当前验证结构

![在这里插入图片描述](https://img-blog.csdnimg.cn/f9179b2b72474633b171c7270c41b759.png#pic_center)

##### 完成APB总线侧的激励发送

- 直接访问方式：调用VIP中的APB测试序列对总线进行访问以完成寄存器的配置;
- register model: 在验证环境中创建一个寄存器模型，通过adapter将其与总线连接起来，用户可以通过register model来配置硬件寄存器的值；

##### APB直接访问

直接在对应的seq中调用apb_seq, 从`watchdog_base_virtual_sequence`类中派生直接APB直接访问的seq，挂载到env中与apb_mst_sequencer连接好的sequencer上，进行激励的发送。需要创建对应的seq与test文件，并将它们加入seq_lib与test_lib的编译文件中。

对于APB直接访问，可以直接读取部分寄存器reset之后的数据，应该都是0；

```systemverilog
 `uvm_do_on_with(apb_rd_seq,p_sequencer.apb_mst_sqr,{addr=='hFE0;})
    rd_val = apb_rd_seq.data;
    void'(this.diff_value( rd_val , 'h24));
```

driver中的声明：

```systemverilog
task apb_master_driver::do_read(apb_transfer t);
  `uvm_info(get_type_name(), "do_write ...", UVM_HIGH)
  @(vif.cb_mst);
  vif.cb_mst.paddr <= t.addr;
  vif.cb_mst.pwrite <= 0;
  vif.cb_mst.psel <= 1;
  vif.cb_mst.penable <= 0;
  @(vif.cb_mst);
  vif.cb_mst.penable <= 1;
  #100ps;
  t.data = vif.prdata;
  repeat(t.idle_cycles) this.do_idle();
endtask: do_read
```

> [!IMPORTANT]
>
> 但是考虑到日后可能访问watchdog一侧的信号要求，也可以将watchdog的interface传递于env中，这里将interface，registermodel，还有一些仿真记录信号一并传递于cfg中，将它们打包，便于创建与configdb配置。

##### 寄存器直接访问

寄存器模型的生成来源于python脚本与csv文件

##### uvm_do_on_with

还有一个，主要是完成transaction的生成，其中数据变量的随机化，然后是将激励发送给driver。

- uvm_do_with和uvm_do_on_with的区别是啥？



##### m_sequencer和p_sequencer之间的区别

p_sequencer对应的类是实际对应的sequencer，即用户自定义的sequencer的名字
m_sequencer对应的类是ovm_sequencer。因此，用法上也有所区别：用p_sequencer，你可以直接访问自定义的sequencer的property或method，而用m_sequencer不能。

**将watchdog sequencer注册为p_sequencer，这一步的目的与uvm中激励发送的driver, sequence和sequencer之间的关系有关。sequence在被挂载至sequencer上时会将当前sqr传递给底层的m_sequencer，由m_sequencer完成driver与sequence之间的桥梁工作，在激励发送时会检查m_sequencer和p_sequencer的指向是否相同，以此保证激励发送符合使用者的理解。**

更细的没看懂，不知道怎么理解。



#### 寄存器模型生成方法

https://www.cnblogs.com/lanlancky/p/17072564.html

自动生成UVM寄存器模型：

验证工程师搭建寄存器模型既可以手写，也可以利用脚本转化实现，但是手写寄存器模型可能出现潜在错误，寄存器越多存在的风险越大，会影响后期验证平台的调试。使用**寄存器模型生成脚本一**方面可以减少错误，一方面可以加快平台搭建速度。以下为寄存器模型自动生成的方法。

1. 根据寄存器文档信息填写your_reg寄存器描述文件，以csv格式保存在桌面； ![image-20240321011229389](/Users/hong/Library/Application%20Support/typora-user-images/image-20240321011229389.png)

| REGISTER | address | reg_access | field     | field_access | reset_value | bitpos_end | bits_start | function       |
| -------- | ------- | ---------- | --------- | ------------ | ----------- | ---------- | ---------- | -------------- |
| IWDG_KR  | 0x00    | W          | OP_ACCESS | W            | 0x0000      | 15         | 0          | OP_TYPE        |
| IWDG_PR  | 0x04    | RW         | PRE_FRE   | RW           | 0x0000      | 2          | 0          | PRE_FRE        |
| IWDG_RLR | 0x08    | RW         | RELOAD    | RW           | 0x0000      | 11         | 0          | RELOAD_NUM     |
| IWDG_SR  | 0x0C    | R          | PVU       | R            | 0x0000      | 0          | 0          | PRE_UPDATED    |
|          |         |            | RVU       | R            | 0x0000      | 1          | 1          | RELOAD_UPDATED |

每个reg的reserved字段最好也写出来

2. 修改python脚本

   生成的ralf文件类型类似json文件格式；已经下载了可用的脚本文件，将其中的your_rgm改成自己的寄存器名称即可；

3. 生成寄存器模型**(后面再去理解寄存器模型生成脚本)**

​	最后是生成一个reg的sv文件；

https://blog.csdn.net/qq_42873953/article/details/131365678

https://blog.csdn.net/m0_64319399/article/details/136738094这个脚本有些问题

#### 寄存器模型前门访问

register model引入环境与cfg类似，也是由test传递至env层次中，需要考虑的是如何在对应的seq中调用register model(rgm), 这里采用的方法是将rgm传递给sequencer，在sequence挂载到sequencer之后，seq可以在body中拿到对应sequencer下的rgm, 从而在sequence中实现寄存器模型的访问。

（保证sequence在sequencer中访问到rgm）

```systemverilog
//1. 将test层面的rgm传递到env中-> test.sv
function new (string name = "rkv_watchdog_base_test", uvm_component parent);
    super.new(name, parent);
  rgm = rkv_watchdog_rgm::type_id::create("rgm", this); //创建register model
    rgm.build();
  endfunction

  function void build_phase(uvm_phase phase);
    super.build_phase(phase);
    cfg = rkv_watchdog_config::type_id::create("cfg"); 
    uvm_config_db#(rkv_watchdog_config)::set(this,"env","cfg",cfg);
    uvm_config_db#(rkv_watchdog_rgm)::set(this,"env","rgm",rgm);//将register model传递给env
    env = rkv_watchdog_env::type_id::create("env", this);
  endfunction
//2. 实现了rgm的配置并传递于下级->env.sv
//实现了predictor与adapter的声明，predictor为uvm提供的explicit predictor，只需声明例化即可使用，同时对adapter和predictor进行连接，是其能够在rgm中发挥作用
if(!uvm_config_db#(rkv_watchdog_rgm)::get(this, "", "rgm",rgm)) begin
      rgm = rkv_watchdog_rgm::type_id::create("rgm", this);
      rgm.build();
    end
    uvm_config_db#(rkv_watchdog_rgm)::set(this,"*","rgm", rgm);
//3. sequencer层次代码，rgm从test一路传递到sequencer中，在base_sequence中也能够拿到对应的rgm
if(!uvm_config_db#(rkv_watchdog_rgm)::get(this, "", "rgm",rgm)) begin
      `uvm_fatal("GTCFG","cannot get rgm from confgdb")
    end
//4. sequence中可以访问到rgm
 virtual task body();
    // get cfg from p_sequencer
    cfg = p_sequencer.cfg;
    // get rgm from p_sequencer
    rgm = cfg.rgm;
    vif = cfg.vif;
    `uvm_info("body", "Entered...", UVM_LOW)
    // TODO in sub-class
    `uvm_info("body", "Exiting...", UVM_LOW)
  endtask
```

想要通过寄存器模型完成与总线、硬件寄存器之间的交流，predictor和adapter是不可或缺的，前者这env环境中自动生成（代码在env中），后者需要手动添加至环境中。

```systemverilog
uvm_reg_predictor #(apb_transfer) predictor;
predictor = uvm_reg_predictor#(apb_transfer)::type_id::create("predictor", this);
apb_mst.monitor.item_collected_port.connect(predictor.bus_in);
```

adapter主要是定义了reg2bus和bus2reg的function;

然后就可以通过继承base sequence创建可以读写reg model的sequence。

> [!CAUTION]
>
> 与直接访问相比，寄存器模型访问的方式将硬件寄存器通过软件的方式进行了封装，不再需要查询每个寄存器的地址来进行配置。同时，也可以针对某个寄存器的域来进行配置，增加了配置的灵活程度。
>
> ![在这里插入图片描述](https://img-blog.csdnimg.cn/20210306213442589.png?x-oss-process=image/watermark,type_ZmFuZ3poZW5naGVpdGk,shadow_10,text_aHR0cHM6Ly9ibG9nLmNzZG4ubmV0L3FxXzM5Nzk0MDYy,size_16,color_FFFFFF,t_70)
>
> ![在这里插入图片描述](https://img-blog.csdnimg.cn/20210307164231922.png)



## APB_SRAM

![image-20240319200243966](/Users/hong/Library/Application%20Support/typora-user-images/image-20240319200243966.png)



















