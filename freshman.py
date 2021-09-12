from selenium import webdriver
from time import sleep
from bs4 import BeautifulSoup
import re
import pickle
import os.path

QUESTION_TYPES = [
    "multiple_choice_question",
    "multiple_answers_question",
    "true_false_question",
    "multiple_dropdowns_question",
]

def query_db(question_db, q_id, ans):
    options = []
    for question_id, _, _, ans in question_db:
        if question_id == q_id:
            for ans_id, _, is_ans_correct in ans:
                if is_ans_correct == "yes":
                    options.append(ans_id)
                    break
            if options == []:
                for ans_id, _, is_ans_correct in ans:
                    if is_ans_correct != "no":
                        options.append(ans_id)
            return options
    return ans

def update_db(question_db, q_id, new_rec):
    new_db = []
    matched = False
    for question_id, question_type, question_text, ans in question_db:
        if question_id == q_id:

            matched = True
            new_ans = new_rec[3]
            old_ans = ans
            new_new_ans = []
            for aid_new, ans_text_new, is_ans_correct_new in new_ans:
                for aid_old, _, is_ans_correct_old in old_ans:
                    if aid_new == aid_old:
                        if is_ans_correct_old == "unknown" and is_ans_correct_new != "unknown":
                            is_ans_correct = is_ans_correct_new
                        elif is_ans_correct_old != "unknown" and is_ans_correct_new == "unknown":
                            is_ans_correct = is_ans_correct_old
                        elif is_ans_correct_old == "unknown" and is_ans_correct_new == "unknown":
                            is_ans_correct = "unknown"
                        else:
                            is_ans_correct = is_ans_correct_new
                        new_new_ans.append([aid_new, ans_text_new, is_ans_correct])
            new_db.append([new_rec[0], new_rec[1], new_rec[2], new_new_ans])
        else:
            new_db.append([question_id, question_type, question_text, ans])
    if not matched:
        new_db.append(new_rec)
    return new_db

def check_answers(html_doc, question_db=[]):
    soup = BeautifulSoup(html_doc, "lxml")
    question_list = soup.select("div.display_question.question")

    for q in question_list:

        is_correct = not "incorrect" in q.attrs["class"]
        question_text = q.select_one("div.question_text").text
        question_id = q.attrs["id"]

        for c in q.attrs["class"]:
            if c in QUESTION_TYPES:
                question_type = c
                break

        if question_type == "multiple_dropdowns_question":
            rec = [question_id, question_type, question_text, []]
            question_db = update_db(question_db, question_id, rec)
        else:
            answer_list = q.find_all(name="div", id=re.compile("answer_\d+"))
            ans = []
            for answer in answer_list:
                is_selected = "selected_answer" in answer.attrs["class"]
                answer_text = answer.select_one("div.answer_text").text
                answer_id = answer.attrs["id"]
                is_ans_correct = ""
                if question_type == "multiple_choice_question" or question_type == "true_false_question":
                    if is_selected:
                        is_ans_correct = "yes" if is_correct else "no"
                    else:
                        is_ans_correct = "no" if is_correct else "unknown"
                elif question_type == "multiple_answers_question":
                    if is_selected and is_correct:
                        is_ans_correct = "yes"
                    else:
                        is_ans_correct = "unknown"
                ans.append([answer_id, answer_text, is_ans_correct])
            rec = [question_id, question_type, question_text, ans]
            question_db = update_db(question_db, question_id, rec)

    return question_db

question_db = []
if os.path.exists("question_db.pkl"):
    with open("question_db.pkl", "rb") as f:
        question_db = pickle.load(f)
    print("DATABASE LOADED")

with webdriver.Chrome(executable_path="/Users/aug/chromedriver") as browser:
    browser.get("https://elearning.fudan.edu.cn/courses/39575/quizzes/5237/take")

    while input("START?") != "s":
        # MAIN
        for i in range(100):
            inputs = browser.find_elements_by_css_selector("label.answer_row > span.answer_input > input.question_input")
            #options = browser.find_elements_by_css_selector("label.answer_row > div.answer_label")
            #question = browser.find_element_by_css_selector("div.question_text")
            ans = []
            for i in inputs:
                input_id = i.get_attribute("id")
                m = re.match("(question_\d+)_(answer_\d+)", input_id)
                qid, aid = m.group(1), m.group(2)
                ans.append(aid)
            ans = query_db(question_db, qid, ans)

            if len(ans) == 1:
                for i in inputs:
                    input_id = i.get_attribute("id")
                    m = re.match("(question_\d+)_(answer_\d+)", input_id)
                    qid, aid = m.group(1), m.group(2)
                    if aid == ans[0]:
                        i.click()
                        break
            else:
                browser.find_element_by_css_selector("a.flag_question").click()

            # NEXT QUESTION
            browser.find_element_by_css_selector("button.next-question").click()
            sleep(0.5)
        
         # SUBMIT
        #browser.find_element_by_id("submit_quiz_button").click()
        #sleep(1)
        input("waiting to submit...")
        
        # CHECK ANSWERS
        html_doc = browser.page_source
        question_db = check_answers(html_doc, question_db)
        with open("question_db.pkl", "wb") as f:
            pickle.dump(question_db, f)
