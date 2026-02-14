import PyInstaller.__main__
import os
import shutil
import sys


def clean_build():
    """清理之前的构建文件"""
    dirs_to_remove = ['build', 'dist']
    for dir_name in dirs_to_remove:
        if os.path.exists(dir_name):
            shutil.rmtree(dir_name)

    files_to_remove = ['BookingSystem.spec']
    for file_name in files_to_remove:
        if os.path.exists(file_name):
            os.remove(file_name)


def build_exe():
    """打包成exe"""

    # 确定分隔符
    sep = ';' if sys.platform.startswith('win') else ':'

    # PyInstaller参数
    args = [
        'main.py',  # 主程序文件
        '--name=BookingSystem',  # 输出文件名
        '--onefile',  # 打包成单个exe
        '--windowed',  # 无控制台窗口（去掉可显示控制台调试）
        f'--add-data=templates{sep}templates',  # 添加HTML模板
        '--add-data=booking_automation.log;.',  # 添加日志文件
        '--hidden-import=selenium',
        '--hidden-import=flask',
        '--hidden-import=flask_cors',
        '--hidden-import=webdriver_manager',
        '--hidden-import=threading',
        '--hidden-import=logging',
        '--collect-all=selenium',
        '--collect-all=webdriver_manager',
        '--clean',
        '--noconfirm'
    ]

    # 如果有图标文件，可以添加
    if os.path.exists('icon.ico'):
        args.append('--icon=icon.ico')

    # 执行打包
    print("开始打包...")
    PyInstaller.__main__.run(args)
    print("打包完成！")


if __name__ == '__main__':
    clean_build()
    build_exe()