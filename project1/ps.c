#include <stdio.h>
#include <dirent.h>
#include <ctype.h>
#include <string.h>
#include <assert.h>

int main(void)
{
    /* TODO */
    DIR *dir_pointer; //定义DIR指针用于接受打开的路径
    char proc_path[]="/proc"; //要打开的路径名
    dir_pointer = opendir(proc_path); //打开路径
    if(!dir_pointer){  //如果打开失败的错误判断
        printf("ERROR: fail to open `/proc` directory!\n");
        return -1;
    }

    /*** readdir ***/
    struct dirent * filename;
    
    // 输出标题
    printf("%5s %c %s\n","PID", 'S', "CMD");

    while ((filename = readdir(dir_pointer)))
    {
        if(filename->d_name[0]<'0' || filename->d_name[0]>'9'||strlen(filename->d_name)>6) // 跳过不是进程的文件
            continue;
        // filename->d_name is pid

        // 计算进程目录的路径
        char subdir_path[15] = "";
        strcpy(subdir_path, proc_path);
        strcat(subdir_path, "/");
        strcat(subdir_path, filename->d_name);

        // 定义字符串，保存需要展示的变量
        char cmd[10000]=""; // command line
        char state = 'S';  // state
        char name[1000]=""; //process name

        // 读取每个进程对应的信息
        DIR *subdir_pointer = opendir(subdir_path);
        struct dirent *proc_info;
        while((proc_info = readdir(subdir_pointer)))
        {
            if(!strcmp(proc_info->d_name, "cmdline") ) // 读取命令行
            {   
                char cmd_path[25];
                strcpy(cmd_path, subdir_path);
                strcat(cmd_path,"/");
                strcat(cmd_path, proc_info->d_name);

                FILE *cmd_fp = fopen(cmd_path, "r"); // 创建文件指针及打开文本文件
                
                if (cmd_fp == NULL)
                {
                    printf("ERROR: fail to open %s", proc_info->d_name);
                    return 0;
                }

                //cmdline文件不换行地存了多个字符串，需要按字符读取
                char ch;
                int idx=0;
                while((ch=fgetc(cmd_fp))!=EOF)
                {
                    if (ch=='\0')
                        ch = ' ';
                    cmd[idx] = ch;
                    idx++;
                }
                cmd[--idx] = '\0';

                fclose(cmd_fp); // 关闭文件指针
            } 
            else if (!strcmp(proc_info->d_name, "status")) // 读取状态
            {
                
                char status_path[25];
                strcpy(status_path, subdir_path);
                strcat(status_path,"/");
                strcat(status_path, proc_info->d_name);

                FILE *status_fp = fopen(status_path, "r"); // 创建文件指针及打开文本文件
                
                if (status_fp == NULL)
                {
                    printf("ERROR: fail to open %s", proc_info->d_name);
                    return 0;
                }
                
                char status_buffer[1000];
                while(fgets(status_buffer, 1000, status_fp) != NULL){
                    // store state
                    if(status_buffer[0]=='S' && status_buffer[1]=='t' && status_buffer[2]=='a' && status_buffer[3]=='t'&& status_buffer[4]=='e')
                    {       
                        state = status_buffer[7];
                        break; // 一定先读取name再读取state，读取完state说明这个status已经读完了
                    }

                    // store name
                    if(status_buffer[0]=='N' && status_buffer[1]=='a' && status_buffer[2]=='m' && status_buffer[3]=='e')
                    {
                        strncpy(name, status_buffer+6, strlen(status_buffer)-7); //去掉前7个和最后的换行符
                    }
                }
                
                // printf("%d\n", line_num);

                fclose(status_fp); // 关闭文件指针

            }

        }

        if(strlen(cmd)!=0)
            printf("%5s %c %s\n", filename->d_name, state, cmd);
        else  
            printf("%5s %c [%s]\n", filename->d_name, state, name); 
        


        // printf("%d\n", filename->d_type);
        // printf("filename:%-10s\td_type:%d\t d_reclen:%us\n",
        // filename->d_name,filename->d_type,filename->d_reclen);
    }

    return 0;
}