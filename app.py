from flask import Flask, render_template, request, session, redirect, url_for
from openai import OpenAI
from dotenv import load_dotenv
import os, json
from pydantic import BaseModel
from typing import Optional

from core_copy.units import UnitManager
from core_copy.progress import ProgressManager

unit_manager = UnitManager()
progress_manager = ProgressManager()

load_dotenv()

app = Flask(__name__)
app.secret_key = "secret_key"

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

class Test_Question(BaseModel):
    question_number: int
    topic_id: str
    question_text: str
    code_snippet: Optional[str] = None  
    options: list[str]
    correct_answer: str

def generate_question(used_ids, topic_scope=None):
    valid_ids = []
    scope_context = ""

    for unit in unit_manager.units_data["units"]:
        if topic_scope and topic_scope == unit["id"]:
            valid_ids.extend([s["id"] for s in unit["sections"]])
            scope_context = f"The student is currently being tested on Unit {unit['unit']}: {unit['title']}."
        else:
            for section in unit["sections"]:
                if topic_scope and topic_scope == section["id"]:
                    valid_ids.append(section["id"])
                    scope_context = f"The student is currently being tested on Section: {section['section']}."
                elif not topic_scope:
                    valid_ids.append(section["id"])

    test_prompt = f"""..."""  # unchanged

    response = client.chat.completions.parse(
        model="gpt-4o-mini",
        response_format=Test_Question,
        messages=[
            {"role": "system", "content": test_prompt},
            {"role": "user", "content": "Generate the next question now."}
        ]
    )
    
    return json.loads(response.choices[0].message.content)

@app.route("/")
def home():
    return render_template("home.html", mode="home")

@app.route("/test_mode")
def test_selection():
    return render_template("testmode.html", units_data=unit_manager.units_data, mode="test")

@app.route("/practice")
def practice_selection():
    return render_template("practicetest.html", units_data=unit_manager.units_data, mode="practice")

@app.route("/test/start/<mode>/<scope>")
def start_test(mode, scope):
    session["questions"] = []
    session["current_question"] = 0
    session["answers"] = {}
    session["feedback_shown"] = {}
    session["used_topic_ids"] = []
    session["mode"] = mode
    session["test_scope"] = None if scope == "all" else scope
    
    if "-" in scope:
        session["total_questions"] = 3
    elif scope.startswith("U"):
        session["total_questions"] = 5
    else:
        session["total_questions"] = 10
        
    return redirect(url_for("question"))

@app.route("/test/question")
def question():
    # 🔴 NEW: handle sidebar jump
    go_to = request.args.get("go")
    if go_to is not None:
        session["current_question"] = int(go_to)

    questions = session.get("questions", [])
    index = session.get("current_question", 0)
    total = session.get("total_questions", 10)
    mode = session.get("mode")

    if index >= total:
        return redirect(url_for("results"))
    
    if index >= len(questions):
        used_ids = session.get("used_topic_ids", [])
        scope = session.get("test_scope")
        
        new_q = generate_question(used_ids, topic_scope=scope)
        questions.append(new_q)
        session["questions"] = questions
        
        used_ids.append(new_q["topic_id"])
        session["used_topic_ids"] = used_ids
        session.modified = True

    q = questions[index]
    answers = session.get("answers", {})
    feedback_shown = session.get("feedback_shown", {})

    selected = answers.get(str(index))

    is_correct = None
    if selected:
        is_correct = (selected == q["correct_answer"])

    show_feedback = (mode == "practice" and feedback_shown.get(str(index)))

    return render_template(
        "test.html",
        q=q,
        index=index,
        selected=selected,
        questions=questions,
        mode=mode,
        show_feedback=show_feedback,
        is_correct=is_correct
    )

@app.route("/test/answer", methods=["POST"])
def answer():
    selected = request.form.get("answer")
    direction = request.form.get("direction")
    index = session["current_question"]
    mode = session.get("mode")

    answers = session.get("answers", {})
    feedback_shown = session.get("feedback_shown", {})

    if selected:
        answers[str(index)] = selected.upper()
        session["answers"] = answers

    if direction == "next":
        session["current_question"] = index + 1
        return redirect(url_for("question"))

    if direction == "back":
        session["current_question"] = max(0, index - 1)
        return redirect(url_for("question"))

    if mode == "practice":
        if not feedback_shown.get(str(index)):
            feedback_shown[str(index)] = True
            session["feedback_shown"] = feedback_shown
            return redirect(url_for("question"))

        session["current_question"] = index + 1
        return redirect(url_for("question"))

    if mode == "test":
        session["current_question"] = index + 1
        return redirect(url_for("question"))

    return redirect(url_for("question"))

@app.route("/test/results")
def results():
    mode = session.get("mode")
    questions = session.get("questions", [])
    answers = session.get("answers", {})
    results_list = []
    score = 0

    for i, q in enumerate(questions):
        selected = answers.get(str(i))
        correct = q["correct_answer"]
        is_correct = (selected == correct)

        if is_correct:
            score += 1
            progress_manager.update(q["topic_id"], True) 
        else:
            progress_manager.update(q["topic_id"], False)

        results_list.append({
            "question": q["question_text"],
            "options": q["options"],
            "your_answer": selected,
            "correct_answer": correct,
            "is_correct": is_correct
        })

    progress_manager.save()
    total = len(questions)
    percentage = (score / total * 100) if total > 0 else 0

    return render_template(
        "results.html", 
        score=score, 
        total=total, 
        percentage=percentage, 
        results=results_list,
        mode=mode
    )

if __name__ == "__main__":
    app.run(debug=True)