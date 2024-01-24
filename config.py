import sys

download_folder = "files"
solution_folder = "solutions"
url = "https://inf-ege.sdamgia.ru/test?id=14912698&nt=True&pub=False"  # Задачи

answers = "answers.html"    # Файл с таблицей правильных ответов
timeout = 10                # Макс время на выполнение задач


def is_debug(): return "checker" not in sys.argv


def debug_print(*messages: str, sep=" ", end="\n"):
    if is_debug(): print("[\033[33m⚠\033[0m]\033[37m " + sep.join(map(str, messages)) + "\033[0m", end=end)



