import time
from rich.progress import track
def main():
    from rich import print

    # 1. 带颜色和样式的文本
    print("Hello, [bold magenta]World[/bold magenta]!", ":snake:")

    # 2. 组合样式
    print("[bold red on white]这是白色背景的粗体红字[/bold red on white]")
    print("[underline]这段文字有下划线[/underline]")
    print("[blink]这段文字会闪烁[/blink]")

    # 3. 自动美化输出数据结构
    my_list = ["foo", "bar", {"baz": "qux"}]
    my_dict = {
        "name": "Gemini",
        "features": ["NLP", "Code Generation", "Multilingual"],
        "version": 1.5
    }

    print("\n--- 美化输出列表 ---")
    print(my_list)

    print("\n--- 美化输出字典 ---")
    print(my_dict)

    from rich.console import Console
    from rich.syntax import Syntax

    console = Console()

    my_code = """
    def factorial(n):
        \"\"\"Calculates the factorial of a number.\"\"\"
        if n == 0:
            return 1
        else:
            return n * factorial(n - 1)

    # Calculate factorial of 5
    result = factorial(5)
    print(f"The factorial of 5 is {result}")
    """

    # 创建一个 Syntax 对象
    # 参数：代码字符串，语言名称，主题，是否显示行号
    syntax = Syntax(my_code, "python", theme="solarized-dark", line_numbers=True)

    # 打印
    console.print(syntax)

    from rich.console import Console
    from rich.table import Table

    console = Console()

    # 创建一个表格实例
    table = Table(title="电影排行榜 Top 3", show_header=True, header_style="bold magenta")

    # 添加列
    table.add_column("排名", style="dim", width=12)
    table.add_column("电影名称")
    table.add_column("年份", justify="right")  # justify 控制对齐方式
    table.add_column("票房（美元）", justify="right")

    # 添加行
    table.add_row("1", "阿凡达", "2009", "$2,923,706,026")
    table.add_row("2", "复仇者联盟4：终局之战", "2019", "$2,797,501,328")
    table.add_row("3", "阿凡达：水之道", "2022", "$2,320,250,281")

    # 打印表格
    console.print(table)

    from rich.console import Console
    from rich.markdown import Markdown

    # 1. 创建一个 Console 对象
    console = Console()

    # 2. 你的 Markdown 文本
    markdown_text = """
    # 这是一个一级标题

    这是普通段落，包含一些 **粗体** 和 *斜体* 文本。

    ## 这是一个二级标题

    * 列表项目 1
    * 列表项目 2
        * 嵌套列表项目

    > 这是一个引用块。

    ---

    `代码片段`
    """

    # 3. 创建一个 Markdown 可渲染对象
    md = Markdown(markdown_text)

    # 4. 使用 console.print() 来打印它，这才会进行渲染
    console.print(md)


if __name__ == "__main__":
    main()
