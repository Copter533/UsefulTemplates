import os
import re
import subprocess
import multiprocessing
from time import time
from datetime import date

import requests
from bs4 import BeautifulSoup

from config import *


def generate_html_table(table, wrongs, newest_list, task_count):
    table_html = "<html>\n<head>\n<meta charset='UTF-8'>\n{}\n</head>\n<body style='background-color: #2b2b2b;'>\n" \
    .format(
        """<style>
            table { background-color: #f0f0f0; border-color: black; border: black; white-space: pre; }
            h1 {
                background-color: #3c3f41;
                color: white;

                padding: 30px;
                border-radius: 10px;
            }
            .hidden {
                background-color: black;
            }
            .hidden:hover {
                background-color: black;
                color: white;
            }
            </style>""")

    # Заголовок
    table_html += "<h1 align='center'>Правильность ответов:</h1>\n"
    # Начало таблицы
    table_html += "<table border='1' cellpadding='10' align='center'>\n"

    # Заголовок таблицы
    table_html += "<tr style='background-color: black; color: white; font-weight: bold;'>\n"
    for item in table[0]:
        table_html += f"<th>{item}</th>\n"
    table_html += "</tr>\n"

    # Остальные строки таблицы
    try:
        spacesM = max([len(i[3].split('\n')[0]) for i in table[1:]])
    except ValueError:
        return table_html + "</table>\n"
    counter = [0, 0, 0]

    for j in range(1, task_count + 1):
        possible_row = [i for i in table if i[0] == f'#{j}']
        row = possible_row[0] if possible_row else [f'#{j}', '', '💫', '❔', None]
        if not isinstance(row[2], bool):
            table_html += "<tr style='background-color: #f0f0ff'>\n"
        else:
            if row[1] == '???':
                table_html += "<tr style='background-color: #c0ffc0'>\n"
                row[1] = '❔❔❔'
            elif row[1] == '_skip_':
                table_html += "<tr style='background-color: #c0c0ff'>\n"
                row[1] = '▶ ▶ Пропуск ▶ ▶'
                row[2] = '💫'
            else:
                table_html += "<tr>\n" if row[2] else "<tr style='background-color: #fff0f0'>\n"

        for i, item in enumerate(row):
            item_s = f"<td align='center'>{item}</td>\n"
            if i == 4:
                item_s = f"<td align='center'><a href={item}>*Клик*</a></td>\n" if item else "<td></td>"
            elif i == 3:
                sp = ' ' * (spacesM - len(item) + 1)
                item_s = f"<td align='center'><span class='hidden'>{sp}{item}{sp}</span></td>\n"
            elif i == 2:
                if not isinstance(item, bool):
                    item_s = f"<td align='center'>{item}</td>\n"
                    counter[2] += 1
                elif not item:
                    paste = '✖'
                    answer, correct = row[1], row[3]
                    answers, corrects = len(answer.split()), len(correct.split())
                    if answers != corrects:
                        paste += ' ' + ['МАЛО', 'МНОГО'][answers > corrects]
                    item_s = f"<td align='center' style='color: red'>{paste}</td>\n"
                    counter[1] += 1
                else:
                    item_s = f"<td align='center' style='color: green'>✔</td>\n"
                    counter[0] += 1
            elif i == 0 and item[1:] in newest_list:
                item_s = f"<td align='center'>      {item} 📔</td>\n"

            table_html += '\t' + item_s
        table_html += "</tr>\n"

    # Закрываем таблицу
    table_html += "</table>\n"

    # Создаём таблицу с результатами
    wrong_style = "align='center' style='color: red'"
    table_html += f"""\
<h1 align='center'>Результаты:</h1>
<table border='1' cellpadding='10' align='center'>
    <tr>
        <td align='center' style='color: green'>✔</td>
        <td align='center' style='color: red'>✖</td>
        <td align='center' style='color: blue'>⚪</td>
        <td align='center' colspan="{len(wrongs)}">Исправить</td>
    </tr>
    <tr>
        <td align='center'>{counter[0]}</td>
        <td align='center'>{counter[1]}</td>
        <td align='center'>{counter[2]}</td>
        <td {wrong_style}>{f'</td><td {wrong_style}>'.join(wrongs)}</td>
    </tr>
</table>"""

    # Окончание
    table_html += "</body>\n</html>"

    return table_html


def check_task(filename, link, answer=None):
    os.chdir(solution_folder)
    if answer is None:
        answer = subprocess.run(["python", filename, "checker"],
                                capture_output=True, text=True, encoding="UTF-8").stdout.lower().strip(' \n')
    os.chdir('../')

    response = requests.get(link)
    soup = BeautifulSoup(response.text, 'html.parser')

    datablob = soup.find("div", id=lambda v: v and re.fullmatch(r'sol\d+', v)).text.lower()
    le = datablob.rfind("ответ") + 6
    ri = datablob.find(".", le)
    if ri == -1: ri = len(datablob)

    correct = datablob.split()[-1].strip('\n. ') if le == 5 else datablob[le:ri].strip()
    correct = correct.replace(' ', '').replace('—', '')

    if not correct[0].isalpha() and not correct.replace(' ', '').isnumeric():
        correct = soup.select('center > p')[0].get_text('\n')

    clear_correct = ' '.join(re.findall(r"[\da-z]+", correct)) if not correct.isalpha() else correct
    return filename, answer, clear_correct, link


def main():
    print("Вывод осуществляется в", answers)

    if not os.path.exists(solution_folder): os.mkdir(solution_folder)

    newest = None
    newest_list = []
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')

    prob_list = soup.find("div", class_="prob_list")
    assert prob_list, ValueError("ОЙ! Укажите ссылку на СПИСОК задач, а не на одну задачу")

    tasks = {}
    table = ['Номер Ответ Правильность Да Ссылка'.split()]
    with multiprocessing.Pool() as pool:
        task_count = len(prob_list.find_all("div", class_="prob_num"))
        for filename in os.listdir(solution_folder):
            if not re.fullmatch("Задача номер \d+\..{2,3}$", filename): continue

            problem_number = [i for i in filename[:filename.find('.')].split(' ') if i.isnumeric()][-1]
            filepath = os.path.join(solution_folder, filename)
            mod_time = date.fromtimestamp(os.path.getmtime(filepath))

            if newest is None: newest = mod_time

            if mod_time > newest:
                # noinspection PyUnusedLocal
                newest = mod_time
                newest_list = [problem_number]
            elif mod_time.day == newest.day:
                newest_list.append(problem_number)

            prob_item = prob_list.find("div", class_="prob_num", string=problem_number)
            assert prob_item, ValueError("ОЙ! Задачи с таким номером нет на сайте!")

            nums = prob_item.find_next().find("span", class_="prob_nums")
            assert nums, ValueError("ОЙ! Ссылка на ответ не найдена!")

            link = url[:url.find('/', url.find('//') + 2)] + nums.find('a')["href"]

            if filename.endswith(".txt"):
                with open(filepath, encoding="utf-8") as f:  # !
                    s = f.read()
                    le = s.find("Ответ: ") + 6
                    ri = s.find('\n', le)
                    answer = s[le:ri].strip()

                    tasks[problem_number] = pool.apply_async(check_task, (filename, link, answer)), link
            else:
                tasks[problem_number] = pool.apply_async(check_task, (filename, link)), link

        wrongs = []
        finished = []
        print("Вычисляем...")

        st = time()
        while (time() - st < timeout) and not all([i[0].ready() for i in tasks.values()]): pass

        print('Завершено!')

        unfinished = [k for k, v in tasks.items() if not v[0].ready()]
        pool.terminate()  # Принудительно завершаем все незавершенные задачи

        for k, data in tasks.items():
            task, link = data
            if not task.ready(): continue

            problem_number = '#' + k
            filename, raw_answer, correct, link = task.get()

            if raw_answer != correct: wrongs.append(problem_number)
            answer = raw_answer if raw_answer else '✖'
            state = answer == correct
            finished.append(problem_number[1:])

            table.append([problem_number, answer, state, correct, link])

        for k in unfinished:
            table.append(['#' + k, 'TIMEOUT', '⏰', '❔', tasks[k][1]])
            wrongs.append('#' + k)

        html_table = generate_html_table(table, wrongs, newest_list, task_count)
        with open(answers, 'w', encoding='utf-8') as f:
            f.write(html_table)

        print("Новые задания:", ", ".join(newest_list))


if __name__ == '__main__':
    main()
