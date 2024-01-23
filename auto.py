import os
import re
import textwrap

import requests
import mimetypes
from bs4 import BeautifulSoup

from config import *

headers = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/51.0.2704.103 "
                  "Safari/537.36 "
}


def sensible_text(nonsense_text: str):
    return re.sub(r'[^a-zA-Zа-яА-Я0-9ёЁ.\-+=?!/\\ ]', '', nonsense_text)


def number_case(number):
    if not (10 <= number <= 20):
        if 2 <= number % 10 <= 4:
            return 'а'
        if number % 10 == 1: return ''
    return 'ов'


def create_solution_file(filedir, task_number, description, attachments):
    filename = "Задача номер " + str(task_number) + (".py", ".txt")[input(" - ❔ Простой ответ? (y/n) ").lower() == "y"]
    filepath = os.path.join(solution_folder, filename)

    wrapper = textwrap.TextWrapper(width=120)

    if not os.path.exists(filedir): os.mkdir(solution_folder)
    if (filename in os.listdir(filedir)) and (input("Заменить файл? (y/n) ") != "y"):
        print("Создание отменено")
    else:
        with open(filepath, "w", encoding="utf-8") as f:
            if filename.endswith(".txt"):
                desc = '\n\n'.join([wrapper.fill(i) for i in description.split('\n')])

                f.write(
                    "Источник: {u}\n\n"
                    "Задача:\n{d}\n\n\n"
                    "Ответ: ВСТАВЬТЕ_ОТВЕТ\n".format(d=desc, u=url)
                )
            else:
                wrapper.initial_indent = "# "
                wrapper.subsequent_indent = "# "
                desc = wrapper.fill(description).replace("💶", "\n\n# ")

                if attachments:
                    files_s = '# Файлы:\n' + \
                              '\n'.join(map(lambda x: f'open(r"../{x}")',
                                            map(lambda x: x.replace('\\', '/'), attachments)))

                f.write(
                    "# Источник: {u}\n\n"
                    "# Задача:\n{d}\n\n{f}".format(d=desc, u=url,
                                                   f=files_s if attachments else "\n")
                )
        print(f'Создан файл: "{filename}"')


def get_problems_count(url):
    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.text, "html.parser")

    prob_list = soup.find("div", class_="prob_list")
    assert prob_list, ValueError("ОЙ! Укажите ссылку на СПИСОК задач, а не на одну задачу")

    return len(prob_list)


def parse_problem(url, problem_number):
    downloaded_files = []

    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.text, "html.parser")

    prob_list = soup.find("div", class_="prob_list")
    assert prob_list, ValueError("ОЙ! Укажите ссылку на СПИСОК задач, а не на одну задачу")

    prob_item = prob_list.find("div", class_="prob_num", string=problem_number)
    assert prob_item, ValueError("ОЙ! Задачи с таким номером нет на сайте!")

    pbody = prob_item.find_next().find("div", class_="pbody")
    assert pbody, ValueError("ОЙ! Тело задачи не найдено!")

    html_string = str(pbody)

    # Ненавижу тех, кто портит данные
    tempstr = re.sub(r"(?=<p.*?>)", "</p>", html_string).replace("</p>", "", 1)
    le = tempstr.find("</p", tempstr.rfind("<p"))
    ri = tempstr.rfind("</p")
    fixed = tempstr[:le] + tempstr[ri:]

    indent_next = False
    description = ""
    soup = BeautifulSoup(fixed, 'html.parser')
    for item in soup.find_all("p"):
        if not item.text:
            indent_next = True
            continue

        if indent_next:
            indent_next = False
            description += '\n'

        c = str(item).startswith('<p class="left_margin">') or str(item).startswith('<p>')

        if c:
            description += item.get_text() + ' '
        else:
            indent_next = False if description.endswith('\n') else True

    description = re.sub(r' +', ' ', sensible_text(description)).strip('\n ')

    files = set(pbody.find_all(target="_blank"))
    for file in pbody.find_all(src=lambda v: v and "/get_file" in v): files.add(file)

    if files:
        print(f" ✅ Найдено {len(files)} файл{number_case(len(files))}.")
        downloaded_recent = {}
        if not os.path.exists(download_folder):
            os.makedirs(download_folder)

        sub_folder = os.path.join(download_folder, f"Задача номер {problem_number}")
        if not os.path.exists(sub_folder):
            os.makedirs(sub_folder)

        file_translations = {'Таблица': 'xlsx', 'Картинка': ['jpg', 'jpeg', 'png'], 'Текстовик': ['txt', 'docx']}
        for file in files:
            file_url_id = [file.get(i) for i in ["href", "src"] if file.get(i) is not None][0]
            file_url = "https://inf-ege.sdamgia.ru" + file_url_id
            file_response = requests.get(file_url)
            mime_type = mimetypes.guess_extension(file_response.headers["Content-Type"].split(';')[0])

            assert mime_type, ValueError("ОЙ! Неизвестное расширение файла")
            posFT = [k for k, v in file_translations.items()
                     if mime_type[1:] in ([v] if isinstance(v, str) else v)]
            filetype = posFT[0] if posFT else 'unknown'
            filename = sensible_text(file.text if file.text else filetype) + mime_type
            filepath = os.path.join(sub_folder, filename)
            downloaded_files.append(filepath)
            downloaded_recent[filename] = [False, None]

            if filename in os.listdir(sub_folder) and \
                    input(f" - ❔ Файл {filename} уже есть! Заменить? (y/n) ") != "y": continue

            with open(filepath, 'wb') as f:
                f.write(file_response.content)
            downloaded_recent[filename] = [True, filetype]

        print(" - Скаченные файлы:")
        for i, (recent, data) in enumerate(downloaded_recent.items()):
            state, filetype = data
            print(f"\t{i + 1}. \033[{0 if state else 9}m{recent:25}\033[0m | {'✔' if state else '❌'} | \033[37m("
                  f"{filetype})\033[0m")

    else:
        print(" - Нечего скачивать ✖")

    return description, downloaded_files


def setup_problem(task_number):
    print(f"\n#===   \033[34mЗадача номер {task_number}  \033[0m ===#\n")
    description, downloaded_files = parse_problem(url, str(task_number))
    create_solution_file(solution_folder, task_number, description, downloaded_files)
    print(f"\n#=== \033[34mСоздание окончено \033[0m ===#\n")


def error(*message: str):
    print("\033[31m[❌]", *message)


if __name__ == "__main__":
    print("Введи:")
    print(" * \033[34mALL\033[37m -\033[0m все задачи сразу")
    print(" * \033[34mA-B\033[37m -\033[0m задачи от \033[31mA\033[0m до \033[32mB\033[0m")
    print()

    task_number = input(" - ❔ Номер задачи: ").lower()
    count = get_problems_count(url)

    if task_number.isnumeric():
        setup_problem(task_number)
    elif re.fullmatch(r"\d+-\d+", task_number):
        from_, to_ = map(int, task_number.replace(" ", "").split("-"))
        if from_ > to_:
            error(f"Число А должно быть меньше B ({from_} < {to_})")
        elif from_ == to_:
            error("Числа должны быть разными")
        else:
            for i in range(from_, to_+1):
                setup_problem(i)
    elif task_number == "all":
        for i in range(1, count+1):
            setup_problem(i)
