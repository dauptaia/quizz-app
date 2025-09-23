from flask import Flask, render_template, request, redirect, url_for
import yaml
import os
import csv
from datetime import datetime, timedelta
from collections import Counter

app = Flask(__name__)


import yaml

with open("config.yaml", "r", encoding="utf-8") as f:
    config = yaml.safe_load(f)

QUIZ_FOLDER = config.get("QUIZ_FOLDER", "quizzes")
ANSWERS_FOLDER = config.get("ANSWERS_FOLDER", "submissions")
HOST = config.get("HOST", "0.0.0.0")
PORT = config.get("PORT", 5000)
#DEBUG = config.get("DEBUG", True)
LAST_N_MINUTES = config.get("SHOW_LAST_N_MINUTES", 30)


os.makedirs(ANSWERS_FOLDER, exist_ok=True)


def load_quizzes():
    quizzes = []
    for file in os.listdir(QUIZ_FOLDER):
        if file.endswith(".yaml"):
            path = os.path.join(QUIZ_FOLDER, file)
            with open(path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
                quizzes.append(data["quiz"])
    return quizzes


def load_quiz(code):
    path = os.path.join(QUIZ_FOLDER, f"{code}.yaml")
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def save_submission(quiz_code, token, answers, score, total):
    filename = os.path.join(ANSWERS_FOLDER, f"{quiz_code}_answers.csv")
    file_exists = os.path.isfile(filename)
    with open(filename, "a", newline="", encoding="utf-8") as csvfile:
        writer = csv.writer(csvfile)
        if not file_exists:
            writer.writerow(["timestamp", "token", "answers", "score", "total"])
        writer.writerow([datetime.now().isoformat(), token, answers, score, total])



def load_submissions(quiz_code, last_minutes=None):
    filename = os.path.join(ANSWERS_FOLDER, f"{quiz_code}_answers.csv")
    submissions = []
    if not os.path.exists(filename):
        return submissions
    with open(filename, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            ts = datetime.fromisoformat(row["timestamp"])
            if last_minutes:
                if ts < datetime.now() - timedelta(minutes=last_minutes):
                    continue
            # Convert answers from string to list of tuples
            answers = eval(row["answers"])
            submissions.append({
                "timestamp": ts,
                "token": row["token"],
                "answers": answers,
                "score": int(row["score"]),
                "total": int(row["total"])
            })
    return submissions

@app.route("/student")
def student_home():
    quizzes = load_quizzes()
    return render_template("student_home.html", quizzes=quizzes)


@app.route("/quiz/<code>", methods=["GET", "POST"])
def quiz(code):
    quiz_data = load_quiz(code)
    questions = quiz_data["questions"]

    if request.method == "POST":
        token = request.form.get("token")
        answers = []
        score = 0
        for q in questions:
            qid = str(q["id"])
            ans = request.form.get(f"q{qid}")
            conf = request.form.get(f"conf{qid}")
            answers.append((qid, ans, conf))
            if ans is not None and int(ans) == q["correct"]:
                score += 1

        save_submission(code, token, answers, score, len(questions))
        return render_template(
            "quiz_result.html", 
            quiz=quiz_data, 
            answers=answers, 
            score=score,
            qa_pairs=zip(questions, answers)  # pass zipped pairs explicitly
        )

    return render_template("quiz.html", quiz=quiz_data)



@app.route("/trainer")
def trainer_home():
    
    quizzes = load_quizzes()
    quiz_stats = []
    for q in quizzes:
        submissions = load_submissions(q["code"])
        quiz_stats.append({
            "title": q["title"],
            "code": q["code"],
            "last_update": q.get("last_update", ""),
            "num_submissions": len(submissions)
        })
    return render_template("trainer_home.html", quiz_stats=quiz_stats)

@app.route("/trainer/<quiz_code>")
def trainer_quiz(quiz_code):
   
    quiz_data = load_quiz(quiz_code)
    submissions = load_submissions(quiz_code, last_minutes=LAST_N_MINUTES)

    scores = [s["score"] for s in submissions]
    total_submissions = len(scores)
    avg_score = sum(scores)/total_submissions if total_submissions else 0

    # Count most failed answers
    question_failures = []
    for q in quiz_data["questions"]:
        counter = Counter()
        for s in submissions:
            for ans in s["answers"]:
                if int(ans[0]) == q["id"] - 1:  # question id adjustment
                    if int(ans[1]) != q["correct"]:
                        counter[int(ans[1])] += 1
        question_failures.append({
            "id": q["id"],
            "text": q["text"],
            "options": q["options"],
            "failures": dict(counter)
        })

    return render_template(
        "trainer_quiz.html",
        quiz=quiz_data,
        total_submissions=total_submissions,
        avg_score=avg_score,
        question_failures=question_failures
    )

@app.template_filter('enumerate')
def jinja2_enumerate(iterable):
    return enumerate(iterable)
